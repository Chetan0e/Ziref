import os
import glob
import time
import asyncio
import mimetypes
import logging
from typing import Optional, Tuple
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from bson import ObjectId

from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import connect_to_database, close_database_connection, get_database
from services.api.core.redis_client import get_project_routing

logger = logging.getLogger("ziref.router")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_database()
    yield
    await close_database_connection()

from starlette.middleware.gzip import GZipMiddleware

app = FastAPI(title="Ziref Dynamic Site Router", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)

async def _resolve_custom_domain(host: str) -> Optional[str]:
    """Resolves an external custom domain (e.g. app.example.com) to a project slug."""
    try:
        db = get_database()
        domain_doc = await db.custom_domains.find_one({"domain": host})
        if domain_doc and domain_doc.get("project_id"):
            project = await db.projects.find_one({"_id": ObjectId(domain_doc["project_id"])})
            if project and project.get("slug"):
                return project["slug"]
    except Exception as e:
        logger.warning(f"Custom domain lookup error for {host}: {e}")
    return None

KNOWN_MIME_TYPES = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".ts": "text/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".htm": "text/html",
    ".json": "application/json",
    ".map": "application/json",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".wasm": "application/wasm",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".xml": "application/xml",
    ".txt": "text/plain",
}

def resolve_media_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in KNOWN_MIME_TYPES:
        return KNOWN_MIME_TYPES[ext]
    guessed, _ = mimetypes.guess_type(filename)
    if guessed and guessed != "application/octet-stream":
        return guessed
    return "text/plain" if ext in [".txt", ".log", ".md"] else "application/octet-stream"

async def _extract_slug_from_request(request: Request) -> Tuple[Optional[str], str]:
    """
    Extracts project slug either from Host header (subdomain/custom domain) or URL path prefix.
    Returns: (slug, subpath)
    """
    host = request.headers.get("host", "").split(":")[0].lower()
    path = request.url.path

    # 1. Path-based routing: /sites/{slug}/...
    if path.startswith("/sites/"):
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            slug = parts[1]
            subpath = "/".join(parts[2:])
            # Strip any repeated 'sites/<slug>/' or '<slug>/' prefixes from subpath
            pattern1 = f"sites/{slug}/"
            pattern2 = f"{slug}/"
            while subpath.startswith(pattern1):
                subpath = subpath[len(pattern1):]
            while subpath.startswith("sites/"):
                subpath = subpath[6:]
            while subpath.startswith(pattern2):
                subpath = subpath[len(pattern2):]
            return slug, subpath

    # 2. Host-based subdomain routing: {slug}.localhost or {slug}.localtest.me
    base = settings.BASE_DOMAIN.split(":")[0].lower()
    if host.endswith("." + base):
        slug = host[: -(len(base) + 1)]
        return slug, path.lstrip("/")

    if host.endswith(".localtest.me"):
        slug = host.split(".")[0]
        return slug, path.lstrip("/")

    if host.endswith(".localhost"):
        slug = host.split(".")[0]
        return slug, path.lstrip("/")

    # 3. Custom domain mapping check
    custom_slug = await _resolve_custom_domain(host)
    if custom_slug:
        return custom_slug, path.lstrip("/")

    return None, path.lstrip("/")

async def _resolve_active_deployment_id(slug: str) -> Optional[str]:
    # 1. Check Redis cache first
    try:
        routing = await get_project_routing(slug)
        if routing and "deployment_id" in routing:
            return routing["deployment_id"]
    except Exception as e:
        logger.warning(f"Redis routing lookup error: {e}")

    # 2. Fallback to Database
    try:
        db = get_database()
        project = await db.projects.find_one({"slug": slug})
        if project and project.get("active_deployment_id"):
            return str(project["active_deployment_id"])

        # Check deployments collection directly by subdomain
        dep = await db.deployments.find_one(
            {"subdomain": slug, "status": "READY"},
            sort=[("created_at", -1)]
        )
        if dep:
            return str(dep["_id"])

        if project:
            dep_by_pid = await db.deployments.find_one(
                {"project_id": str(project["_id"]), "status": "READY"},
                sort=[("created_at", -1)]
            )
            if dep_by_pid:
                return str(dep_by_pid["_id"])
    except Exception as e:
        logger.error(f"Database routing lookup error: {e}")

    # 3. Direct filesystem check: storage/deployments/{slug}
    try:
        variants = [slug, slug.replace("_", "-"), slug.replace("-", "_")]
        for variant in variants:
            slug_dir = os.path.join(settings.STORAGE_PATH, "deployments", variant)
            if os.path.exists(slug_dir) and os.path.isdir(slug_dir):
                return variant
    except Exception:
        pass

    return None

