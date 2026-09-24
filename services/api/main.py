import uuid
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from services.api.core.config import settings
from services.api.core.database import connect_to_database, close_database_connection
from services.api.core.redis_client import close_redis
from services.api.routers import auth, projects, uploads, builds, deployments, env, apps, health, domains, runtime_logs, webhooks, analytics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("ziref.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Ziref API...")
    await connect_to_database()
    yield
    logger.info("Shutting down Ziref API...")
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
    allow_origins=["*"],  # Development / configurable
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

# Standardized Error Handlers (Section 24)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="0.0.0.0", port=8000, reload=True)
