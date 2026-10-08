import os
import tempfile
import shutil
import zipfile
import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId

from services.api.main import app
from services.api.core.config import settings
from services.api.core.database import connect_to_database, close_database_connection, get_database
from services.api.core.datetime_util import utc_now_iso
from services.api.core.models import ProjectStatus, MobileAppStatus
from services.api.core.security import create_access_token
from services.analyzer.detector import project_detector
from services.builder.docker_sandbox import docker_sandbox
from services.app_builder.apk_builder import mobile_build_pipeline

@pytest.mark.asyncio
async def test_static_html_analysis_and_sandbox_build():
    tmp_dir = tempfile.mkdtemp()
    try:
        index_html = os.path.join(tmp_dir, "index.html")
        with open(index_html, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><body><h1>Welcome to Static Ziref</h1></body></html>")

        styles_css = os.path.join(tmp_dir, "styles.css")
        with open(styles_css, "w", encoding="utf-8") as f:
            f.write("body { background: #000; color: #fff; }")

        # 1. Detector
        analysis = project_detector.analyze(tmp_dir)
        assert analysis.framework == "html"
        assert analysis.packageManager == "none"
        assert analysis.buildCommand is None
        assert analysis.outputDirectory == "."

        # 2. Sandbox execution (must succeed without npm install or error)
        logs = []
        async def mock_log(evt):
            logs.append(evt.message)

        out_dir = await docker_sandbox.execute_build(
            workspace_dir=tmp_dir,
            package_manager=analysis.packageManager,
            build_command=analysis.buildCommand,
            output_directory=analysis.outputDirectory,
            env_vars={},
            log_callback=mock_log
        )

        assert os.path.exists(out_dir)
        assert os.path.exists(os.path.join(out_dir, "index.html"))
        assert any("Static application detected" in msg for msg in logs)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_nested_html_analysis():
    tmp_dir = tempfile.mkdtemp()
    try:
        nested_dir = os.path.join(tmp_dir, "my-website-folder")
        os.makedirs(nested_dir, exist_ok=True)
        with open(os.path.join(nested_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write("<h1>Nested Site</h1>")

        analysis = project_detector.analyze(tmp_dir)
        assert analysis.framework == "html"
        assert analysis.packageManager == "none"
        assert analysis.buildCommand is None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_mobile_build_pipeline_completion():
    await connect_to_database()
    try:
        db = get_database()
        now_str = utc_now_iso()

        # Create dummy project
        proj_res = await db.projects.insert_one({
            "name": "Mobile Test Project",
            "slug": f"mobile-test-{ObjectId()}",
            "status": ProjectStatus.DEPLOYED.value,
            "active_url": "https://mobiletest.ziref.dev",
            "created_at": now_str,
            "updated_at": now_str
        })
        project_id = str(proj_res.inserted_id)

        # Create mobile app
        app_res = await db.mobile_apps.insert_one({
            "project_id": project_id,
            "app_name": "Mobile Test App",
            "package_id": "com.ziref.mobiletest",
            "version": "1.0.0",
            "version_code": 1,
            "website_url": "https://mobiletest.ziref.dev",
            "theme": "system",
            "orientation": "portrait",
            "permissions": ["camera", "location"],
            "created_at": now_str
        })
        app_id = str(app_res.inserted_id)

        # Create mobile build record
        build_res = await db.mobile_builds.insert_one({
            "mobile_app_id": app_id,
            "project_id": project_id,
            "status": MobileAppStatus.APP_QUEUED.value,
            "build_target": "android",
            "apk_artifact_id": None,
            "source_artifact_id": None,
            "logs": [],
            "created_at": now_str
        })
        mobile_build_id = str(build_res.inserted_id)

        # Execute build job
        await mobile_build_pipeline.process_mobile_build_job({
            "mobile_build_id": mobile_build_id,
            "mobile_app_id": app_id,
            "project_id": project_id
        })

        # Verify build completed
        updated_build = await db.mobile_builds.find_one({"_id": ObjectId(mobile_build_id)})
        assert updated_build is not None
        assert updated_build["status"] == MobileAppStatus.APP_READY.value
        assert updated_build["apk_artifact_id"] is not None
        assert updated_build["source_artifact_id"] is not None

        # Verify files on disk
        apk_disk_path = os.path.join(settings.STORAGE_PATH, updated_build["apk_artifact_id"])
        source_disk_path = os.path.join(settings.STORAGE_PATH, updated_build["source_artifact_id"])

        assert os.path.exists(apk_disk_path)
        assert os.path.exists(source_disk_path)
        assert zipfile.is_zipfile(apk_disk_path)
        assert zipfile.is_zipfile(source_disk_path)
    finally:
        await close_database_connection()

@pytest.mark.asyncio
async def test_deployer_unwraps_nested_index_html():
    from services.deployer.deployer_service import deployer_service
    import tarfile

    await connect_to_database()
    try:
        db = get_database()
        now_str = utc_now_iso()

        # 1. Create a dummy project
        slug = f"unwrap-test-{ObjectId()}"
        p_res = await db.projects.insert_one({
            "name": "Unwrap Test",
            "slug": slug,
            "status": ProjectStatus.BUILD_QUEUED.value,
            "created_at": now_str,
            "updated_at": now_str
        })
        project_id = str(p_res.inserted_id)

        # 2. Create artifact tarball with nested dist/index.html
        build_id = str(ObjectId())
        artifact_rel = os.path.join("artifacts", f"test-artifact-{build_id}.tar.gz")
        artifact_abs = os.path.join(settings.STORAGE_PATH, artifact_rel)
        os.makedirs(os.path.dirname(artifact_abs), exist_ok=True)

        tmp_build = tempfile.mkdtemp()
        try:
            nested_dist = os.path.join(tmp_build, "dist")
            os.makedirs(nested_dist, exist_ok=True)
            with open(os.path.join(nested_dist, "index.html"), "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html><html><body><h1>Unwrapped Dist Site</h1></body></html>")
            with open(os.path.join(nested_dist, "app.js"), "w", encoding="utf-8") as f:
                f.write("console.log('unwrapped');")

            with tarfile.open(artifact_abs, "w:gz") as tar:
                tar.add(tmp_build, arcname=".")
        finally:
            shutil.rmtree(tmp_build, ignore_errors=True)

        # 3. Process deploy job
        deployment_id = await deployer_service.process_deploy_job({
            "build_id": build_id,
            "project_id": project_id,
            "artifact_path": artifact_rel,
            "runtime": "static"
        })

        assert deployment_id is not None

        # Verify deployment record
        dep = await db.deployments.find_one({"_id": ObjectId(deployment_id)})
        assert dep["status"] == "READY"

        # Verify index.html exists at top-level deployment directory
        deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments", deployment_id)
        assert os.path.exists(os.path.join(deploy_dir, "index.html"))
        assert os.path.exists(os.path.join(deploy_dir, "app.js"))

        # Verify project status
        proj = await db.projects.find_one({"_id": ObjectId(project_id)})
        assert proj["status"] == ProjectStatus.DEPLOYED.value
        assert proj["active_deployment_id"] == deployment_id
    finally:
        await close_database_connection()

