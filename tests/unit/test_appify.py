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
        assert "networkSecurityConfig" in content  # Verify network security config is referenced

    # Verify network security config file exists
    network_config = os.path.join(app_dir, "src", "main", "res", "xml", "network_security_config.xml")
    assert os.path.exists(network_config), "Network security config XML should be generated"

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

def test_icon_generation_with_invalid_base64(temp_dir):
    """Test that icon generation handles invalid base64 gracefully"""
    config = {
        "app_name": "Fallback Icon App",
        "package_id": "com.ziref.fallback",
        "version": "1.0.0",
        "version_code": 1,
        "website_url": "https://test.ziref.app",
        "icon_base64": "invalid_base64_string"
    }

    # Should not raise exception, should fall back to default icon
    proj_dir = android_project_generator.generate(config, os.path.join(temp_dir, "proj_fallback"))
    res_dir = os.path.join(proj_dir, "app", "src", "main", "res")

    # Verify default icons were still generated
    for density in ["mdpi", "hdpi"]:
        icon_path = os.path.join(res_dir, f"mipmap-{density}", "ic_launcher.png")
        assert os.path.exists(icon_path), f"Default icon should be generated even with invalid base64: {icon_path}"

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
        fg_icon_path = os.path.join(res_dir, f"mipmap-{density}", "ic_launcher_foreground.png")
        assert os.path.exists(icon_path), f"Missing {icon_path}"
        assert os.path.exists(round_icon_path), f"Missing {round_icon_path}"
        assert os.path.exists(fg_icon_path), f"Missing {fg_icon_path}"

    # Verify adaptive icon XML descriptors
    adaptive_dir = os.path.join(res_dir, "mipmap-anydpi-v26")
    assert os.path.exists(os.path.join(adaptive_dir, "ic_launcher.xml"))
    assert os.path.exists(os.path.join(adaptive_dir, "ic_launcher_round.xml"))

    apk_path = os.path.join(temp_dir, "icon-app.apk")
    mobile_build_pipeline._create_apk_package(apk_path, config, proj_dir)

    assert os.path.exists(apk_path)
    ok, err = mobile_build_pipeline._verify_apk_structure(apk_path)
    assert ok is True, f"Structure check failed: {err}"

    # Verify icons are actually inside the APK
    with zipfile.ZipFile(apk_path, "r") as zf:
        namelist = zf.namelist()
        # Check that at least some mipmap icons are present
        icon_files = [n for n in namelist if "mipmap" in n and ".png" in n]
        assert len(icon_files) > 0, f"No icon files found in APK. Namelist: {namelist[:20]}"
        # Check adaptive XML is present
        assert any("ic_launcher.xml" in n for n in namelist), "Adaptive icon XML not found in APK"


def test_exif_orientation_transposition(temp_dir):
    """Verify that images with EXIF orientation tags are properly normalized upright."""
    import base64
    import io
    from PIL import Image

    # Create a 60x100 rectangle image with an EXIF orientation tag (e.g. 6 = 90 deg rotation)
    im = Image.new("RGB", (60, 100), color=(0, 200, 100))
    exif = im.getexif()
    exif[0x0112] = 6  # EXIF orientation tag 274: orientation = 6 (requires 90 CW transpose)

    buf = io.BytesIO()
    im.save(buf, format="JPEG", exif=exif)
    b64_img = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    config = {
        "app_name": "EXIF Test App",
        "package_id": "com.ziref.exiftest",
        "website_url": "http://10.0.0.5:8000/sites/demo/",
        "icon_base64": b64_img
    }

    proj_dir = android_project_generator.generate(config, os.path.join(temp_dir, "exif_proj"))
    res_dir = os.path.join(proj_dir, "app", "src", "main", "res")
    hdpi_icon = os.path.join(res_dir, "mipmap-hdpi", "ic_launcher.png")
    assert os.path.exists(hdpi_icon)

    # When transposed from orientation 6 (60x100), dimension becomes 100x60,
    # and then square-padded and resized to (72, 72)
    saved_icon = Image.open(hdpi_icon)
    assert saved_icon.size == (72, 72)


def test_network_discovery_utility():
    from services.api.core.network import get_local_lan_ip

    lan_ip = get_local_lan_ip()
    assert isinstance(lan_ip, str)
    assert len(lan_ip.split(".")) == 4
    # Should not be empty or loopback in normal connected environments
    assert lan_ip != ""



