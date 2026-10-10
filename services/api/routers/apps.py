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
from services.api.core.network import get_local_lan_ip
from services.api.core.deployment_url import deployment_url_service
from services.api.schemas.apps import MobileAppCreate, MobileAppResponse, MobileBuildResponse, NetworkInfoResponse

router = APIRouter(tags=["Appify (Mobile)"])


def _to_mobile_build_response(b: Dict[str, Any]) -> MobileBuildResponse:
    build_id = str(b["_id"])
    apk_dl = f"/api/v1/mobile-builds/{build_id}/download/apk" if b.get("apk_artifact_id") else None
    src_dl = f"/api/v1/mobile-builds/{build_id}/download/source" if b.get("source_artifact_id") else None
    return MobileBuildResponse(
        id=build_id,
        mobile_app_id=b["mobile_app_id"],
        project_id=b["project_id"],
        status=b["status"],
        build_target=b.get("build_target", "android"),
        apk_artifact_id=b.get("apk_artifact_id"),
        source_artifact_id=b.get("source_artifact_id"),
        apk_download_url=apk_dl,
        source_download_url=src_dl,
        apk_filename=b.get("apk_filename"),
        apk_sha256=b.get("apk_sha256"),
        apk_size_bytes=b.get("apk_size_bytes"),
        apk_package_name=b.get("apk_package_name"),
        apk_version_name=b.get("apk_version_name"),
        apk_version_code=b.get("apk_version_code"),
        apk_signed=b.get("apk_signed", False),
        apk_verified=b.get("apk_verified", False),
        apk_target_url=b.get("apk_target_url"),
        apk_url_is_localhost=b.get("apk_url_is_localhost", False),
        error_message=b.get("error_message"),
        started_at=b.get("started_at"),
        completed_at=b.get("completed_at"),
        created_at=b.get("created_at", "")
    )


