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
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
