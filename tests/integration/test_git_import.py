import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId

from services.analyzer.git_importer import git_importer, GitSecurityError
from services.api.main import app
from services.api.core.database import connect_to_database
from services.api.core.security import create_access_token

def test_git_url_validation():
    # Valid URLs
    assert git_importer.validate_url("https://github.com/vitejs/vite") == "https://github.com/vitejs/vite"
    assert git_importer.validate_url("https://gitlab.com/group/repo.git") == "https://gitlab.com/group/repo.git"

    # Malicious or invalid URLs
    with pytest.raises(GitSecurityError):
        git_importer.validate_url("--upload-pack=exploit")

    with pytest.raises(GitSecurityError):
        git_importer.validate_url("file:///etc/passwd")

    with pytest.raises(GitSecurityError):
        git_importer.validate_url("ssh://git@github.com/repo.git")

    with pytest.raises(GitSecurityError):
        git_importer.validate_url("https://github.com/foo/bar;rm -rf /")

@pytest.mark.asyncio
async def test_import_git_endpoint_validation():
    await connect_to_database()
    user_id = str(ObjectId())
    token = create_access_token({"sub": user_id, "email": "git@example.com"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test invalid URL rejected with 400
        resp = await client.post(
            "/api/v1/projects/import-git",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Exploit Attempt",
                "repo_url": "file:///tmp/secret"
            }
        )
        assert resp.status_code == 400
