import os
import tempfile
import shutil
import json
import tarfile
import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.analyzer.detector import project_detector
from services.builder.docker_sandbox import docker_sandbox
from services.deployer.deployer_service import deployer_service
from services.api.core.database import get_database
from bson import ObjectId

@pytest.mark.asyncio
async def test_full_mern_build_deploy_and_preview_flow():
    temp_dir = tempfile.mkdtemp()
    try:
        # 1. Scaffold MERN Monorepo: Root Backend + Client Frontend
        root_pkg = {
            "name": "full-mern-store",
            "scripts": {
                "start": "node server.js",
                "build": "cd client && npm install && npm run build"
            },
            "dependencies": {
                "express": "^4.18.2",
                "mongoose": "^7.0.0",
                "cors": "^2.8.5"
            }
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(root_pkg, f)

        with open(os.path.join(temp_dir, "server.js"), "w") as f:
            f.write("const express = require('express');\nconst app = express();\n")

        client_dir = os.path.join(temp_dir, "client")
        os.makedirs(client_dir, exist_ok=True)
        client_pkg = {
            "name": "client-react",
            "scripts": {"build": "vite build"},
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            },
            "devDependencies": {
                "vite": "^5.0.0"
            }
        }
        with open(os.path.join(client_dir, "package.json"), "w") as f:
            json.dump(client_pkg, f)

        # Built client distribution in client/dist
        dist_dir = os.path.join(client_dir, "dist")
        assets_dir = os.path.join(dist_dir, "assets")
        os.makedirs(assets_dir, exist_ok=True)

        with open(os.path.join(dist_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>MERN Store App</title>
    <link rel="stylesheet" href="/assets/index-123.css">
</head>
<body>
    <div id="root"><h1>MERN App Live</h1></div>
    <script type="module" src="/assets/index-123.js"></script>
</body>
</html>""")

        with open(os.path.join(assets_dir, "index-123.js"), "w", encoding="utf-8") as f:
            f.write("console.log('MERN react client loaded successfully');")

        with open(os.path.join(assets_dir, "index-123.css"), "w", encoding="utf-8") as f:
            f.write("body { background: #0f172a; color: white; }")

        # 2. Test Detection
        analysis = project_detector.analyze(temp_dir)
        assert analysis.framework == "react"
        assert analysis.runtime == "static"
        assert analysis.outputDirectory == "client/dist"
        assert analysis.buildCommand == "npm run build"

        # 3. Test Sandbox Output Resolution
        resolved_out = docker_sandbox._resolve_output_directory(temp_dir, analysis.outputDirectory)
        assert os.path.isdir(resolved_out)
        assert os.path.exists(os.path.join(resolved_out, "index.html"))

        # 4. Create Build Artifact Tarball & Project in DB
        from services.api.core.config import settings
        build_id = str(ObjectId())
        project_id = str(ObjectId())
        slug = f"mern-test-{build_id[:6]}"

        db = get_database()
        await db.projects.insert_one({
            "_id": ObjectId(project_id),
            "name": "MERN Test Store",
            "slug": slug,
            "status": "BUILDING",
            "user_id": "test-user-id"
        })

        artifact_filename = f"artifact-{build_id}.tar.gz"
        artifact_rel_path = os.path.join("artifacts", artifact_filename)
        artifact_abs_path = os.path.join(settings.STORAGE_PATH, artifact_rel_path)

        with tarfile.open(artifact_abs_path, "w:gz") as tar:
            tar.add(resolved_out, arcname=".")

        # 5. Process Deployment
        deployment_id = await deployer_service.process_deploy_job({
            "build_id": build_id,
            "project_id": project_id,
            "artifact_path": artifact_rel_path,
            "runtime": "static"
        })
        assert deployment_id is not None

        # Verify deployment record
        dep_doc = await db.deployments.find_one({"_id": ObjectId(deployment_id)})
        assert dep_doc["status"] == "READY"

        # 6. Verify Preview Gateway on Port 8000 via ASGI Client
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
            # 6a. Live HTML preview page
            res_html = await client.get(f"/sites/{slug}/")
            assert res_html.status_code == 200
            assert "text/html" in res_html.headers.get("content-type", "")

            body = res_html.text
            # Base href must be injected
            assert f'<base href="/sites/{slug}/">' in body
            # Root-relative asset paths must be rewritten
            assert f'href="/sites/{slug}/assets/index-123.css"' in body
            assert f'src="/sites/{slug}/assets/index-123.js"' in body

            # Security headers: X-Frame-Options and Content-Security-Policy frame-ancestors
            assert res_html.headers.get("x-frame-options") == "SAMEORIGIN"
            assert "frame-ancestors" in res_html.headers.get("content-security-policy", "")

            # 6b. Directly fetch rewritten JS bundle
            res_js = await client.get(f"/sites/{slug}/assets/index-123.js")
            assert res_js.status_code == 200
            assert "javascript" in res_js.headers.get("content-type", "")
            assert "MERN react client loaded" in res_js.text

            # 6c. Directly fetch rewritten CSS stylesheet
            res_css = await client.get(f"/sites/{slug}/assets/index-123.css")
            assert res_css.status_code == 200
            assert "text/css" in res_css.headers.get("content-type", "")
            assert "#0f172a" in res_css.text

            # 6d. Test Referer fallback: fetch un-namespaced /assets/index-123.js with preview Referer
            res_ref_js = await client.get(
                "/assets/index-123.js",
                headers={"referer": f"http://localhost:8000/sites/{slug}/"}
            )
            assert res_ref_js.status_code == 200
            assert "javascript" in res_ref_js.headers.get("content-type", "")
            assert "MERN react client loaded" in res_ref_js.text
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