def _apply_security_and_cache_headers(res: Response, clean_subpath: str) -> Response:
    # Standard production security headers
    res.headers["X-Content-Type-Options"] = "nosniff"
    res.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Allow embedding in local dashboard previews and mobile simulator
    res.headers["Content-Security-Policy"] = "frame-ancestors 'self' http://localhost:* http://127.0.0.1:* *;"
    res.headers["X-XSS-Protection"] = "1; mode=block"
    res.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    res.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    # Intelligent cache control headers
    ext = os.path.splitext(clean_subpath)[1].lower()
    if ext in [".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".woff2", ".woff", ".ttf", ".ico"]:
        res.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif ext in [".html", ".htm"] or not ext:
        res.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    else:
        res.headers["Cache-Control"] = "public, max-age=86400"
    return res

@app.api_route("/{full_path:path}", methods=["GET", "HEAD", "OPTIONS"])
async def route_site(request: Request, full_path: str = ""):
    # Ensure directory requests end with a trailing slash so relative links/assets resolve correctly
    path = request.url.path
    if path.startswith("/sites/"):
        parts = path.strip("/").split("/")
        if len(parts) == 2 and not path.endswith("/"):
            target = path + "/"
            if request.url.query:
                target += f"?{request.url.query}"
            return RedirectResponse(url=target, status_code=302)

    slug, subpath = await _extract_slug_from_request(request)

    if not slug:
        res = HTMLResponse(
            status_code=404,
            content="""<!DOCTYPE html>
<html>
<head><title>Ziref — Router</title><style>body{font-family:sans-serif;background:#09090b;color:#fafafa;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}div{text-align:center;max-width:480px;padding:2rem;background:#18181b;border:1px solid #27272a;border-radius:8px}h1{color:#60a5fa}p{color:#a1a1aa}</style></head>
<body><div><h1>Ziref Site Router</h1><p>No project matched this hostname or URL. Ensure your project is deployed and the subdomain or path is correct.</p></div></body>
</html>"""
        )
        return _apply_security_and_cache_headers(res, "")

    deployment_id = await _resolve_active_deployment_id(slug)
    if not deployment_id:
        res = HTMLResponse(
            status_code=404,
            content=f"""<!DOCTYPE html>
<html>
<head><title>Ziref — Project Not Ready</title><style>body{{font-family:sans-serif;background:#09090b;color:#fafafa;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}div{{text-align:center;max-width:500px;padding:2rem;background:#18181b;border:1px solid #27272a;border-radius:8px}}h1{{color:#f59e0b}}p{{color:#a1a1aa}}code{{color:#38bdf8}}</style></head>
<body><div><h1>Project Not Ready</h1><p>Project <code>{slug}</code> does not currently have an active deployment. Please verify your build completed successfully in the Ziref Dashboard.</p></div></body>
</html>"""
        )
        return _apply_security_and_cache_headers(res, "")

    deploy_root = os.path.abspath(os.path.join(settings.STORAGE_PATH, "deployments", deployment_id))
    if not os.path.exists(deploy_root):
        deploy_root = os.path.abspath(os.path.join(settings.STORAGE_PATH, "deployments", slug))
    if not os.path.exists(deploy_root):
        res = HTMLResponse(
            status_code=500,
            content="<h1>Deployment Artifact Missing on Disk</h1>"
        )
        return _apply_security_and_cache_headers(res, "")

    # Clean requested path
    clean_subpath = os.path.normpath(subpath).lstrip("/\\") if subpath else ""
    target_file = os.path.join(deploy_root, clean_subpath)

    # Determine response
    res = None
    start_time = time.time()

    # 1. Direct file match
    if os.path.isfile(target_file):
        res = FileResponse(target_file, media_type=resolve_media_type(target_file))

    # 1b. Check if asset exists inside a subfolder in deploy_root
    elif clean_subpath:
        sub_matches = glob.glob(os.path.join(deploy_root, "**", os.path.basename(clean_subpath)), recursive=True)
        if sub_matches and os.path.isfile(sub_matches[0]):
            res = FileResponse(sub_matches[0], media_type=resolve_media_type(sub_matches[0]))

    # 2. Directory match -> look for index.html
    if res is None and os.path.isdir(target_file):
        index_file = os.path.join(target_file, "index.html")
        if os.path.isfile(index_file):
            res = FileResponse(index_file, media_type="text/html")

    # 3. Root index.html check (SPA fallback)
    if res is None:
        index_html = os.path.join(deploy_root, "index.html")
        if os.path.isfile(index_html):
            ext = os.path.splitext(clean_subpath)[1]
            if not ext or ext.lower() in [".html", ".htm"]:
                res = FileResponse(index_html, media_type="text/html")
        else:
            # Check nested index.html
            nested_html = glob.glob(os.path.join(deploy_root, "**", "index.html"), recursive=True)
            if nested_html:
                res = FileResponse(nested_html[0], media_type="text/html")

    if res is None:
        ext = os.path.splitext(clean_subpath)[1].lower()
        if ext in [".js", ".mjs", ".css", ".json", ".svg", ".wasm"]:
            res = Response(
                status_code=404,
                content=f"/* 404: Asset '{subpath}' not found */" if ext in [".js", ".css"] else "{}",
                media_type=resolve_media_type(clean_subpath)
            )
        else:
            res = HTMLResponse(
                status_code=404,
                content=f"<h1>404 Not Found</h1><p>Asset '{subpath}' not found in deployment {deployment_id}.</p>"
            )

    # Apply security and cache headers
    _apply_security_and_cache_headers(res, clean_subpath)

    # Log runtime traffic asynchronously
    duration_ms = round((time.time() - start_time) * 1000, 2)
    asyncio.create_task(_log_access_event(
        slug=slug,
        deployment_id=deployment_id,
        method=request.method,
        path=request.url.path,
        status_code=res.status_code if hasattr(res, "status_code") else 200,
        duration_ms=duration_ms,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown")
    ))

    return res

async def _log_access_event(slug: str, deployment_id: str, method: str, path: str, status_code: int, duration_ms: float, client_ip: str, user_agent: str):
    try:
        from datetime import datetime, timezone
        from services.api.core.redis_client import publish_event
        db = get_database()
        project = await db.projects.find_one({"slug": slug})
        project_id = str(project["_id"]) if project else None

        event = {
            "project_id": project_id,
            "slug": slug,
            "deployment_id": deployment_id,
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_ip": client_ip,
            "user_agent": user_agent[:120],
            "timestamp": utc_now_iso()
        }

        await db.runtime_logs.insert_one(event)
        if project_id:
            await publish_event(f"project:{project_id}:runtime_logs", event)
    except Exception as e:
        logger.warning(f"Failed to record access event: {e}")
