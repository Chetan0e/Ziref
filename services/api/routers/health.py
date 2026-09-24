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
