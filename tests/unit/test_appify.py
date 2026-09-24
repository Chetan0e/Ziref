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
        assert "META-INF/MANIFEST.MF" in namelist
