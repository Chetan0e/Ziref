from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime, timezone
from bson import ObjectId
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import re

import os
import shutil
import hashlib
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.models import ProjectStatus, BuildStatus
from services.api.core.redis_client import push_job
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
        active_url = p.get("active_url") or (f"http://{slug}.{settings.BASE_DOMAIN}" if p.get("active_deployment_id") else None)
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

    now_str = datetime.now(timezone.utc).isoformat() + "Z"
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

@router.post("/create-demo", status_code=status.HTTP_201_CREATED)
async def create_demo_project(token_data: Dict[str, Any] = Depends(get_current_user_token)):
    """Automatically sets up and triggers a build for the bundled React+Vite sample project."""
    db = get_database()
    now_str = datetime.now(timezone.utc).isoformat() + "Z"

    base_slug = "demo-react"
    slug = base_slug
    counter = 1
    while await db.projects.find_one({"slug": slug}):
        slug = f"{base_slug}-{counter}"
        counter += 1

    # 1. Create Project Record
    proj_doc = {
        "user_id": token_data["sub"],
        "name": f"React Vite Demo ({slug})",
        "slug": slug,
        "status": ProjectStatus.BUILD_QUEUED.value,
        "framework": "react",
        "language": "typescript",
        "package_manager": "pnpm",
        "build_command": "pnpm run build",
        "output_directory": "dist",
        "active_deployment_id": None,
        "active_url": None,
        "created_at": now_str,
        "updated_at": now_str
    }
    proj_res = await db.projects.insert_one(proj_doc)
    project_id = str(proj_res.inserted_id)

    # 2. Copy bundled fixture ZIP
    fixture_zip = os.path.abspath("tests/fixtures/ziref-demo-react.zip")
    upload_id = str(ObjectId())
    storage_rel_path = os.path.join("uploads", f"{upload_id}_ziref-demo-react.zip")
    storage_abs_path = os.path.join(settings.STORAGE_PATH, storage_rel_path)
    os.makedirs(os.path.dirname(storage_abs_path), exist_ok=True)
    shutil.copyfile(fixture_zip, storage_abs_path)

    with open(fixture_zip, "rb") as f:
        content = f.read()
    file_size = len(content)
    checksum = hashlib.sha256(content).hexdigest()

    # 3. Create Upload Record
    upload_doc = {
        "_id": ObjectId(upload_id),
        "project_id": project_id,
        "user_id": token_data["sub"],
        "filename": "ziref-demo-react.zip",
        "file_size": file_size,
        "checksum": checksum,
        "storage_path": storage_rel_path,
        "analysis": {
            "projectType": "web",
            "framework": "react",
            "language": "typescript",
            "packageManager": "pnpm",
            "runtime": "static",
            "buildCommand": "pnpm run build",
            "outputDirectory": "dist",
            "confidence": 0.98,
            "warnings": []
        },
        "created_at": now_str
    }
    await db.uploads.insert_one(upload_doc)

    # 4. Create Build Record
    build_doc = {
        "project_id": project_id,
        "upload_id": upload_id,
        "user_id": token_data["sub"],
        "status": BuildStatus.QUEUED.value,
        "framework": "react",
        "package_manager": "pnpm",
        "build_command": "pnpm run build",
        "output_directory": "dist",
        "exit_code": None,
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None,
        "created_at": now_str
    }
    b_res = await db.builds.insert_one(build_doc)
    build_id = str(b_res.inserted_id)

    # 5. Push to Redis build queue
    await push_job("build", {
        "build_id": build_id,
        "project_id": project_id,
        "upload_id": upload_id,
        "package_manager": "pnpm",
        "build_command": "pnpm run build",
        "output_directory": "dist"
    })

    return {
        "project_id": project_id,
        "slug": slug,
        "build_id": build_id,
        "message": "Demo project created and build queued successfully!"
    }

@router.post("/import-git", status_code=status.HTTP_201_CREATED)
async def import_git_project(payload: GitImportRequest, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    """Imports a project from a public Git repository, analyzes it, and launches the build."""
    db = get_database()
    now_str = datetime.now(timezone.utc).isoformat() + "Z"

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

        build_cmd = analysis.buildCommand or "npm run build"
        out_dir = analysis.outputDirectory or "dist"

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

@router.post("/{project_id}/redeploy", status_code=status.HTTP_202_ACCEPTED)
async def redeploy_project(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    """Triggers a new build and deployment using the project's most recent source upload."""
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Find latest upload
    latest_upload = await db.uploads.find_one({"project_id": project_id}, sort=[("created_at", -1)])
    if not latest_upload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No source uploads found for this project")

    now_str = datetime.now(timezone.utc).isoformat() + "Z"
    upload_id = str(latest_upload["_id"])
    build_cmd = project.get("build_command") or "npm run build"
    out_dir = project.get("output_directory") or "dist"

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
        {"_id": ObjectId(project_id)},
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
    query = {"user_id": token_data["sub"]}
    if ObjectId.is_valid(id_or_slug):
        query["_id"] = ObjectId(id_or_slug)
    else:
        query["slug"] = id_or_slug

    project = await db.projects.find_one(query)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    slug = project["slug"]
    active_url = project.get("active_url") or (f"http://{slug}.{settings.BASE_DOMAIN}" if project.get("active_deployment_id") else None)

    return ProjectResponse(
        id=str(project["_id"]),
        name=project["name"],
        slug=slug,
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

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, payload: ProjectUpdate, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    updates = {}
    if payload.name:
        updates["name"] = payload.name.strip()
    if payload.build_command is not None:
        updates["build_command"] = payload.build_command
    if payload.output_directory is not None:
        updates["output_directory"] = payload.output_directory

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat() + "Z"
        await db.projects.update_one(
            {"_id": ObjectId(project_id), "user_id": token_data["sub"]},
            {"$set": updates}
        )

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

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
        active_url=project.get("active_url"),
        created_at=project.get("created_at", ""),
        updated_at=project.get("updated_at", "")
    )

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    res = await db.projects.delete_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Cascade delete related records
    await db.builds.delete_many({"project_id": project_id})
    await db.deployments.delete_many({"project_id": project_id})
    await db.uploads.delete_many({"project_id": project_id})
    await db.environment_variables.delete_many({"project_id": project_id})
    await db.mobile_apps.delete_many({"project_id": project_id})

    return None
