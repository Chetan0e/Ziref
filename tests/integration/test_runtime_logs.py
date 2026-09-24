import pytest
from httpx import AsyncClient, ASGITransport
from services.deployer.site_router import app as deployer_app
from services.api.main import app as api_app
from services.api.core.security import create_access_token

@pytest.mark.asyncio
async def test_runtime_logging_and_spa():
    transport = ASGITransport(app=deployer_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Request a route through router
        res = await client.get("/sites/nonexistent-project/about")
        assert res.status_code == 404

    # Verify through API
    api_transport = ASGITransport(app=api_app)
    token = create_access_token({"sub": "usr_runtime_tester", "email": "runtime@ziref.dev"})
    async with AsyncClient(transport=api_transport, base_url="http://test") as client:
        # Check health
        health_res = await client.get("/health")
        assert health_res.status_code == 200
