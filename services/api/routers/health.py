from fastapi import APIRouter, Response, status
from services.api.core.database import get_database
from services.api.core.redis_client import get_redis

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

@router.get("/system/status")
@router.get("/api/v1/system/status")
async def get_system_status():
    """Returns actual real-time worker, sandbox, and active build metrics."""
    import time
    import json
    db = get_database()
    heartbeat = None

    # 1. Try Redis
    try:
        redis_client = await get_redis()
        if redis_client:
            raw = await redis_client.get("ziref:worker:heartbeat")
            if raw:
                heartbeat = json.loads(raw)
    except Exception:
        pass

    # 2. Try DB fallback
    if not heartbeat:
        try:
            doc = await db.system_status.find_one({"_id": "worker_heartbeat"})
            if doc:
                heartbeat = doc
        except Exception:
            pass

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
    if is_online:
        from datetime import datetime, timezone, timedelta
        thirty_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        try:
            active_builds = await db.builds.count_documents({
                "status": {"$in": ["BUILDING", "QUEUED", "PREPARING"]},
                "created_at": {"$gte": thirty_mins_ago}
            })
        except Exception:
            try:
                active_builds = sum(
                    1 for b in db.builds.data.get("builds", [])
                    if b.get("status") in ["BUILDING", "QUEUED", "PREPARING"]
                    and b.get("created_at", "") >= thirty_mins_ago
                )
            except Exception:
                pass

    active_deployments = 0
    try:
        active_deployments = await db.deployments.count_documents({"status": {"$in": ["READY", "DEPLOYED"]}})
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
