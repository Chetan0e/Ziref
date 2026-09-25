import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from bson import ObjectId
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse, FileResponse

logger = logging.getLogger("ziref.apps")

from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.models import MobileAppStatus
from services.api.core.redis_client import push_job, subscribe_events
from services.api.schemas.apps import MobileAppCreate, MobileAppResponse, MobileBuildResponse

router = APIRouter(tags=["Appify (Mobile)"])

@router.get("/projects/{project_id}/apps", response_model=List[MobileAppResponse])
async def list_project_apps(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    cursor = db.mobile_apps.find({"project_id": project_id, "user_id": token_data["sub"]})
    apps = []
    async for a in cursor:
        apps.append(MobileAppResponse(
            id=str(a["_id"]),
            project_id=a["project_id"],
            app_name=a["app_name"],
            package_id=a["package_id"],
            version=a.get("version", "1.0.0"),
            version_code=a.get("version_code", 1),
            theme=a.get("theme", "system"),
            orientation=a.get("orientation", "portrait"),
            permissions=a.get("permissions", []),
            website_url=a.get("website_url", ""),
            created_at=a.get("created_at", "")
        ))
    return apps

@router.post("/projects/{project_id}/apps", response_model=MobileAppResponse, status_code=status.HTTP_201_CREATED)
async def create_mobile_app(
    project_id: str,
    payload: MobileAppCreate,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    slug = project["slug"]
    website_url = project.get("active_url") or f"http://{slug}.{settings.BASE_DOMAIN}"
    now_str = utc_now_iso()

    doc = {
        "project_id": project_id,
        "user_id": token_data["sub"],
        "app_name": payload.app_name.strip(),
        "package_id": payload.package_id.strip(),
        "version": payload.version,
        "version_code": payload.version_code,
        "theme": payload.theme,
        "orientation": payload.orientation,
        "permissions": payload.permissions or [],
        "website_url": website_url,
        "created_at": now_str,
        "updated_at": now_str
    }

    res = await db.mobile_apps.insert_one(doc)
    doc["_id"] = res.inserted_id

    return MobileAppResponse(
        id=str(doc["_id"]),
        project_id=doc["project_id"],
        app_name=doc["app_name"],
        package_id=doc["package_id"],
        version=doc["version"],
        version_code=doc["version_code"],
        theme=doc["theme"],
        orientation=doc["orientation"],
        permissions=doc.get("permissions", []),
        website_url=doc["website_url"],
        created_at=doc["created_at"]
    )

@router.post("/apps/{app_id}/build", response_model=MobileBuildResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_mobile_build(app_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(app_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid app ID")

    app_doc = await db.mobile_apps.find_one({"_id": ObjectId(app_id), "user_id": token_data["sub"]})
    if not app_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mobile app config not found")

    now_str = utc_now_iso()
    build_doc = {
        "mobile_app_id": app_id,
        "project_id": app_doc["project_id"],
        "user_id": token_data["sub"],
        "status": MobileAppStatus.APP_QUEUED.value,
        "build_target": "android",
        "apk_artifact_id": None,
        "source_artifact_id": None,
        "logs": [],
        "started_at": None,
        "completed_at": None,
        "error_message": None,
        "created_at": now_str
    }

    res = await db.mobile_builds.insert_one(build_doc)
    mobile_build_id = str(res.inserted_id)

    # Enqueue job to Redis
    await push_job("app_build", {
        "mobile_build_id": mobile_build_id,
        "mobile_app_id": app_id,
        "project_id": app_doc["project_id"]
    })

    return MobileBuildResponse(
        id=mobile_build_id,
        mobile_app_id=app_id,
        project_id=app_doc["project_id"],
        status=MobileAppStatus.APP_QUEUED,
        created_at=now_str
    )

@router.get("/mobile-builds/{build_id}", response_model=MobileBuildResponse)
async def get_mobile_build(build_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    b = None
    if ObjectId.is_valid(build_id):
        b = await db.mobile_builds.find_one({"_id": ObjectId(build_id)})
    if not b:
        b = await db.mobile_builds.find_one({"_id": build_id})
    if not b or (b.get("user_id") and b.get("user_id") != token_data["sub"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")

    apk_dl = f"/api/v1/mobile-builds/{build_id}/download/apk" if b.get("apk_artifact_id") else None
    src_dl = f"/api/v1/mobile-builds/{build_id}/download/source" if b.get("source_artifact_id") else None

    return MobileBuildResponse(
        id=str(b["_id"]),
        mobile_app_id=b["mobile_app_id"],
        project_id=b["project_id"],
        status=b["status"],
        build_target=b.get("build_target", "android"),
        apk_artifact_id=b.get("apk_artifact_id"),
        source_artifact_id=b.get("source_artifact_id"),
        apk_download_url=apk_dl,
        source_download_url=src_dl,
        error_message=b.get("error_message"),
        started_at=b.get("started_at"),
        completed_at=b.get("completed_at"),
        created_at=b.get("created_at", "")
    )

@router.get("/mobile-builds/{build_id}/logs/stream")
async def stream_mobile_build_logs(build_id: str):
    async def event_generator():
        db = get_database()
        b = await db.mobile_builds.find_one({"_id": ObjectId(build_id)})
        if b and b.get("logs"):
            for evt in b["logs"]:
                yield f"data: {json.dumps(evt)}\n\n"

        if b and b.get("status") in [MobileAppStatus.APP_READY.value, MobileAppStatus.APP_FAILED.value]:
            yield f"data: {json.dumps({'stage': 'done', 'level': 'info', 'message': '[STREAM_CLOSED]'})}\n\n"
            return

        try:
            async for live_evt in subscribe_events(f"mobile:{build_id}:logs"):
                yield f"data: {json.dumps(live_evt)}\n\n"
                if live_evt.get("stage") == "completed" or "failed" in live_evt.get("message", "").lower():
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.api_route("/mobile-builds/{build_id}/download", methods=["GET", "HEAD"])
@router.api_route("/mobile-builds/{build_id}/download/{artifact_type}", methods=["GET", "HEAD"])
async def download_mobile_artifact(build_id: str, artifact_type: str = "apk"):
    db = get_database()
    b = None
    if ObjectId.is_valid(build_id):
        b = await db.mobile_builds.find_one({"_id": ObjectId(build_id)})
    if not b:
        b = await db.mobile_builds.find_one({"_id": build_id})

    is_apk = artifact_type.lower() in ["apk", "default", ""]
    expected_filename = f"app-debug-{build_id}.apk" if is_apk else f"app-source-{build_id}.zip"
    direct_disk_path = os.path.normpath(os.path.join(settings.STORAGE_PATH, "mobile", expected_filename))

    abs_path = None
    if b:
        rel_path = b.get("apk_artifact_id") if is_apk else b.get("source_artifact_id")
        if rel_path:
            candidate = os.path.normpath(os.path.join(settings.STORAGE_PATH, rel_path))
            if os.path.exists(candidate):
                abs_path = candidate

    if not abs_path and os.path.exists(direct_disk_path):
        abs_path = direct_disk_path

    if not abs_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file not found")

    filename = os.path.basename(abs_path)
    media_type = "application/vnd.android.package-archive" if is_apk else "application/zip"
    return FileResponse(abs_path, media_type=media_type, filename=filename)
