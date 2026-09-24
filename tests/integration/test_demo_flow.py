import os
import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.core.security import create_access_token

@pytest.mark.asyncio
async def test_create_demo_project_endpoint():
    transport = ASGITransport(app=app)
    token = create_access_token({"sub": "usr_demo_tester", "email": "tester@ziref.dev"})

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/projects/create-demo",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 201
        data = res.json()
        assert "project_id" in data
        assert "build_id" in data
        assert "slug" in data
        assert data["slug"].startswith("demo-react")

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
