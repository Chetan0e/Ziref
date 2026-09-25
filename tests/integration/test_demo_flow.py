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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Trailing slash redirect
        redirect_res = await client.get("/sites/wild-pedia-web-project-enhanced", follow_redirects=False)
        assert redirect_res.status_code == 302
        assert redirect_res.headers["location"] == "/sites/wild-pedia-web-project-enhanced/"

        # 2. Live preview HTML response with CSP frame-ancestors
        preview_res = await client.get("/sites/wild-pedia-web-project-enhanced/")
        assert preview_res.status_code == 200
        assert "text/html" in preview_res.headers.get("content-type", "")
        assert "frame-ancestors" in preview_res.headers.get("content-security-policy", "")
        assert len(preview_res.content) > 0

        # 3. Mobile APK download
        apk_res = await client.get("/api/v1/mobile-builds/6ab5798778d2f5d6ea36276c/download")
        assert apk_res.status_code == 200
        assert apk_res.headers.get("content-type") == "application/vnd.android.package-archive"
        assert len(apk_res.content) > 0

        # 4. Mobile project source ZIP download
        zip_res = await client.get("/api/v1/mobile-builds/6ab5798778d2f5d6ea36276c/download/source")
        assert zip_res.status_code == 200
        assert zip_res.headers.get("content-type") == "application/zip"
        assert len(zip_res.content) > 0


