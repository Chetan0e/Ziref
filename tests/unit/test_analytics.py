import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId

from services.api.main import app
from services.api.core.database import get_database, connect_to_database
from services.api.core.security import create_access_token

@pytest.mark.asyncio
async def test_analytics_aggregation():
    await connect_to_database()
    db = get_database()
    user_id = str(ObjectId())
    token = create_access_token({"sub": user_id, "email": "analytics@example.com"})

    # Create dummy project
    p_res = await db.projects.insert_one({
        "user_id": user_id,
        "name": "Analytics Test Project",
        "slug": "analytics-test",
        "status": "DEPLOYED"
    })
    project_id = str(p_res.inserted_id)

    # Insert mock runtime access logs
    mock_logs = [
        {"project_id": project_id, "slug": "analytics-test", "method": "GET", "path": "/", "status_code": 200, "duration_ms": 12.5, "client_ip": "1.1.1.1", "user_agent": "Mozilla/5.0 Desktop", "timestamp": "2026-09-23T00:10:00Z"},
        {"project_id": project_id, "slug": "analytics-test", "method": "GET", "path": "/", "status_code": 200, "duration_ms": 15.0, "client_ip": "1.1.1.1", "user_agent": "Mozilla/5.0 Desktop", "timestamp": "2026-09-23T00:11:00Z"},
        {"project_id": project_id, "slug": "analytics-test", "method": "GET", "path": "/assets/index.js", "status_code": 200, "duration_ms": 5.0, "client_ip": "2.2.2.2", "user_agent": "Android Mobile", "timestamp": "2026-09-23T00:12:00Z"},
        {"project_id": project_id, "slug": "analytics-test", "method": "GET", "path": "/not-found", "status_code": 404, "duration_ms": 3.0, "client_ip": "3.3.3.3", "user_agent": "Mozilla/5.0 Desktop", "timestamp": "2026-09-23T00:13:00Z"},
    ]
    await db.runtime_logs.insert_many(mock_logs)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/projects/{project_id}/analytics",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_requests"] == 4
        assert data["unique_visitors"] == 3
        assert data["status_codes"]["status_2xx"] == 3
        assert data["status_codes"]["status_4xx"] == 1
        assert len(data["top_paths"]) >= 2
        assert data["device_breakdown"]["desktop"] == 3
        assert data["device_breakdown"]["mobile"] == 1
