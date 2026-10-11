import os
import tempfile
import shutil
import pytest
from starlette.requests import Request
from starlette.datastructures import Headers
from services.deployer.site_router import (
    _serve_transformed_html,
    _extract_slug_from_request,
    _apply_security_and_cache_headers,
)
from fastapi import Response

def test_serve_transformed_html_injects_base_and_rewrites_assets():
    temp_dir = tempfile.mkdtemp()
    try:
        html_file = os.path.join(temp_dir, "index.html")
        raw_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico">
    <link rel="stylesheet" href="/assets/main.css">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
    <title>Preview Test</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/assets/index.js"></script>
    <img src="/logo.png" alt="Logo">
    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg" alt="Inline">
</body>
</html>"""
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(raw_html)

        res = _serve_transformed_html(html_file, "my-preview-app")
        body = res.body.decode("utf-8")

        # 1. Verify <base href="/sites/my-preview-app/"> is injected
        assert '<base href="/sites/my-preview-app/">' in body

        # 2. Verify root-relative asset URLs are rewritten to /sites/my-preview-app/...
        assert 'href="/sites/my-preview-app/favicon.ico"' in body
        assert 'href="/sites/my-preview-app/assets/main.css"' in body
        assert 'src="/sites/my-preview-app/assets/index.js"' in body
        assert 'src="/sites/my-preview-app/logo.png"' in body

        # 3. Verify external URLs and data URIs are not rewritten
        assert 'href="https://fonts.googleapis.com/css2?family=Inter"' in body
        assert 'src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUg"' in body
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_extract_slug_from_referer_fallback():
    # Simulates browser fetching /assets/index.js from an iframe preview at http://localhost:8000/sites/ecommerce-mern/
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/assets/index.js",
        "headers": [
            (b"host", b"localhost:8000"),
            (b"referer", b"http://localhost:8000/sites/ecommerce-mern/"),
            (b"user-agent", b"pytest-client"),
        ],
    }
    req = Request(scope)
    slug, subpath = await _extract_slug_from_request(req)

    assert slug == "ecommerce-mern"
    assert subpath == "assets/index.js"

@pytest.mark.asyncio
async def test_extract_slug_from_path_prefix():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/sites/my-test-app/assets/style.css",
        "headers": [(b"host", b"localhost:8000")],
    }
    req = Request(scope)
    slug, subpath = await _extract_slug_from_request(req)

    assert slug == "my-test-app"
    assert subpath == "assets/style.css"

def test_security_headers_allow_dashboard_iframe_embedding():
    res = Response()
    _apply_security_and_cache_headers(res, "index.html")

    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"

    # CSP must allow embedding from localhost ports
    csp = res.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors" in csp
    assert "http://localhost:*" in csp
    assert "http://localhost:3000" in csp
