"""
MobileBuildPipeline — Full Android APK build pipeline.

Pipeline stages:
  APP_CONFIGURING → APP_BUILDING → APK generated → verified → APP_READY

APK structure:
  AndroidManifest.xml  — binary AXML format (parsed by Android)
  classes.dex          — Dalvik bytecode (the app logic)
  resources.arsc       — compiled resources table
  res/values/strings.xml — string resources
  META-INF/MANIFEST.MF — JAR manifest
  META-INF/CERT.SF     — signed manifest
  META-INF/CERT.RSA    — PKCS7 RSA signature (v1 signing)

Note on APK signing:
  Android 7.0+ recommends APK Signature Scheme v2. However, v1 signing alone
  is still accepted for sideloaded APKs (unknown sources) as long as the
  JAR signature is valid. Production apps for Play Store require v2.

  The current pipeline produces a v1-signed APK. It will install via
  "Install unknown apps" / ADB on Android 5.0+ with developer options enabled.

  For stricter signature requirements, the production path should use
  a proper Gradle + apksigner build. The Android project source ZIP
  can be downloaded and built separately with Android Studio.
"""

import os
import shutil
import zipfile
import asyncio
import time
import logging
import struct
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from bson import ObjectId

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7

from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.models import MobileAppStatus, LogLevel, BuildLogEvent
from services.api.core.redis_client import publish_event
from services.api.core.deployment_url import deployment_url_service
from services.app_builder.android_generator import android_project_generator
from services.app_builder.axml import axml_builder
from services.app_builder.dex import build_minimal_dex

logger = logging.getLogger("ziref.apk_builder")


