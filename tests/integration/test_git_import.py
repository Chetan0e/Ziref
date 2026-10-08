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
    assert git_importer.validate_url("github.com/vitejs/vite") == "https://github.com/vitejs/vite"
    assert git_importer.validate_url("https://github.com/vitejs/vite?tab=readme") == "https://github.com/vitejs/vite"

    # Malicious or invalid URLs
    with pytest.raises(GitSecurityError):
        git_importer.validate_url("--upload-pack=exploit")

    with pytest.raises(GitSecurityError):
        git_importer.validate_url("file:///etc/passwd")

    with pytest.raises(GitSecurityError):
        git_importer.validate_url("ssh://git@github.com/repo.git")

    with pytest.raises(GitSecurityError):
        git_importer.validate_url("https://github.com/foo/bar;rm -rf /")

def test_git_repo_details_parsing():
    details = git_importer.parse_repo_details("https://github.com/octocat/Hello-World/tree/feature/sub/path")
    assert details["owner"] == "octocat"
    assert details["repo"] == "Hello-World"
    assert details["branch"] == "feature"
    assert details["subpath"] == "sub/path"
    assert "octocat/Hello-World.git" in details["clean_url"]

def test_clone_or_download_repo_default_branch():
    import os, shutil
    # octocat/Hello-World has default branch 'master', NOT 'main'
    # Test that even if branch='main' was requested, it falls back to master/default branch successfully
    workspace_dir, zip_path, file_size, checksum = git_importer.clone_or_download_repo(
        repo_url="https://github.com/octocat/Hello-World",
        branch="main"
    )
    try:
        assert os.path.isdir(workspace_dir)
        assert os.path.isfile(zip_path)
        assert file_size > 0
        assert len(checksum) == 64
        # Verify README exists in cloned repo
        assert any("README" in f.upper() for f in os.listdir(workspace_dir))
    finally:
        parent = os.path.dirname(workspace_dir)
        if "ziref_git_" in os.path.basename(parent):
            shutil.rmtree(parent, ignore_errors=True)
        elif os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)

def test_sandbox_output_resolution_priority():
    import tempfile, os, shutil
    from services.builder.docker_sandbox import docker_sandbox

    tmp = tempfile.mkdtemp()
    try:
        # Create uncompiled index.html in root
        with open(os.path.join(tmp, "index.html"), "w") as f:
            f.write("<html><body>Source JSX/TSX</body></html>")

        # Create compiled index.html in dist
        dist_dir = os.path.join(tmp, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        with open(os.path.join(dist_dir, "index.html"), "w") as f:
            f.write("<html><body>Compiled Bundle</body></html>")

        # Must prioritize dist over root index.html even if output_dir is configured as "." or empty
        resolved = docker_sandbox._resolve_output_directory(tmp, ".")
        assert resolved == dist_dir
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

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

