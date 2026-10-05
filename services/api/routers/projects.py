from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re

import os
import shutil
import hashlib
import asyncio
from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.models import ProjectStatus, BuildStatus
from services.api.core.redis_client import push_job
from services.api.core.deployment_url import deployment_url_service
from services.api.schemas.projects import ProjectCreate, ProjectUpdate, ProjectResponse
from services.analyzer.archive_validator import archive_validator
from services.analyzer.detector import project_detector
from services.analyzer.git_importer import git_importer, GitSecurityError


router = APIRouter(prefix="/projects", tags=["Projects"])

class GitImportRequest(BaseModel):
    name: str
    repo_url: str
    branch: Optional[str] = None
    slug: Optional[str] = None

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

@router.get("", response_model=List[ProjectResponse])
async def list_projects(token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    cursor = db.projects.find({"user_id": token_data["sub"]}).sort("created_at", -1)
    projects = []
    async for p in cursor:
        slug = p["slug"]
        # active_url is ONLY set by the deployer via deployment_url_service.
        # Never invent a URL here — if it's None, the project has not been deployed yet.
        active_url = p.get("active_url") or None
        projects.append(ProjectResponse(
            id=str(p["_id"]),
            name=p["name"],
            slug=slug,
            status=p.get("status", ProjectStatus.CREATED.value),
            framework=p.get("framework"),
            language=p.get("language"),
            package_manager=p.get("package_manager"),
            build_command=p.get("build_command"),
            output_directory=p.get("output_directory"),
            active_deployment_id=p.get("active_deployment_id"),
            active_url=active_url,
            created_at=p.get("created_at", ""),
            updated_at=p.get("updated_at", "")
        ))
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(payload: ProjectCreate, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    base_slug = _slugify(payload.slug or payload.name)
    if not base_slug:
        base_slug = "project"

    # Ensure unique slug
    slug = base_slug
    counter = 1
    while await db.projects.find_one({"slug": slug}):
        slug = f"{base_slug}-{counter}"
        counter += 1

    now_str = utc_now_iso()
    doc = {
        "user_id": token_data["sub"],
        "name": payload.name.strip(),
        "slug": slug,
        "status": ProjectStatus.CREATED.value,
        "framework": None,
        "language": None,
        "package_manager": None,
        "build_command": None,
        "output_directory": "dist",
        "active_deployment_id": None,
        "active_url": None,
        "created_at": now_str,
        "updated_at": now_str
    }

    res = await db.projects.insert_one(doc)
    doc["_id"] = res.inserted_id

    return ProjectResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        slug=doc["slug"],
        status=doc["status"],
        framework=doc["framework"],
        language=doc["language"],
        package_manager=doc["package_manager"],
        build_command=doc["build_command"],
        output_directory=doc["output_directory"],
        active_deployment_id=doc["active_deployment_id"],
        active_url=doc["active_url"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"]
    )

@router.post("/import-git", status_code=status.HTTP_201_CREATED)
async def import_git_project(payload: GitImportRequest, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    """Imports a project from a public Git repository, analyzes it, and launches the build."""
    db = get_database()
    now_str = utc_now_iso()

    # 1. Clone or download remote repo into workspace
    try:
        workspace_dir, zip_path, file_size, checksum = git_importer.clone_or_download_repo(
            repo_url=payload.repo_url,
            branch=payload.branch
        )
    except GitSecurityError as gse:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(gse))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Git import failed: {str(e)}")

    try:
        # 2. Analyze extracted workspace
        analysis = project_detector.analyze(workspace_dir)

        # 3. Create Project record
        base_slug = _slugify(payload.slug or payload.name)
        if not base_slug:
            base_slug = "repo"
        slug = base_slug
        counter = 1
        while await db.projects.find_one({"slug": slug}):
            slug = f"{base_slug}-{counter}"
            counter += 1

        build_cmd = analysis.buildCommand
        out_dir = analysis.outputDirectory or "."

        proj_doc = {
            "user_id": token_data["sub"],
            "name": payload.name.strip(),
            "slug": slug,
            "status": ProjectStatus.BUILD_QUEUED.value,
            "framework": analysis.framework,
            "language": analysis.language,
            "package_manager": analysis.packageManager,
            "build_command": build_cmd,
            "output_directory": out_dir,
            "git_repo": payload.repo_url,
            "git_branch": payload.branch or "main",
            "active_deployment_id": None,
            "active_url": None,
            "created_at": now_str,
            "updated_at": now_str
        }
        p_res = await db.projects.insert_one(proj_doc)
        project_id = str(p_res.inserted_id)

        # 4. Save ZIP into permanent storage
        upload_id = str(ObjectId())
        storage_rel_path = os.path.join("uploads", f"{upload_id}_git_export.zip")
        storage_abs_path = os.path.join(settings.STORAGE_PATH, storage_rel_path)
        os.makedirs(os.path.dirname(storage_abs_path), exist_ok=True)
        shutil.copyfile(zip_path, storage_abs_path)

        upload_doc = {
            "_id": ObjectId(upload_id),
            "project_id": project_id,
            "user_id": token_data["sub"],
            "filename": f"{slug}-git.zip",
            "file_size": file_size,
            "checksum": checksum,
            "storage_path": storage_rel_path,
            "analysis": analysis.model_dump(),
            "created_at": now_str
        }
        await db.uploads.insert_one(upload_doc)

        # 5. Create Build Record
        build_doc = {
            "project_id": project_id,
            "upload_id": upload_id,
            "user_id": token_data["sub"],
            "status": BuildStatus.QUEUED.value,
            "framework": analysis.framework,
            "package_manager": analysis.packageManager,
            "build_command": build_cmd,
            "output_directory": out_dir,
            "exit_code": None,
            "started_at": None,
            "completed_at": None,
            "duration_seconds": None,
            "error_message": None,
            "created_at": now_str
        }
        b_res = await db.builds.insert_one(build_doc)
        build_id = str(b_res.inserted_id)

        # 6. Push to Redis build queue
        await push_job("build", {
            "build_id": build_id,
            "project_id": project_id,
            "upload_id": upload_id,
            "package_manager": analysis.packageManager,
            "build_command": build_cmd,
            "output_directory": out_dir
        })

        return {
            "project_id": project_id,
            "slug": slug,
            "build_id": build_id,
            "analysis": analysis.model_dump(),
            "message": "Git repository successfully imported and build queued!"
        }

    finally:
        # Cleanup temporary files
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)

async def _resolve_user_project(db, id_or_slug: str, user_id: str) -> Dict[str, Any]:
    query: Dict[str, Any] = {"user_id": user_id}
    if ObjectId.is_valid(id_or_slug):
        query["_id"] = ObjectId(id_or_slug)
    else:
        query["slug"] = id_or_slug
    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project

@router.post("/{id_or_slug}/redeploy", status_code=status.HTTP_202_ACCEPTED)
async def redeploy_project(id_or_slug: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    """Triggers a new build and deployment using the project's most recent source upload."""
    db = get_database()
    project = await _resolve_user_project(db, id_or_slug, token_data["sub"])
    project_id = str(project["_id"])

    # Find latest upload
    latest_upload = await db.uploads.find_one({"project_id": project_id}, sort=[("created_at", -1)])
    if not latest_upload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No source uploads found for this project")

    now_str = utc_now_iso()
    upload_id = str(latest_upload["_id"])
    build_cmd = project.get("build_command")
    out_dir = project.get("output_directory") or "."

    build_doc = {
        "project_id": project_id,
        "upload_id": upload_id,
        "user_id": token_data["sub"],
        "status": BuildStatus.QUEUED.value,
        "framework": project.get("framework"),
        "package_manager": project.get("package_manager"),
        "build_command": build_cmd,
        "output_directory": out_dir,
        "exit_code": None,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None,
        "created_at": now_str
    }
    b_res = await db.builds.insert_one(build_doc)
    build_id = str(b_res.inserted_id)

    await db.projects.update_one(
        {"_id": project["_id"]},
        {"$set": {"status": ProjectStatus.BUILD_QUEUED.value}}
    )

    await push_job("build", {
        "build_id": build_id,
        "project_id": project_id,
        "upload_id": upload_id,
        "package_manager": project.get("package_manager"),
        "build_command": build_cmd,
        "output_directory": out_dir
    })

    return {
        "project_id": project_id,
        "build_id": build_id,
        "status": "QUEUED",
        "message": "Redeployment queued successfully!"
    }

@router.get("/{id_or_slug}", response_model=ProjectResponse)
async def get_project(id_or_slug: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    project = await _resolve_user_project(db, id_or_slug, token_data["sub"])

    # active_url is set by the deployer; never invent it here
    active_url = project.get("active_url") or None

    return ProjectResponse(
        id=str(project["_id"]),
        name=project["name"],
        slug=project["slug"],
        status=project.get("status", ProjectStatus.CREATED.value),
        framework=project.get("framework"),
        language=project.get("language"),
        package_manager=project.get("package_manager"),
        build_command=project.get("build_command"),
        output_directory=project.get("output_directory"),
        active_deployment_id=project.get("active_deployment_id"),
        active_url=active_url,
        created_at=project.get("created_at", ""),
        updated_at=project.get("updated_at", "")
    )


@router.patch("/{id_or_slug}", response_model=ProjectResponse)
async def update_project(id_or_slug: str, payload: ProjectUpdate, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    project = await _resolve_user_project(db, id_or_slug, token_data["sub"])

    updates = {}
    if payload.name:
        updates["name"] = payload.name.strip()
    if payload.build_command is not None:
        updates["build_command"] = payload.build_command
    if payload.output_directory is not None:
        updates["output_directory"] = payload.output_directory

    if updates:
        updates["updated_at"] = utc_now_iso()
        await db.projects.update_one(
            {"_id": project["_id"]},
            {"$set": updates}
        )

    updated_project = await db.projects.find_one({"_id": project["_id"]})
    if not updated_project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return ProjectResponse(
        id=str(updated_project["_id"]),
        name=updated_project["name"],
        slug=updated_project["slug"],
        status=updated_project.get("status", ProjectStatus.CREATED.value),
        framework=updated_project.get("framework"),
        language=updated_project.get("language"),
        package_manager=updated_project.get("package_manager"),
        build_command=updated_project.get("build_command"),
        output_directory=updated_project.get("output_directory"),
        active_deployment_id=updated_project.get("active_deployment_id"),
        active_url=updated_project.get("active_url"),
        created_at=updated_project.get("created_at", ""),
        updated_at=updated_project.get("updated_at", "")
    )

@router.delete("/{id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(id_or_slug: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    project = await _resolve_user_project(db, id_or_slug, token_data["sub"])

    project_id = str(project["_id"])
    slug = project.get("slug")

    # 1. Delete project document
    await db.projects.delete_one({"_id": project["_id"]})

    # 2. Cascade delete related records across all collections (supporting string and ObjectId formats)
    target_ids = [project_id]
    if ObjectId.is_valid(project_id):
        target_ids.append(ObjectId(project_id))

    for pid in target_ids:
        await db.builds.delete_many({"project_id": pid})
        await db.build_events.delete_many({"project_id": pid})
        await db.deployments.delete_many({"project_id": pid})
        await db.uploads.delete_many({"project_id": pid})
        await db.environment_variables.delete_many({"project_id": pid})
        await db.mobile_apps.delete_many({"project_id": pid})
        await db.mobile_builds.delete_many({"project_id": pid})
        await db.custom_domains.delete_many({"project_id": pid})
        await db.webhooks.delete_many({"project_id": pid})
        await db.runtime_logs.delete_many({"project_id": pid})
        await db.analytics.delete_many({"project_id": pid})

    # 3. Clean up physical directories on disk asynchronously in background thread
    def _cleanup_disk_sync():
        try:
            if slug:
                site_dep = os.path.join(settings.STORAGE_PATH, "deployments", slug)
                if os.path.exists(site_dep):
                    shutil.rmtree(site_dep, ignore_errors=True)
            ws_dir = os.path.join(settings.STORAGE_PATH, "workspaces", project_id)
            if os.path.exists(ws_dir):
                shutil.rmtree(ws_dir, ignore_errors=True)
        except Exception:
            pass

    asyncio.create_task(asyncio.to_thread(_cleanup_disk_sync))

    return None
