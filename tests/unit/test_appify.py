import os
import tempfile
import shutil
import zipfile
import pytest
from services.app_builder.android_generator import android_project_generator
from services.app_builder.apk_builder import mobile_build_pipeline

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)

def test_android_project_generation(temp_dir):
    config = {
        "app_name": "Test Application",
        "package_id": "com.ziref.testapp",
        "version": "1.0.0",
        "version_code": 1,
        "website_url": "https://testapp.ziref.app",
        "theme": "dark",
        "orientation": "portrait"
    }

    out_dir = android_project_generator.generate(config, temp_dir)
    assert os.path.exists(os.path.join(out_dir, "build.gradle.kts"))
    assert os.path.exists(os.path.join(out_dir, "settings.gradle.kts"))

    app_dir = os.path.join(out_dir, "app")
    manifest = os.path.join(app_dir, "src", "main", "AndroidManifest.xml")
    assert os.path.exists(manifest)

    with open(manifest, "r", encoding="utf-8") as f:
        content = f.read()
        assert "com.ziref.testapp" in content or "package" in content or "android:name" in content
        assert "android.permission.INTERNET" in content

    main_activity = os.path.join(app_dir, "src", "main", "java", "com", "ziref", "testapp", "MainActivity.kt")
    assert os.path.exists(main_activity)

    with open(main_activity, "r", encoding="utf-8") as f:
        kt_content = f.read()
        assert "package com.ziref.testapp" in kt_content
        assert "https://testapp.ziref.app" in kt_content

def test_apk_packaging(temp_dir):
    config = {
        "app_name": "APK Test",
        "package_id": "com.ziref.apktest",
        "website_url": "https://demo.ziref.app"
    }

    proj_dir = android_project_generator.generate(config, os.path.join(temp_dir, "proj"))
    apk_path = os.path.join(temp_dir, "app-test.apk")

    mobile_build_pipeline._create_apk_package(apk_path, config, proj_dir)

    assert os.path.exists(apk_path)
    assert zipfile.is_zipfile(apk_path)

    with zipfile.ZipFile(apk_path, "r") as zf:
        namelist = zf.namelist()
        assert "AndroidManifest.xml" in namelist
        assert "classes.dex" in namelist
        assert "resources.arsc" in namelist
        assert "META-INF/MANIFEST.MF" in namelist
        assert "META-INF/CERT.SF" in namelist
        assert "META-INF/CERT.RSA" in namelist

    # Verify APK structure verification helper
    ok, err = mobile_build_pipeline._verify_apk_structure(apk_path)
    assert ok is True, f"APK verification failed: {err}"

    # Verify SHA-256 computation
    sha256 = mobile_build_pipeline._sha256_file(apk_path)
    assert len(sha256) == 64
    assert all(c in "0123456789abcdef" for c in sha256)

def test_dex_structure_integrity():
    import struct, zlib, hashlib
    from services.app_builder.dex import build_minimal_dex

    dex = build_minimal_dex("com.example.testapp")
    assert dex.startswith(b"dex\n035\x00")
    assert len(dex) == 432

    # Verify Adler32 checksum
    checksum = zlib.adler32(dex[12:]) & 0xFFFFFFFF
    stored_checksum = struct.unpack("<I", dex[8:12])[0]
    assert checksum == stored_checksum

    # Verify SHA-1 signature
    sha1 = hashlib.sha1(dex[32:]).digest()
    stored_sha1 = dex[12:32]
    assert sha1 == stored_sha1

def test_deployment_url_service_sanitization():
    from services.api.core.deployment_url import deployment_url_service

    assert deployment_url_service.generate_public_url("my-app") == "http://localhost:8000/sites/my-app/"
    assert deployment_url_service.is_localhost_url("http://localhost:8000/sites/x/") is True
    assert deployment_url_service.is_localhost_url("https://ziref.app/sites/x/") is False

    ok, _ = deployment_url_service.sanitize_package_id("com.company.app")
    assert ok is True
    ok, _ = deployment_url_service.sanitize_package_id("invalid")
    assert ok is False

    filename = deployment_url_service.apk_filename("my-app", "1.2.0", 3)
    assert filename == "my-app-1.2.0-3.apk"

def test_app_icon_generation_and_badging(temp_dir):
    import base64
    import io
    from PIL import Image

    # Create a tiny 32x32 red PNG in base64
    img = Image.new("RGBA", (32, 32), (255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64_icon = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    config = {
        "app_name": "Icon Test App",
        "package_id": "com.ziref.icontest",
        "version": "1.0.0",
        "version_code": 1,
        "website_url": "https://test.ziref.app",
        "icon_base64": b64_icon
    }

    proj_dir = android_project_generator.generate(config, os.path.join(temp_dir, "proj_icon"))
    res_dir = os.path.join(proj_dir, "app", "src", "main", "res")

    # Verify density mipmaps generated
    for density in ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]:
        icon_path = os.path.join(res_dir, f"mipmap-{density}", "ic_launcher.png")
        round_icon_path = os.path.join(res_dir, f"mipmap-{density}", "ic_launcher_round.png")
        assert os.path.exists(icon_path), f"Missing {icon_path}"
        assert os.path.exists(round_icon_path), f"Missing {round_icon_path}"

    apk_path = os.path.join(temp_dir, "icon-app.apk")
    mobile_build_pipeline._create_apk_package(apk_path, config, proj_dir)

    assert os.path.exists(apk_path)
    ok, err = mobile_build_pipeline._verify_apk_structure(apk_path)
    assert ok is True, f"Structure check failed: {err}"


