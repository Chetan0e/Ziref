import os
import tempfile
import shutil
import json
import pytest
from services.analyzer.detector import ProjectDetector

@pytest.fixture
def detector():
    return ProjectDetector()

def test_detect_react_vite(detector):
    temp_dir = tempfile.mkdtemp()
    try:
        pkg = {
            "name": "vite-react-app",
            "scripts": {"build": "vite build"},
            "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},
            "devDependencies": {"vite": "^5.0.0"}
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(pkg, f)
        with open(os.path.join(temp_dir, "pnpm-lock.yaml"), "w") as f:
            f.write("lockfileVersion: 5.4")
        with open(os.path.join(temp_dir, "vite.config.ts"), "w") as f:
            f.write("export default {}")

        result = detector.analyze(temp_dir)
        assert result.framework == "react"
        assert result.packageManager == "pnpm"
        assert result.buildCommand == "pnpm run build"
        assert result.outputDirectory == "dist"
        assert result.runtime == "static"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_detect_nextjs(detector):
    temp_dir = tempfile.mkdtemp()
    try:
        pkg = {
            "name": "next-app",
            "scripts": {"build": "next build", "start": "next start"},
            "dependencies": {"next": "14.2.0", "react": "^18.2.0"}
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(pkg, f)
        with open(os.path.join(temp_dir, "next.config.js"), "w") as f:
            f.write("module.exports = {}")

        result = detector.analyze(temp_dir)
        assert result.framework == "nextjs"
        assert result.buildCommand == "npm run build"
        assert result.outputDirectory == "out"  # Changed to 'out' for static export
        assert result.runtime == "static"  # Changed to static for deployment compatibility
        assert len(result.warnings) > 0  # Should warn about missing static export config
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_detect_static_html(detector):
    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "index.html"), "w") as f:
            f.write("<!DOCTYPE html><html><body>Hello World</body></html>")

        result = detector.analyze(temp_dir)
        assert result.framework == "html"
        assert result.runtime == "static"
        assert result.outputDirectory == "."
        assert result.buildCommand is None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_sandbox_static_html_ignores_erroneous_build_command():
    from services.builder.docker_sandbox import docker_sandbox
    temp_dir = tempfile.mkdtemp()
    try:
        with open(os.path.join(temp_dir, "index.html"), "w") as f:
            f.write("<!DOCTYPE html><html><body>Hello World</body></html>")

        logs = []
        async def dummy_callback(evt):
            logs.append(evt.message)

        out = await docker_sandbox.execute_build(
            workspace_dir=temp_dir,
            package_manager="none",
            build_command="npm run build",  # Erroneous legacy command
            output_directory=".",
            env_vars={},
            log_callback=dummy_callback
        )
        assert os.path.exists(out)
        assert any("Static application detected" in log for log in logs)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_detect_mern_with_root_build_script(detector):
    temp_dir = tempfile.mkdtemp()
    try:
        # Root backend package.json with express and build script targeting client
        root_pkg = {
            "name": "mern-ecommerce",
            "version": "1.0.0",
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

        # Client frontend directory with React/Vite
        client_dir = os.path.join(temp_dir, "client")
        os.makedirs(client_dir, exist_ok=True)
        client_pkg = {
            "name": "client",
            "scripts": {
                "build": "vite build"
            },
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

        result = detector.analyze(temp_dir)
        assert result.framework == "react"
        assert result.runtime == "static"
        assert result.buildCommand == "npm run build"
        assert result.outputDirectory == "client/dist"
        assert any("client" in w for w in result.warnings)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_detect_mern_with_workspaces(detector):
    temp_dir = tempfile.mkdtemp()
    try:
        root_pkg = {
            "name": "mern-monorepo",
            "workspaces": ["frontend", "backend"],
            "scripts": {
                "build": "npm run build --workspace=frontend"
            }
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(root_pkg, f)

        # Frontend workspace directory
        frontend_dir = os.path.join(temp_dir, "frontend")
        os.makedirs(frontend_dir, exist_ok=True)
        frontend_pkg = {
            "name": "frontend",
            "scripts": {"build": "react-scripts build"},
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1"
            }
        }
        with open(os.path.join(frontend_dir, "package.json"), "w") as f:
            json.dump(frontend_pkg, f)
        os.makedirs(os.path.join(frontend_dir, "public"), exist_ok=True)

        result = detector.analyze(temp_dir)
        assert result.framework == "react"
        assert result.runtime == "static"
        assert result.outputDirectory == "frontend/build"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_detect_mern_with_static_client(detector):
    temp_dir = tempfile.mkdtemp()
    try:
        root_pkg = {
            "name": "express-static-app",
            "scripts": {"start": "node index.js"},
            "dependencies": {"express": "^4.18.0"}
        }
        with open(os.path.join(temp_dir, "package.json"), "w") as f:
            json.dump(root_pkg, f)

        client_dir = os.path.join(temp_dir, "client")
        os.makedirs(client_dir, exist_ok=True)
        with open(os.path.join(client_dir, "index.html"), "w") as f:
            f.write("<!DOCTYPE html><html><body><h1>Client Static App</h1></body></html>")

        result = detector.analyze(temp_dir)
        assert result.framework == "html"
        assert result.runtime == "static"
        assert result.outputDirectory == "client"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


