import os
import io
import zipfile
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.api.core.security import create_access_token
from services.api.core.database import connect_to_database, close_database_connection

@pytest.mark.asyncio
async def test_e2e_html_upload_build_deploy_and_apk():
    await connect_to_database()
    transport = ASGITransport(app=app)
    token = create_access_token({"sub": "usr_e2e_tester", "email": "e2e@ziref.dev"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create project
        res = await client.post(
            "/api/v1/projects",
            json={"name": "My Static Portfolio", "slug": "static-portfolio"},
            headers=headers
        )
        assert res.status_code == 201
        project = res.json()
        project_id = project["id"]

        # 2. Upload ZIP with simple HTML
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "index.html",
                "<!DOCTYPE html><html><head><title>Ziref Live</title></head><body><h1>Hello from Clean HTML!</h1></body></html>"
            )
            zf.writestr("styles.css", "body { font-family: sans-serif; background: #000; color: #fff; }")
        zip_bytes = zip_buf.getvalue()

        files = {"file": ("portfolio.zip", zip_bytes, "application/zip")}
        upload_res = await client.post(f"/api/v1/projects/{project_id}/uploads", files=files, headers=headers)
        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        upload_id = upload_data["id"]
        analysis = upload_data.get("analysis")
        assert analysis["framework"] == "html"
        assert analysis["buildCommand"] is None

        # 3. Trigger build
        build_res = await client.post(
            f"/api/v1/projects/{project_id}/builds",
            json={"upload_id": upload_id},
            headers=headers
        )
        assert build_res.status_code == 202
        build_id = build_res.json()["id"]

        # 4. Wait for build to complete
        b = {}
        for _ in range(30):
            await asyncio.sleep(0.5)
            resp = await client.get(f"/api/v1/builds/{build_id}", headers=headers)
            if resp.status_code == 200:
                b = resp.json()
                if b.get("status") in ["BUILT", "FAILED"]:
                    break
        assert b.get("status") == "BUILT", f"Build failed: {b.get('error_message')}"

        # 5. Check deployments
        for _ in range(30):
            await asyncio.sleep(0.5)
            deps = (await client.get(f"/api/v1/projects/{project_id}/deployments", headers=headers)).json()
            if deps and deps[0]["status"] in ["READY", "FAILED"]:
                break
        assert len(deps) > 0
        assert deps[0]["status"] == "READY"

        # 6. Create Mobile App
        app_res = await client.post(
            f"/api/v1/projects/{project_id}/apps",
            json={
                "app_name": "Portfolio Mobile App",
                "package_id": "com.ziref.portfolio",
                "theme": "dark",
                "orientation": "portrait",
                "permissions": ["camera"]
            },
            headers=headers
        )
        assert app_res.status_code == 201
        mobile_app = app_res.json()
        app_id = mobile_app["id"]

        # 7. Trigger Mobile Build
        mbuild_res = await client.post(f"/api/v1/apps/{app_id}/build", headers=headers)
        assert mbuild_res.status_code == 202
        mbuild_id = mbuild_res.json()["id"]

        # 8. Wait for mobile build to finish
        mb = {}
        for _ in range(30):
            await asyncio.sleep(0.5)
            resp = await client.get(f"/api/v1/mobile-builds/{mbuild_id}", headers=headers)
            if resp.status_code == 200:
                mb = resp.json()
                if mb.get("status") in ["APP_READY", "APP_FAILED"]:
                    break
        assert mb.get("status") == "APP_READY", f"Mobile build failed: {mb.get('error_message')}"
        assert mb.get("apk_download_url") is not None

        # 9. Verify APK download
        apk_res = await client.get(f"/api/v1/mobile-builds/{mbuild_id}/download/apk")
        assert apk_res.status_code == 200
        assert len(apk_res.content) > 0

    await close_database_connection()
