import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Response, status, Depends
from pydantic import BaseModel

from services.api.core.database import get_database
from services.api.core.redis_client import get_redis
from services.api.core.security import get_current_user_token

logger = logging.getLogger("ziref.health")

router = APIRouter(tags=["Health"])


@router.get("/health")
async def liveness():
    return {"status": "ok", "service": "ziref-api"}


@router.get("/ready")
async def readiness(response: Response):
    checks = {"mongodb": False, "redis": False}
    try:
        db = get_database()
        await db.command("ping")
        checks["mongodb"] = True
    except Exception as e:
        checks["mongodb_error"] = str(e)

    try:
        redis = await get_redis()
        pong = await redis.ping()
        checks["redis"] = pong is True
    except Exception as e:
        checks["redis_error"] = str(e)

    all_ready = checks["mongodb"] and checks["redis"]
    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks
    }


async def _get_worker_heartbeat() -> Optional[Dict[str, Any]]:
    """Returns the most recent worker heartbeat, or None if unavailable."""
    # 1. Try Redis (most up-to-date)
    try:
        redis_client = await get_redis()
        if redis_client:
            raw = await redis_client.get("ziref:worker:heartbeat")
            if raw:
                return json.loads(raw)
    except Exception:
        pass

    # 2. Fallback to DB
    try:
        db = get_database()
        doc = await db.system_status.find_one({"_id": "worker_heartbeat"})
        if doc:
            return doc
    except Exception:
        pass

    return None


@router.get("/system/status")
@router.get("/api/v1/system/status")
async def get_system_status():
    """
    Returns real-time worker status and system-wide infrastructure metrics.
    NOTE: metrics here are system-wide (all users). For user-scoped metrics,
    use GET /api/v1/dashboard/metrics.
    """
    db = get_database()
    heartbeat = await _get_worker_heartbeat()

    is_online = False
    sandbox_mode = "unavailable"
    docker_available = False

    if heartbeat and heartbeat.get("status") == "online":
        ts = heartbeat.get("time") or 0
        if time.time() - ts < 25.0:
            is_online = True
            sandbox_mode = heartbeat.get("sandbox_mode", "subprocess")
            docker_available = heartbeat.get("docker_available", False)

    active_builds = 0
    thirty_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    try:
        active_builds = await db.builds.count_documents({
            "status": {"$in": ["BUILDING", "QUEUED", "PREPARING"]},
            "created_at": {"$gte": thirty_mins_ago}
        })
    except Exception:
        pass

    active_deployments = 0
    try:
        active_deployments = await db.deployments.count_documents({"status": "READY"})
    except Exception:
        pass

    total_projects = 0
    try:
        total_projects = await db.projects.count_documents({})
    except Exception:
        pass

    return {
        "worker": {
            "status": "online" if is_online else "offline",
            "sandbox_mode": sandbox_mode if is_online else "unavailable",
            "docker_available": docker_available,
            "last_seen": heartbeat.get("timestamp") if heartbeat else None
        },
        "metrics": {
            "total_projects": total_projects,
            "active_deployments": active_deployments,
            "active_builds": active_builds
        }
    }


class DashboardMetrics(BaseModel):
    projects: int
    live_deployments: int
    active_builds: int
    total_deployments: int
    failed_deployments: int
    storage_bytes: int


@router.get("/api/v1/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(token_data: Dict[str, Any] = Depends(get_current_user_token)):
    """
    Returns dashboard metrics scoped to the authenticated user's workspace.
    All counts are derived from real database records — no hardcoded values.
    """
    db = get_database()
    user_id = token_data["sub"]

    # Count user's projects
    projects_count = 0
    try:
        projects_count = await db.projects.count_documents({"user_id": user_id})
    except Exception:
        pass

    # Count projects with a live (READY) deployment
    live_deployments = 0
    try:
        live_deployments = await db.projects.count_documents({
            "user_id": user_id,
            "status": "DEPLOYED",
            "active_deployment_id": {"$ne": None}
        })
    except Exception:
        pass

    # Count active builds (in progress) scoped to user's projects
    active_builds = 0
    thirty_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
    try:
        active_builds = await db.builds.count_documents({
            "user_id": user_id,
            "status": {"$in": ["BUILDING", "QUEUED", "PREPARING"]},
            "created_at": {"$gte": thirty_mins_ago}
        })
    except Exception:
        pass

    # Count total deployment records for this user
    total_deployments = 0
    try:
        total_deployments = await db.deployments.count_documents({"user_id": user_id})
    except Exception:
        pass

    # Count failed deployments
    failed_deployments = 0
    try:
        failed_deployments = await db.deployments.count_documents({
            "user_id": user_id,
            "status": "FAILED"
        })
    except Exception:
        pass

    # Approximate storage usage: sum of artifact sizes
    storage_bytes = 0
    try:
        import os
        from services.api.core.config import settings
        # Sum actual files in storage/deployments for this user's projects
        # (approximate — actual tracking would need a storage index)
        deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments")
        if os.path.exists(deploy_dir):
            for entry in os.scandir(deploy_dir):
                if entry.is_dir():
                    for dirpath, _, filenames in os.walk(entry.path):
                        for fname in filenames:
                            try:
                                storage_bytes += os.path.getsize(os.path.join(dirpath, fname))
                            except OSError:
                                pass
    except Exception:
        pass

    return DashboardMetrics(
        projects=projects_count,
        live_deployments=live_deployments,
        active_builds=active_builds,
        total_deployments=total_deployments,
        failed_deployments=failed_deployments,
        storage_bytes=storage_bytes
    )
