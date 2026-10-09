import uuid
import time
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import connect_to_database, close_database_connection, get_database
from services.api.core.redis_client import pop_job, get_redis, close_redis
from services.api.routers import auth, projects, uploads, builds, deployments, env, apps, health, domains, runtime_logs, webhooks, analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("ziref.api")

async def _publish_worker_heartbeat():
    try:
        docker_available = False
        try:
            import docker
            c = docker.from_env()
            c.ping()
            docker_available = True
        except Exception:
            docker_available = False

        heartbeat_doc = {
            "status": "online",
            "timestamp": utc_now_iso(),
            "time": time.time(),
            "docker_available": docker_available,
            "sandbox_mode": "docker" if docker_available else "subprocess"
        }
        redis_client = await get_redis()
        if redis_client:
            await redis_client.set("ziref:worker:heartbeat", json.dumps(heartbeat_doc), ex=25)
        db = get_database()
        await db.system_status.update_one({"_id": "worker_heartbeat"}, {"$set": heartbeat_doc}, upsert=True)
    except Exception as e:
        logger.debug(f"Heartbeat write note: {e}")

async def _recover_stalled_jobs():
    try:
        from services.api.core.redis_client import push_job
        db = get_database()
        cursor = db.builds.find({"status": "QUEUED"})
        recovered_builds = 0
        async for b in cursor:
            await push_job("build", {
                "build_id": str(b["_id"]),
                "project_id": b["project_id"],
                "upload_id": b["upload_id"],
                "package_manager": b.get("package_manager"),
                "build_command": b.get("build_command"),
                "output_directory": b.get("output_directory")
            })
            recovered_builds += 1
        if recovered_builds > 0:
            logger.info(f"[Worker Engine] Recovered {recovered_builds} previously queued build jobs.")

        m_cursor = db.mobile_builds.find({"status": "APP_QUEUED"})
        recovered_apps = 0
        async for mb in m_cursor:
            await push_job("app_build", {
                "mobile_build_id": str(mb["_id"]),
                "mobile_app_id": mb["mobile_app_id"],
                "project_id": mb["project_id"]
            })
            recovered_apps += 1
        if recovered_apps > 0:
            logger.info(f"[Worker Engine] Recovered {recovered_apps} previously queued mobile app build jobs.")
    except Exception as e:
        logger.debug(f"Job recovery note: {e}")

async def _embedded_worker_runner():
    logger.info("Embedded worker engine started. Monitoring build, deploy, and mobile APK queues.")
    await _recover_stalled_jobs()
    last_heartbeat = 0.0

    while True:
        try:
            now = time.time()
            db = get_database()
            # If external worker daemon is active, yield queue polling to it
            hb = await db.system_status.find_one({"_id": "worker_heartbeat"})
            if hb and hb.get("source") == "worker_daemon" and (now - hb.get("time", 0)) < 15.0:
                await asyncio.sleep(2.0)
                continue

            if now - last_heartbeat >= 4.0:
                last_heartbeat = now
                await _publish_worker_heartbeat()

            # 1. Check build queue
            build_job = await pop_job("build", timeout=1)
            if build_job:
                logger.info(f"[Worker Engine] Processing build job: {build_job.get('build_id')}")
                from services.builder.build_executor import build_pipeline_executor
                asyncio.create_task(build_pipeline_executor.process_build_job(build_job))
                continue

            # 2. Check deploy queue
            deploy_job = await pop_job("deploy", timeout=1)
            if deploy_job:
                logger.info(f"[Worker Engine] Processing deploy job: {deploy_job.get('build_id')}")
                from services.deployer.deployer_service import deployer_service
                asyncio.create_task(deployer_service.process_deploy_job(deploy_job))
                continue

            # 3. Check mobile APK build queue
            app_job = await pop_job("app_build", timeout=1)
            if app_job:
                logger.info(f"[Worker Engine] Processing mobile APK build job: {app_job.get('mobile_build_id')}")
                from services.app_builder.apk_builder import mobile_build_pipeline
                asyncio.create_task(mobile_build_pipeline.process_mobile_build_job(app_job))
                continue

            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[Worker Engine] Loop exception: {e}")
            await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Ziref API...")
    await connect_to_database()
    worker_task = asyncio.create_task(_embedded_worker_runner())
    yield
    logger.info("Shutting down Ziref API...")
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await close_database_connection()
    await close_redis()

app = FastAPI(
    title="Ziref API",
    description="Developer Infrastructure & Deployment Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Logging Middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    start_time = time.time()

    response = await call_next(request)

    duration = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration}ms"
    return response

# Standardized Error Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {},
                "requestId": req_id
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload.",
                "details": {"errors": exc.errors()},
                "requestId": req_id
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"Unhandled exception [req_id={req_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected internal error occurred.",
                "details": {},
                "requestId": req_id
            }
        }
    )

# Site Asset Referer Fallback Middleware
# If a static site loaded under /sites/{slug}/ requests a root-relative asset (/style.css, /assets/...) that returns 404,
# inspect Referer and redirect to /sites/{slug}/{path}
@app.middleware("http")
async def site_asset_referer_fallback_middleware(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 404 and not request.url.path.startswith("/api/") and not request.url.path.startswith("/docs"):
        referer = request.headers.get("referer", "")
        if "/sites/" in referer:
            try:
                import re
                from fastapi.responses import RedirectResponse
                match = re.search(r"/sites/([^/?#]+)", referer)
                if match:
                    ref_slug = match.group(1)
                    target_url = f"/sites/{ref_slug}{request.url.path}"
                    return RedirectResponse(url=target_url, status_code=302)
            except Exception:
                pass
    return response

# Include Routers under /api/v1
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(builds.router, prefix="/api/v1")
app.include_router(deployments.router, prefix="/api/v1")
app.include_router(env.router, prefix="/api/v1")
app.include_router(apps.router, prefix="/api/v1")
app.include_router(domains.router, prefix="/api/v1")
app.include_router(runtime_logs.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(health.router)

from services.deployer.site_router import route_site

# Dynamic Site Preview & Hosting Gateway on port 8000
@app.api_route("/sites", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/sites/{full_path:path}", methods=["GET", "HEAD", "OPTIONS"])
async def site_router_preview_gateway(request: Request, full_path: str = ""):
    return await route_site(request, full_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="0.0.0.0", port=8000, reload=True)
