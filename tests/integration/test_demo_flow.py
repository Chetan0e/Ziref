import os
import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.core.security import create_access_token

@pytest.mark.asyncio
async def test_create_project_and_system_status():
    transport = ASGITransport(app=app)
    token = create_access_token({"sub": "usr_project_tester", "email": "tester@ziref.dev"})

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project via standard API
        res = await client.post(
            "/api/v1/projects",
            json={"name": "Production Service", "slug": "prod-service"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["slug"].startswith("prod-service")
        assert data["status"] == "CREATED"

        # 2. Check system status endpoint
        status_res = await client.get("/api/v1/system/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert "worker" in status_data
        assert "metrics" in status_data

@pytest.mark.asyncio
async def test_custom_domains_flow():
    import uuid
    transport = ASGITransport(app=app)
    token = create_access_token({"sub": "usr_dom_tester", "email": "domain@ziref.dev"})
    unique_dom = f"app-{uuid.uuid4().hex[:6]}.company.org"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a project
        proj_res = await client.post(
            "/api/v1/projects",
            json={"name": "Domain Test Project"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert proj_res.status_code == 201
        project_id = proj_res.json()["id"]

        # 2. Add custom domain
        dom_res = await client.post(
            f"/api/v1/projects/{project_id}/domains",
            json={"domain": unique_dom},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert dom_res.status_code == 201
        domain_id = dom_res.json()["id"]
        assert dom_res.json()["status"] == "PENDING_DNS"

        # 3. Verify custom domain
        verify_res = await client.post(
            f"/api/v1/projects/{project_id}/domains/{domain_id}/verify",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert verify_res.status_code == 200
        assert verify_res.json()["status"] == "VERIFIED"

        # 4. List domains
        list_res = await client.get(
            f"/api/v1/projects/{project_id}/domains",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

@pytest.mark.asyncio
async def test_delete_project_by_id_and_slug():
    transport = ASGITransport(app=app)
    token = create_access_token({"sub": "usr_del_tester", "email": "delete_tester@ziref.dev"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project 1 and delete by slug
        p1_res = await client.post("/api/v1/projects", json={"name": "Delete By Slug", "slug": "del-by-slug"}, headers=headers)
        assert p1_res.status_code == 201
        slug1 = p1_res.json()["slug"]

        del1_res = await client.delete(f"/api/v1/projects/{slug1}", headers=headers)
        assert del1_res.status_code == 204

        # Verify it no longer exists
        get1_res = await client.get(f"/api/v1/projects/{slug1}", headers=headers)
        assert get1_res.status_code == 404

        # 2. Create project 2 and delete by ID
        p2_res = await client.post("/api/v1/projects", json={"name": "Delete By ID"}, headers=headers)
        assert p2_res.status_code == 201
        id2 = p2_res.json()["id"]

        del2_res = await client.delete(f"/api/v1/projects/{id2}", headers=headers)
        assert del2_res.status_code == 204

        # Verify it no longer exists
        get2_res = await client.get(f"/api/v1/projects/{id2}", headers=headers)
        assert get2_res.status_code == 404

@pytest.mark.asyncio
async def test_site_router_preview_and_downloads():
    import uuid
    from bson import ObjectId
    from services.api.core.config import settings
    from services.api.core.database import connect_to_database, get_database
    from services.deployer.site_router import app as router_app

    await connect_to_database()
    db = get_database()

    # --- Setup: deployment directory fixture ---
    slug = f"ci-preview-{uuid.uuid4().hex[:8]}"
    deployment_id = str(ObjectId())
    project_id = str(ObjectId())

    deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments", deployment_id)
    os.makedirs(deploy_dir, exist_ok=True)
    with open(os.path.join(deploy_dir, "index.html"), "w") as f:
        f.write("<!DOCTYPE html><html><body><h1>CI Preview</h1></body></html>")

    await db.projects.insert_one({
        "_id": ObjectId(project_id),
        "slug": slug,
        "name": "CI Preview Project",
        "active_deployment_id": deployment_id,
        "status": "DEPLOYED",
    })

    # --- Setup: mobile build fixture with real artifact files on disk ---
    mobile_build_id = str(ObjectId())
    mobile_dir = os.path.join(settings.STORAGE_PATH, "mobile")
    os.makedirs(mobile_dir, exist_ok=True)

    apk_rel = f"mobile/app-debug-{mobile_build_id}.apk"
    zip_rel = f"mobile/app-source-{mobile_build_id}.zip"
    apk_abs = os.path.join(settings.STORAGE_PATH, apk_rel)
    zip_abs = os.path.join(settings.STORAGE_PATH, zip_rel)

    with open(apk_abs, "wb") as f:
        f.write(b"PK\x03\x04" + b"\x00" * 26)   # minimal ZIP/APK stub
    with open(zip_abs, "wb") as f:
        f.write(b"PK\x03\x04" + b"\x00" * 26)

    await db.mobile_builds.insert_one({
        "_id": ObjectId(mobile_build_id),
        "project_id": project_id,
        "status": "APP_READY",
        "apk_artifact_id": apk_rel,
        "source_artifact_id": zip_rel,
    })

    # --- Tests against the site router ASGI app ---
    router_transport = ASGITransport(app=router_app)
    async with AsyncClient(transport=router_transport, base_url="http://localhost:8080") as router_client:
        # 1. Trailing slash redirect
        redirect_res = await router_client.get(f"/sites/{slug}", follow_redirects=False)
        assert redirect_res.status_code == 302
        assert redirect_res.headers["location"] == f"/sites/{slug}/"

        # 2. Live preview HTML response with security headers
        preview_res = await router_client.get(f"/sites/{slug}/")
        assert preview_res.status_code == 200
        assert "text/html" in preview_res.headers.get("content-type", "")
        assert "frame-ancestors" in preview_res.headers.get("content-security-policy", "")
        assert len(preview_res.content) > 0

    # --- Tests against the API app for artifact downloads ---
    api_transport = ASGITransport(app=app)
    async with AsyncClient(transport=api_transport, base_url="http://test") as api_client:
        # 3. Mobile APK download
        apk_res = await api_client.get(f"/api/v1/mobile-builds/{mobile_build_id}/download")
        assert apk_res.status_code == 200
        assert apk_res.headers.get("content-type") == "application/vnd.android.package-archive"
        assert len(apk_res.content) > 0

        # 4. Mobile project source ZIP download
        zip_res = await api_client.get(f"/api/v1/mobile-builds/{mobile_build_id}/download/source")
        assert zip_res.status_code == 200
        assert zip_res.headers.get("content-type") == "application/zip"
        assert len(zip_res.content) > 0