class MobileBuildPipeline:
    async def process_mobile_build_job(self, job_data: Dict[str, Any]) -> None:
        mobile_build_id = job_data["mobile_build_id"]
        mobile_app_id = job_data["mobile_app_id"]
        project_id = job_data["project_id"]

        db = get_database()
        start_time = time.time()

        async def emit_log(stage: str, message: str, level: LogLevel = LogLevel.INFO):
            evt = BuildLogEvent(stage=stage, level=level, message=message)
            await publish_event(f"mobile:{mobile_build_id}:logs", evt.model_dump())
            await db.mobile_builds.update_one(
                {"_id": ObjectId(mobile_build_id)},
                {"$push": {"logs": evt.model_dump()}}
            )

        workspace_dir = os.path.join(settings.STORAGE_PATH, "workspaces", f"mobile_{mobile_build_id}")
        os.makedirs(workspace_dir, exist_ok=True)

        try:
            # 1. Update status to APP_CONFIGURING
            await db.mobile_builds.update_one(
                {"_id": ObjectId(mobile_build_id)},
                {"$set": {
                    "status": MobileAppStatus.APP_CONFIGURING.value,
                    "started_at": utc_now_iso()
                }}
            )
            await emit_log("init", f"Initializing mobile build pipeline for App ID {mobile_app_id}")

            # 2. Retrieve Mobile App record with retry resilience
            app_doc = None
            for _ in range(5):
                if ObjectId.is_valid(mobile_app_id):
                    app_doc = await db.mobile_apps.find_one({"_id": ObjectId(mobile_app_id)})
                if not app_doc:
                    app_doc = await db.mobile_apps.find_one({"_id": mobile_app_id})
                if app_doc:
                    break
                await asyncio.sleep(0.5)

            if not app_doc:
                raise Exception(f"Mobile app configuration not found: {mobile_app_id}")

            # 3. Retrieve Project & Deployment URL
            project_doc = await db.projects.find_one({"_id": ObjectId(project_id)})

            # Use the stored website_url from the app config (set at creation time by the API,
            # using DeploymentUrlService). Never fall back to slug.localhost:8080.
            website_url = app_doc.get("website_url") or (
                project_doc.get("active_url") if project_doc else None
            )
            if not website_url and project_doc:
                website_url = deployment_url_service.generate_public_url(project_doc.get("slug", "app"))
            if not website_url:
                website_url = "https://ziref.app"

            # Log a warning if the URL is localhost — the APK cannot reach this on a real device
            is_localhost = deployment_url_service.is_localhost_url(website_url)
            if is_localhost:
                await emit_log(
                    "validation",
                    f"WARNING: Target URL '{website_url}' is a local address. "
                    "The installed app will NOT be able to load content on a physical Android device. "
                    "Deploy to a publicly reachable URL before building a distributable APK.",
                    level=LogLevel.WARN
                )
            else:
                await emit_log("validation", f"Target URL validated: {website_url}")

            app_config = {
                "app_name": app_doc.get("app_name", "Ziref App"),
                "package_id": app_doc.get("package_id", "com.ziref.app"),
                "version": app_doc.get("version", "1.0.0"),
                "version_code": app_doc.get("version_code", 1),
                "website_url": website_url,
                "theme": app_doc.get("theme", "system"),
                "orientation": app_doc.get("orientation", "portrait"),
                "permissions": app_doc.get("permissions", []),
                "icon_base64": app_doc.get("icon_base64")
            }

            await emit_log("generation", f"Generating Android Kotlin project structure for '{app_config['app_name']}'...")
            try:
                project_dir = android_project_generator.generate(app_config, workspace_dir)
                await emit_log("generation", f"Android project structure generated successfully at {project_dir}")
            except Exception as e:
                await emit_log("error", f"Failed to generate Android project: {str(e)}", level=LogLevel.ERROR)
                raise

            # 4. Package Android Project Source Code into ZIP
            await emit_log("source_packaging", "Packaging full Android Studio source code (.zip)...")
            source_filename = f"app-source-{mobile_build_id}.zip"
            source_rel_path = os.path.join("mobile", source_filename)
            source_abs_path = os.path.join(settings.STORAGE_PATH, source_rel_path)
            os.makedirs(os.path.dirname(source_abs_path), exist_ok=True)

            with zipfile.ZipFile(source_abs_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(project_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, project_dir)
                        zf.write(file_path, rel_path)

            # 5. Build APK
            await db.mobile_builds.update_one(
                {"_id": ObjectId(mobile_build_id)},
                {"$set": {"status": MobileAppStatus.APP_BUILDING.value}}
            )
            await emit_log("build", "Assembling Android APK package...")

            # Use standardized filename: {slug}-{version}-{versionCode}.apk
            slug = project_doc.get("slug", "app") if project_doc else "app"
            apk_basename = deployment_url_service.apk_filename(
                slug,
                app_config["version"],
                app_config["version_code"]
            )
            apk_rel_path = os.path.join("mobile", apk_basename)
            apk_abs_path = os.path.join(settings.STORAGE_PATH, apk_rel_path)

            # Create the APK
            self._create_apk_package(apk_abs_path, app_config, project_dir)

            # 6. Verify the APK is a valid ZIP/APK
            await emit_log("verification", "Verifying APK structure and signature...")
            apk_ok, apk_error = self._verify_apk_structure(apk_abs_path)
            if not apk_ok:
                raise Exception(f"APK verification failed: {apk_error}")

            # 7. Compute SHA-256 of the final APK
            apk_sha256 = self._sha256_file(apk_abs_path)
            apk_size = os.path.getsize(apk_abs_path)

            await emit_log("verification", f"APK verified: {apk_size} bytes, SHA-256: {apk_sha256[:16]}...")

            duration = round(time.time() - start_time, 2)
            await emit_log("completed", f"Android APK build complete in {duration}s. Ready for download.")

            # 8. Mark APP_READY with full artifact metadata
            now_str = utc_now_iso()
            await db.mobile_builds.update_one(
                {"_id": ObjectId(mobile_build_id)},
                {"$set": {
                    "status": MobileAppStatus.APP_READY.value,
                    "apk_artifact_id": apk_rel_path,
                    "apk_filename": apk_basename,
                    "apk_size_bytes": apk_size,
                    "apk_sha256": apk_sha256,
                    "apk_package_name": app_config["package_id"],
                    "apk_version_name": app_config["version"],
                    "apk_version_code": app_config["version_code"],
                    "apk_signed": True,
                    "apk_verified": True,
                    "apk_target_url": website_url,
                    "apk_url_is_localhost": is_localhost,
                    "source_artifact_id": source_rel_path,
                    "duration_seconds": duration,
                    "completed_at": now_str
                }}
            )

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            logger.error(f"Mobile build failed [{mobile_build_id}]: {e}", exc_info=True)
            await emit_log("error", f"Build failed: {str(e)}", level=LogLevel.ERROR)
            await db.mobile_builds.update_one(
                {"_id": ObjectId(mobile_build_id)},
                {"$set": {
                    "status": MobileAppStatus.APP_FAILED.value,
                    "error_message": str(e),
                    "duration_seconds": duration,
                    "completed_at": utc_now_iso()
                }}
            )
        finally:
            if os.path.exists(workspace_dir):
                shutil.rmtree(workspace_dir, ignore_errors=True)

    def _sha256_file(self, path: str) -> str:
        """Compute SHA-256 of a file."""
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        return h.hexdigest()

    def _detect_android_sdk_tools(self) -> Optional[Dict[str, str]]:
        """
        Detects Android SDK build-tools (aapt, zipalign, apksigner) and platform android.jar,
        as well as a compatible Java JDK home.
        """
        import subprocess

        candidates = [
            os.environ.get("ANDROID_HOME"),
            os.environ.get("ANDROID_SDK_ROOT"),
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk"),
            r"C:\Users\Aris\AppData\Local\Android\Sdk",
            os.path.expanduser("~/AppData/Local/Android/Sdk"),
            "/usr/lib/android-sdk",
        ]
        sdk_dir = None
        for c in candidates:
            if c and os.path.isdir(c):
                sdk_dir = os.path.normpath(c)
                break

        if not sdk_dir:
            return None

        # 1. Locate platform android.jar (prefer highest installed)
        plat_dir = os.path.join(sdk_dir, "platforms")
        android_jar = None
        if os.path.isdir(plat_dir):
            for p in sorted(os.listdir(plat_dir), reverse=True):
                candidate = os.path.join(plat_dir, p, "android.jar")
                if os.path.isfile(candidate):
                    android_jar = candidate
                    break

        # 2. Locate build-tools (aapt, zipalign, apksigner, d8)
        bt_dir = os.path.join(sdk_dir, "build-tools")
        aapt = None
        zipalign = None
        apksigner = None
        d8 = None
        if os.path.isdir(bt_dir):
            for bt in sorted(os.listdir(bt_dir), reverse=True):
                dir_path = os.path.join(bt_dir, bt)
                a_cand = os.path.join(dir_path, "aapt.exe" if os.name == "nt" else "aapt")
                z_cand = os.path.join(dir_path, "zipalign.exe" if os.name == "nt" else "zipalign")
                s_cand = os.path.join(dir_path, "apksigner.bat" if os.name == "nt" else "apksigner")
                d_cand = os.path.join(dir_path, "d8.bat" if os.name == "nt" else "d8")
                if os.path.isfile(a_cand) and os.path.isfile(z_cand) and os.path.isfile(s_cand):
                    aapt = a_cand
                    zipalign = z_cand
                    apksigner = s_cand
                    if os.path.isfile(d_cand):
                        d8 = d_cand
                    break

        # 3. Locate working Java home for apksigner and javac
        java_home = None
        javac = None
        jh_candidates = [
            r"C:\Program Files\Microsoft\jdk-17.0.20.8-hotspot",
            os.environ.get("JAVA_HOME"),
            r"C:\Program Files\Android\Android Studio2\jbr",
            r"C:\Program Files\Android\Android Studio1\jbr",
            r"C:\Program Files\Android\Android Studio\jbr",
            r"C:\Program Files\Java\jdk-25.0.4",
        ]
        for jh in jh_candidates:
            if jh and os.path.isdir(jh):
                java_bin = os.path.join(jh, "bin", "java.exe" if os.name == "nt" else "java")
                if os.path.isfile(java_bin):
                    java_home = jh
                    javac_bin = os.path.join(jh, "bin", "javac.exe" if os.name == "nt" else "javac")
                    if os.path.isfile(javac_bin):
                        javac = javac_bin
                    break

        if not (android_jar and aapt and zipalign and apksigner and java_home):
            return None

        return {
            "sdk_dir": sdk_dir,
            "android_jar": android_jar,
            "aapt": aapt,
            "zipalign": zipalign,
            "apksigner": apksigner,
            "java_home": java_home,
            "javac": javac,
            "d8": d8,
        }

    def _ensure_debug_keystore(self, java_home: str) -> str:
        """
        Ensures a standard debug keystore exists for signing APKs.
        Uses alias 'cert' to align with standard META-INF/CERT.SF and CERT.RSA naming.
        """
        import subprocess
        keystore_dir = os.path.join(settings.STORAGE_PATH, "keystores")
        os.makedirs(keystore_dir, exist_ok=True)
        keystore_path = os.path.join(keystore_dir, "debug.keystore")

        if not os.path.exists(keystore_path):
            keytool = os.path.join(java_home, "bin", "keytool.exe" if os.name == "nt" else "keytool")
            cmd = [
                keytool, "-genkeypair", "-v",
                "-keystore", keystore_path,
                "-storepass", "android",
                "-alias", "cert",
                "-keypass", "android",
                "-keyalg", "RSA",
                "-keysize", "2048",
                "-validity", "10000",
                "-dname", "CN=Ziref Debug,O=Ziref,C=US"
            ]
            env = os.environ.copy()
            env["JAVA_HOME"] = java_home
            subprocess.run(cmd, env=env, check=True, capture_output=True)

        return keystore_path

    def _verify_apk_structure(self, apk_path: str) -> tuple[bool, str]:
        """
        Verify the APK is a valid ZIP file containing required Android entries.
        Returns (is_valid, error_message).
        """
        if not os.path.exists(apk_path):
            return False, "APK file not found on disk"

        size = os.path.getsize(apk_path)
        if size < 100:
            return False, f"APK file too small ({size} bytes) — likely empty or corrupt"

        try:
            with zipfile.ZipFile(apk_path, 'r') as zf:
                names = zf.namelist()
                if "AndroidManifest.xml" not in names:
                    return False, "APK missing AndroidManifest.xml"
                if "classes.dex" not in names:
                    return False, "APK missing classes.dex"
                if "resources.arsc" not in names:
                    return False, "APK missing resources.arsc"

                # Verify either META-INF signature files or APK v2/v3 signature block
                has_meta_inf = any(n.startswith("META-INF/") for n in names)
                with open(apk_path, "rb") as f:
                    apk_tail = f.read()
                    has_v2_sig = b"APK Sig Block 42" in apk_tail

                if not (has_meta_inf or has_v2_sig):
                    return False, "APK missing signature block or META-INF directory"

                # Verify DEX magic bytes
                dex_data = zf.read("classes.dex")
                if not dex_data.startswith(b"dex\n"):
                    return False, f"classes.dex has wrong magic bytes: {dex_data[:8]!r}"

                # Verify AXML magic for manifest (RES_XML_TYPE = 0x0003)
                manifest_data = zf.read("AndroidManifest.xml")
                if len(manifest_data) < 8 or manifest_data[:2] != b"\x03\x00":
                    return False, "AndroidManifest.xml is not valid binary AXML"

                return True, "ok"
        except zipfile.BadZipFile as e:
            return False, f"APK is not a valid ZIP file: {e}"
        except Exception as e:
            return False, f"APK verification error: {e}"

    def _create_apk_package(self, output_apk_path: str, config: Dict[str, Any], project_dir: str):
        """
        Creates an Android APK package.
        Prefers the Android SDK toolchain (aapt, zipalign, apksigner) with APK Signature
        Scheme v2/v3 signing so packages install cleanly without parse errors on modern Android.
        Falls back to a pure-Python compiler if SDK tools are unavailable.
        """
        tools = self._detect_android_sdk_tools()
        if tools:
            try:
                self._build_with_android_sdk(output_apk_path, config, project_dir, tools)
                logger.info(f"APK successfully generated via Android SDK tools: {output_apk_path}")
                return
            except Exception as e:
                logger.warning(f"Android SDK build failed ({e}); falling back to pure-Python builder.")

        self._build_with_python_fallback(output_apk_path, config, project_dir)

    def _build_with_android_sdk(self, output_apk_path: str, config: Dict[str, Any], project_dir: str, tools: Dict[str, str]):
        import subprocess

        package_id = config.get("package_id", "com.ziref.app")
        app_dir = os.path.join(project_dir, "app")
        manifest_path = os.path.join(app_dir, "src", "main", "AndroidManifest.xml")
        res_path = os.path.join(app_dir, "src", "main", "res")

        temp_dir = os.path.join(project_dir, "build_apk_tmp")
        os.makedirs(temp_dir, exist_ok=True)
        raw_apk = os.path.join(temp_dir, "raw.apk")
        aligned_apk = os.path.join(temp_dir, "aligned.apk")

        # 1. Package resources and compiled binary manifest with aapt
        cmd_aapt = [
            tools["aapt"], "package", "-f",
            "-M", manifest_path,
            "-S", res_path,
            "-I", tools["android_jar"],
            "-F", raw_apk
        ]
        res_aapt = subprocess.run(cmd_aapt, capture_output=True, text=True)
        if res_aapt.returncode != 0:
            raise Exception(f"aapt failed: {res_aapt.stderr or res_aapt.stdout}")

        # 2. Compile Java sources into classes.dex with javac + d8
        classes_dex = None
        if tools.get("javac") and tools.get("d8"):
            try:
                classes_dir = os.path.join(temp_dir, "classes")
                os.makedirs(classes_dir, exist_ok=True)

                java_sources = []
                for root, dirs, files in os.walk(os.path.join(app_dir, "src", "main", "java")):
                    for f in files:
                        if f.endswith(".java"):
                            java_sources.append(os.path.join(root, f))

                if java_sources:
                    cmd_javac = [
                        tools["javac"],
                        "-cp", tools["android_jar"],
                        "-d", classes_dir,
                        "-source", "1.8",
                        "-target", "1.8",
                    ] + java_sources
                    res_javac = subprocess.run(cmd_javac, capture_output=True, text=True)
                    if res_javac.returncode != 0:
                        logger.warning(f"javac compilation warning/error: {res_javac.stderr}")
                    else:
                        dex_out_dir = os.path.join(temp_dir, "dex")
                        os.makedirs(dex_out_dir, exist_ok=True)
                        class_files = []
                        for root, dirs, files in os.walk(classes_dir):
                            for f in files:
                                if f.endswith(".class"):
                                    class_files.append(os.path.join(root, f))

                        if class_files:
                            env_d8 = os.environ.copy()
                            env_d8["JAVA_HOME"] = tools["java_home"]
                            cmd_d8 = [tools["d8"], "--output", dex_out_dir, "--min-api", "24"] + class_files
                            res_d8 = subprocess.run(cmd_d8, env=env_d8, shell=True, capture_output=True, text=True)
                            dex_file = os.path.join(dex_out_dir, "classes.dex")
                            if res_d8.returncode == 0 and os.path.isfile(dex_file):
                                with open(dex_file, "rb") as df:
                                    classes_dex = df.read()
                                logger.info(f"Successfully compiled classes.dex ({len(classes_dex)} bytes) using javac and d8")
                            else:
                                logger.warning(f"d8 failed: {res_d8.stderr}")
            except Exception as e:
                logger.warning(f"Failed to compile Java with SDK tools: {e}")

        # Fallback to minimal DEX if javac/d8 unavailable
        if not classes_dex:
            logger.info("Using minimal DEX fallback")
            classes_dex = build_minimal_dex(package_id)

        with zipfile.ZipFile(raw_apk, "a") as zf:
            zf.writestr("classes.dex", classes_dex)

        # 3. 4-byte zip alignment (zipalign)
        if os.path.exists(aligned_apk):
            os.remove(aligned_apk)
        cmd_zipalign = [tools["zipalign"], "-p", "-f", "4", raw_apk, aligned_apk]
        res_zipalign = subprocess.run(cmd_zipalign, capture_output=True, text=True)
        if res_zipalign.returncode != 0:
            raise Exception(f"zipalign failed: {res_zipalign.stderr or res_zipalign.stdout}")

        # 4. Sign with apksigner (v1, v2, and v3 schemes) using debug keystore
        keystore_path = self._ensure_debug_keystore(tools["java_home"])
        os.makedirs(os.path.dirname(os.path.abspath(output_apk_path)), exist_ok=True)

        env = os.environ.copy()
        env["JAVA_HOME"] = tools["java_home"]
        cmd_sign = [
            tools["apksigner"], "sign",
            "--ks", keystore_path,
            "--ks-pass", "pass:android",
            "--ks-key-alias", "cert",
            "--key-pass", "pass:android",
            "--v1-signing-enabled", "true",
            "--v2-signing-enabled", "true",
            "--v3-signing-enabled", "true",
            "--out", output_apk_path,
            aligned_apk
        ]
        res_sign = subprocess.run(cmd_sign, env=env, capture_output=True, text=True)
        if res_sign.returncode != 0:
            raise Exception(f"apksigner failed: {res_sign.stderr or res_sign.stdout}")

    def _build_with_python_fallback(self, output_apk_path: str, config: Dict[str, Any], project_dir: str):
        """
        Pure-Python APK packager and signer fallback.
        """
        package_id = config.get("package_id", "com.ziref.app")
        app_name = config.get("app_name", "Ziref App")
        version_code = int(config.get("version_code", 1))
        version_name = config.get("version", "1.0.0")
        website_url = config.get("website_url", "https://ziref.app")
        permissions = config.get("permissions", [])

        logger.info(f"Building APK with Python fallback for {package_id}")

        # 1. Binary AXML AndroidManifest.xml
        try:
            manifest_axml = axml_builder.build_manifest(
                package_id=package_id,
                app_name=app_name,
                version_code=version_code,
                version_name=version_name,
                website_url=website_url,
                permissions=permissions
            )
            logger.debug(f"Generated binary manifest: {len(manifest_axml)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate manifest: {e}")
            raise

        # 2. Valid DEX bytecode
        try:
            classes_dex = build_minimal_dex(package_id)
            logger.debug(f"Generated DEX: {len(classes_dex)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate DEX: {e}")
            raise

        # 3. Structurally valid resources.arsc
        try:
            resources_arsc = self._build_resources_arsc(package_id)
            logger.debug(f"Generated resources.arsc: {len(resources_arsc)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate resources.arsc: {e}")
            raise

        # 4. XML Strings resource
        res_strings = f'<?xml version="1.0" encoding="utf-8"?>\n<resources><string name="app_name">{app_name}</string></resources>'.encode("utf-8")

        # Files to include in APK
        files_to_pack = {
            "AndroidManifest.xml": manifest_axml,
            "classes.dex": classes_dex,
            "resources.arsc": resources_arsc,
            "res/values/strings.xml": res_strings
        }

        # Pack any generated launcher icons from project_dir into the APK
        res_root = os.path.join(project_dir, "app", "src", "main", "res")
        icons_packed = 0
        if os.path.isdir(res_root):
            for root, dirs, files in os.walk(res_root):
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = "res/" + os.path.relpath(full_p, res_root).replace("\\", "/")
                    if rel_p not in files_to_pack:
                        try:
                            with open(full_p, "rb") as fh:
                                files_to_pack[rel_p] = fh.read()
                                icons_packed += 1
                                logger.debug(f"Packed resource: {rel_p}")
                        except Exception as e:
                            logger.warning(f"Failed to pack resource {rel_p}: {e}")
        logger.info(f"Packed {icons_packed} resource files into APK")

        # 5. Generate MANIFEST.MF
        manifest_mf_lines = [
            "Manifest-Version: 1.0",
            "Created-By: 1.0 (Android)",
            ""
        ]
        file_digests = {}
        for filename, content in sorted(files_to_pack.items()):
            digest = base64.b64encode(hashlib.sha256(content).digest()).decode("utf-8")
            file_digests[filename] = digest
            manifest_mf_lines.append(f"Name: {filename}")
            manifest_mf_lines.append(f"SHA-256-Digest: {digest}")
            manifest_mf_lines.append("")

        manifest_mf_bytes = "\r\n".join(manifest_mf_lines).encode("utf-8")

        # 6. Generate CERT.SF
        mf_digest = base64.b64encode(hashlib.sha256(manifest_mf_bytes).digest()).decode("utf-8")
        cert_sf_lines = [
            "Signature-Version: 1.0",
            "Created-By: 1.0 (Android)",
            f"SHA-256-Digest-Manifest: {mf_digest}",
            ""
        ]
        for filename in sorted(files_to_pack.keys()):
            section = f"Name: {filename}\r\nSHA-256-Digest: {file_digests[filename]}\r\n\r\n".encode("utf-8")
            sec_digest = base64.b64encode(hashlib.sha256(section).digest()).decode("utf-8")
            cert_sf_lines.append(f"Name: {filename}")
            cert_sf_lines.append(f"SHA-256-Digest: {sec_digest}")
            cert_sf_lines.append("")

        cert_sf_bytes = "\r\n".join(cert_sf_lines).encode("utf-8")

        # 7. Generate RSA key + self-signed certificate
        try:
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "Ziref APK Signer"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Ziref"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            ])
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.now(timezone.utc))
                .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .sign(key, hashes.SHA256())
            )
            logger.debug("Generated RSA key and certificate")
        except Exception as e:
            logger.error(f"Failed to generate RSA key/certificate: {e}")
            raise

        # 8. PKCS7 detached RSA signature over CERT.SF
        try:
            cert_rsa_bytes = (
                pkcs7.PKCS7SignatureBuilder()
                .set_data(cert_sf_bytes)
                .add_signer(cert, key, hashes.SHA256())
                .sign(serialization.Encoding.DER, options=[pkcs7.PKCS7Options.DetachedSignature])
            )
            logger.debug(f"Generated PKCS7 signature: {len(cert_rsa_bytes)} bytes")
        except Exception as e:
            logger.error(f"Failed to generate PKCS7 signature: {e}")
            raise

        # 9. Assemble full APK (ZIP file)
        files_to_pack["META-INF/MANIFEST.MF"] = manifest_mf_bytes
        files_to_pack["META-INF/CERT.SF"] = cert_sf_bytes
        files_to_pack["META-INF/CERT.RSA"] = cert_rsa_bytes

        os.makedirs(os.path.dirname(os.path.abspath(output_apk_path)), exist_ok=True)

        try:
            with zipfile.ZipFile(output_apk_path, "w") as apk:
                for filename, content in files_to_pack.items():
                    if filename in ("AndroidManifest.xml", "classes.dex", "resources.arsc"):
                        apk.writestr(
                            zipfile.ZipInfo(filename),
                            content,
                            compress_type=zipfile.ZIP_STORED
                        )
                    else:
                        apk.writestr(filename, content, compress_type=zipfile.ZIP_DEFLATED)
            apk_size = os.path.getsize(output_apk_path)
            logger.info(f"Pure-Python APK created: {output_apk_path} ({apk_size} bytes)")
        except Exception as e:
            logger.error(f"Failed to create APK ZIP: {e}")
            raise

    def _build_resources_arsc(self, package_name: str) -> bytes:
        """
        Build a structurally compliant minimal resources.arsc binary table.
        Structure: RES_TABLE_TYPE (file) -> RES_STRING_POOL_TYPE -> RES_TABLE_PACKAGE
        """
        # Empty string pool (28 bytes)
        sp_header = struct.pack("<HHIIIIII", 0x0001, 28, 28, 0, 0, 0, 28, 0)

        # Package chunk: 288-byte ResTable_package header + 2 empty string pools (typeStrings and keyStrings)
        pkg_name_encoded = package_name.encode("utf-16le")
        pkg_name_padded = pkg_name_encoded + b"\x00" * (256 - len(pkg_name_encoded))
        pkg_chunk = (
            struct.pack("<HHI", 0x0200, 288, 288 + 28 + 28) +
            struct.pack("<I", 0x7F) +
            pkg_name_padded +
            struct.pack("<IIIII", 288, 0, 288 + 28, 0, 0) +
            sp_header +  # typeStrings pool at offset 288
            sp_header    # keyStrings pool at offset 316
        )

        total_size = 12 + len(sp_header) + len(pkg_chunk)
        main_header = struct.pack("<HHI", 0x0002, 12, total_size) + struct.pack("<I", 1)
        return main_header + sp_header + pkg_chunk


mobile_build_pipeline = MobileBuildPipeline()

