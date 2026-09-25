import os
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId

from services.deployer.site_router import app as router_app
from services.api.core.config import settings
from services.api.core.database import connect_to_database, get_database

@pytest.mark.asyncio
async def test_router_security_and_cache_headers():
    await connect_to_database()
    db = get_database()
    project_id = str(ObjectId())
    deployment_id = str(ObjectId())
    slug = f"sec-test-{uuid.uuid4().hex[:8]}"

    # Setup deployment folder with index.html and static asset
    deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments", deployment_id)
    os.makedirs(deploy_dir, exist_ok=True)
    with open(os.path.join(deploy_dir, "index.html"), "w") as f:
        f.write("<!DOCTYPE html><html><body><h1>Secure Site</h1></body></html>")

    assets_dir = os.path.join(deploy_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    with open(os.path.join(assets_dir, "main.js"), "w") as f:
        f.write("console.log('secure bundle');")

    await db.projects.insert_one({
        "_id": ObjectId(project_id),
        "slug": slug,
        "name": "Security Test Project",
        "active_deployment_id": deployment_id
    })

    transport = ASGITransport(app=router_app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8080") as client:
        # 1. Test HTML route
        resp = await client.get(f"/sites/{slug}/")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "SAMEORIGIN"
        assert "no-revalidate" in resp.headers.get("cache-control", "") or "max-age=0" in resp.headers.get("cache-control", "")

        # 2. Test Static Asset route
        resp_asset = await client.get(f"/sites/{slug}/assets/main.js")
        assert resp_asset.status_code == 200
        assert resp_asset.headers.get("x-content-type-options") == "nosniff"
        assert "immutable" in resp_asset.headers.get("cache-control", "")

@pytest.mark.asyncio
async def test_router_custom_domain_lookup():
    await connect_to_database()
    db = get_database()
    project_id = str(ObjectId())
    deployment_id = str(ObjectId())
    slug = f"dom-test-{uuid.uuid4().hex[:8]}"
    custom_domain = f"{slug}.mycompany.com"

    deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments", deployment_id)
    os.makedirs(deploy_dir, exist_ok=True)
    with open(os.path.join(deploy_dir, "index.html"), "w") as f:
        f.write("<h1>Custom Domain Site</h1>")

    await db.projects.insert_one({
        "_id": ObjectId(project_id),
        "slug": slug,
        "name": "Domain Test",
        "active_deployment_id": deployment_id
    })

    await db.custom_domains.insert_one({
        "project_id": project_id,
        "domain": custom_domain,
        "status": "VERIFIED"
    })

    transport = ASGITransport(app=router_app)
    async with AsyncClient(transport=transport, base_url=f"http://{custom_domain}") as client:
        resp = await client.get("/", headers={"Host": custom_domain})
        assert resp.status_code == 200
        assert "Custom Domain Site" in resp.text
