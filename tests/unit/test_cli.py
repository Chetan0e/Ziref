import os
import zipfile
import tempfile
from packages.cli.config import cli_config
from packages.cli.client import ZirefApiClient
from packages.cli.main import create_archive_from_dir

def test_cli_config_token():
    cli_config.save({"token": "test-token-12345"})
    assert cli_config.get_token() == "test-token-12345"
    cli_config.clear()

def test_cli_create_archive_ignores():
    with tempfile.TemporaryDirectory() as tmp_src:
        # Create normal files
        with open(os.path.join(tmp_src, "index.html"), "w") as f:
            f.write("<h1>Hello</h1>")
        with open(os.path.join(tmp_src, "package.json"), "w") as f:
            f.write("{}")

        # Create ignored dirs and files
        node_modules = os.path.join(tmp_src, "node_modules")
        os.makedirs(node_modules, exist_ok=True)
        with open(os.path.join(node_modules, "dep.js"), "w") as f:
            f.write("module.exports = {}")

        dot_git = os.path.join(tmp_src, ".git")
        os.makedirs(dot_git, exist_ok=True)
        with open(os.path.join(dot_git, "config"), "w") as f:
            f.write("gitconfig")

        zip_path = create_archive_from_dir(tmp_src)
        assert os.path.exists(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            namelist = zf.namelist()
            assert "index.html" in namelist
            assert "package.json" in namelist
            assert not any("node_modules" in name for name in namelist)
            assert not any(".git" in name for name in namelist)

        os.remove(zip_path)

def test_cli_client_headers():
    client = ZirefApiClient(base_url="http://test-server:8000")
    headers = client._headers()
    assert headers["User-Agent"] == "Ziref-CLI/1.0"
    assert headers["Content-Type"] == "application/json"
