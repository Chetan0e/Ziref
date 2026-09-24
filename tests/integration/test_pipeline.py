import os
import pytest
from httpx import AsyncClient, ASGITransport
from services.api.main import app
from services.analyzer.detector import project_detector
from services.analyzer.archive_validator import archive_validator

@pytest.mark.asyncio
async def test_demo_fixture_analysis():
    fixture_dir = os.path.abspath("tests/fixtures/sample-react-vite")
    analysis = project_detector.analyze(fixture_dir)

    assert analysis.framework == "react"
    assert analysis.outputDirectory == "dist"
    assert "build" in analysis.buildCommand

@pytest.mark.asyncio
async def test_demo_zip_validation():
    zip_path = os.path.abspath("tests/fixtures/ziref-demo-react.zip")
    assert os.path.exists(zip_path)

    import tempfile, shutil
    tmp_out = tempfile.mkdtemp()
    try:
        success, msg, files = archive_validator.validate_and_extract(zip_path, tmp_out)
        assert success is True
        assert len(files) > 0
        assert any("package.json" in f for f in files)
        assert any("vite.config.ts" in f for f in files)

        analysis = project_detector.analyze(tmp_out)
        assert analysis.framework == "react"
        assert analysis.outputDirectory == "dist"
    finally:
        shutil.rmtree(tmp_out, ignore_errors=True)

@pytest.mark.asyncio
async def test_api_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