@router.get("/projects/{project_id}/network-info", response_model=NetworkInfoResponse)
async def get_project_network_info(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    slug = "app"
    active_url = None
    active_dep_id = None
    if ObjectId.is_valid(project_id):
        project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
        if project:
            slug = project.get("slug", "app")
            active_url = project.get("active_url")
            active_dep_id = project.get("active_deployment_id")

    lan_ip = get_local_lan_ip()

    # Check if deployed static assets exist
    has_dep = False
    if active_dep_id:
        dep_dir = os.path.join(settings.STORAGE_PATH, "deployments", str(active_dep_id))
        if os.path.isdir(dep_dir) and os.path.isfile(os.path.join(dep_dir, "index.html")):
            has_dep = True
    if not has_dep and slug:
        slug_dir = os.path.join(settings.STORAGE_PATH, "deployments", slug)
        if os.path.isdir(slug_dir) and os.path.isfile(os.path.join(slug_dir, "index.html")):
            has_dep = True

    return NetworkInfoResponse(
        lan_ip=lan_ip,
        port=8000,
        lan_url=f"http://{lan_ip}:8000/sites/{slug}/",
        localhost_url=f"http://localhost:8000/sites/{slug}/",
        emulator_url=f"http://10.0.2.2:8000/sites/{slug}/",
        embedded_url="file:///android_asset/www/index.html",
        active_url=active_url,
        has_deployment=has_dep
    )



@router.get("/projects/{project_id}/apps", response_model=List[MobileAppResponse])
async def list_project_apps(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    cursor = db.mobile_apps.find({"project_id": project_id, "user_id": token_data["sub"]}).sort("created_at", -1)
    apps = []
    async for a in cursor:
        app_id_str = str(a["_id"])
        latest_b = await db.mobile_builds.find_one(
            {"mobile_app_id": app_id_str},
            sort=[("created_at", -1)]
        )
        latest_build_resp = _to_mobile_build_response(latest_b) if latest_b else None

        apps.append(MobileAppResponse(
            id=app_id_str,
            project_id=a["project_id"],
            app_name=a["app_name"],
            package_id=a["package_id"],
            version=a.get("version", "1.0.0"),
            version_code=a.get("version_code", 1),
            theme=a.get("theme", "system"),
            orientation=a.get("orientation", "portrait"),
            permissions=a.get("permissions", []),
            icon_base64=a.get("icon_base64"),
            website_url=a.get("website_url", ""),
            website_url_is_localhost=a.get("website_url_is_localhost", False),
            latest_build=latest_build_resp,
            updated_at=a.get("updated_at"),
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

    # Validate package ID
    pkg_valid, pkg_reason = deployment_url_service.sanitize_package_id(payload.package_id.strip())
    if not pkg_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid package ID: {pkg_reason}")

    # Validate app name
    name_valid, name_reason = deployment_url_service.sanitize_app_name(payload.app_name.strip())
    if not name_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid app name: {name_reason}")

    slug = project["slug"]
    lan_ip = get_local_lan_ip()

    # Determine target URL:
    # 1. Explicit user override from payload (e.g. selected LAN IP or custom domain)
    # 2. Existing active_url if it is public
    # 3. LAN IP URL if in local development mode so physical Wi-Fi devices work seamlessly
    # 4. Fallback to canonical development URL
    if payload.website_url and payload.website_url.strip():
        website_url = payload.website_url.strip()
    elif project.get("active_url") and not deployment_url_service.is_localhost_url(project.get("active_url")):
        website_url = project.get("active_url")
    else:
        if lan_ip and lan_ip != "127.0.0.1":
            website_url = f"http://{lan_ip}:8000/sites/{slug}/"
        else:
            website_url = project.get("active_url") or deployment_url_service.generate_public_url(slug)

    is_localhost = deployment_url_service.is_localhost_url(website_url)
    now_str = utc_now_iso()

    # Upsert: If mobile app already exists for this project, update it instead of creating duplicates
    existing_app = await db.mobile_apps.find_one({"project_id": project_id, "user_id": token_data["sub"]})
    if existing_app:
        update_fields: Dict[str, Any] = {
            "app_name": payload.app_name.strip(),
            "package_id": payload.package_id.strip().lower(),
            "version": payload.version,
            "version_code": payload.version_code,
            "theme": payload.theme,
            "orientation": payload.orientation,
            "permissions": payload.permissions or [],
            "website_url": website_url,
            "website_url_is_localhost": is_localhost,
            "updated_at": now_str
        }
        if payload.icon_base64 is not None:
            update_fields["icon_base64"] = payload.icon_base64

        await db.mobile_apps.update_one({"_id": existing_app["_id"]}, {"$set": update_fields})
        doc = await db.mobile_apps.find_one({"_id": existing_app["_id"]})
    else:
        doc = {
            "project_id": project_id,
            "user_id": token_data["sub"],
            "app_name": payload.app_name.strip(),
            "package_id": payload.package_id.strip().lower(),
            "version": payload.version,
            "version_code": payload.version_code,
            "theme": payload.theme,
            "orientation": payload.orientation,
            "permissions": payload.permissions or [],
            "icon_base64": payload.icon_base64,
            "website_url": website_url,
            "website_url_is_localhost": is_localhost,
            "created_at": now_str,
            "updated_at": now_str
        }
        res = await db.mobile_apps.insert_one(doc)
        doc["_id"] = res.inserted_id

    # Check for existing latest build to attach
    latest_b = await db.mobile_builds.find_one(
        {"mobile_app_id": str(doc["_id"])},
        sort=[("created_at", -1)]
    )
    latest_build_resp = _to_mobile_build_response(latest_b) if latest_b else None

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
        icon_base64=doc.get("icon_base64"),
        website_url=doc["website_url"],
        website_url_is_localhost=doc.get("website_url_is_localhost", False),
        latest_build=latest_build_resp,
        updated_at=doc.get("updated_at"),
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

    return _to_mobile_build_response(b)

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
    """
    Download APK or source ZIP for a completed mobile build.
    Returns proper Content-Disposition, media type, and SHA-256 digest header.
    """
    from fastapi.responses import Response as FastAPIResponse
    db = get_database()
    b = None
    if ObjectId.is_valid(build_id):
        b = await db.mobile_builds.find_one({"_id": ObjectId(build_id)})
    if not b:
        b = await db.mobile_builds.find_one({"_id": build_id})

    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build record not found")

    if b.get("status") not in [MobileAppStatus.APP_READY.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Build is not ready for download (status: {b.get('status')})"
        )

    is_apk = artifact_type.lower() in ["apk", "default", ""]

    abs_path = None
    if is_apk:
        rel_path = b.get("apk_artifact_id")
        if rel_path:
            candidate = os.path.normpath(os.path.join(settings.STORAGE_PATH, rel_path))
            if os.path.exists(candidate):
                abs_path = candidate
        # Legacy fallback for builds created before apk_filename was standardized
        if not abs_path:
            legacy_path = os.path.normpath(
                os.path.join(settings.STORAGE_PATH, "mobile", f"app-debug-{build_id}.apk")
            )
            if os.path.exists(legacy_path):
                abs_path = legacy_path
    else:
        rel_path = b.get("source_artifact_id")
        if rel_path:
            candidate = os.path.normpath(os.path.join(settings.STORAGE_PATH, rel_path))
            if os.path.exists(candidate):
                abs_path = candidate
        if not abs_path:
            legacy_path = os.path.normpath(
                os.path.join(settings.STORAGE_PATH, "mobile", f"app-source-{build_id}.zip")
            )
            if os.path.exists(legacy_path):
                abs_path = legacy_path

    if not abs_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact file not found on storage")

    filename = b.get("apk_filename") if is_apk else os.path.basename(abs_path)
    if not filename:
        filename = os.path.basename(abs_path)

    media_type = "application/vnd.android.package-archive" if is_apk else "application/zip"

    # Add SHA-256 digest header if available (for integrity verification)
    headers = {}
    if is_apk and b.get("apk_sha256"):
        headers["X-Content-SHA256"] = b["apk_sha256"]
    if is_apk and b.get("apk_package_name"):
        headers["X-APK-Package"] = b["apk_package_name"]
    if is_apk and b.get("apk_version_name"):
        headers["X-APK-Version"] = b["apk_version_name"]
    if is_apk and b.get("apk_url_is_localhost"):
        headers["X-APK-Warning"] = "target-url-is-localhost"

    return FileResponse(abs_path, media_type=media_type, filename=filename, headers=headers)

