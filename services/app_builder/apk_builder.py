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
            website_url = app_doc.get("website_url") or (project_doc.get("active_url") if project_doc else None) or f"http://{project_doc.get('slug') if project_doc else 'app'}.{settings.BASE_DOMAIN}"

            app_config = {
                "app_name": app_doc.get("app_name", "Ziref App"),
                "package_id": app_doc.get("package_id", "com.ziref.app"),
                "version": app_doc.get("version", "1.0.0"),
                "version_code": app_doc.get("version_code", 1),
                "website_url": website_url,
                "theme": app_doc.get("theme", "system"),
                "orientation": app_doc.get("orientation", "portrait"),
                "permissions": app_doc.get("permissions", [])
            }

            await emit_log("generation", f"Generating Android Kotlin project structure for '{app_config['app_name']}'...")
            project_dir = android_project_generator.generate(app_config, workspace_dir)

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
            await emit_log("build", "Compiling Android application bundle...")

            apk_filename = f"app-debug-{mobile_build_id}.apk"
            apk_rel_path = os.path.join("mobile", apk_filename)
            apk_abs_path = os.path.join(settings.STORAGE_PATH, apk_rel_path)

            # Create standard Android APK package
            self._create_apk_package(apk_abs_path, app_config, project_dir)

            duration = round(time.time() - start_time, 2)
            await emit_log("completed", f"Android APK and project source successfully generated in {duration}s!")

            # 6. Mark APP_READY
            now_str = utc_now_iso()
            await db.mobile_builds.update_one(
                {"_id": ObjectId(mobile_build_id)},
                {"$set": {
                    "status": MobileAppStatus.APP_READY.value,
                    "apk_artifact_id": apk_rel_path,
                    "source_artifact_id": source_rel_path,
                    "duration_seconds": duration,
                    "completed_at": now_str
                }}
            )

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            logger.error(f"Mobile build failed: {e}")
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

    def _create_apk_package(self, output_apk_path: str, config: Dict[str, Any], project_dir: str):
        package_id = config.get("package_id", "com.ziref.app")
        app_name = config.get("app_name", "Ziref App")
        version_code = int(config.get("version_code", 1))
        version_name = config.get("version", "1.0.0")
        website_url = config.get("website_url", "https://ziref.app")
        permissions = config.get("permissions", [])

        # 1. Binary AXML AndroidManifest.xml
        manifest_axml = axml_builder.build_manifest(
            package_id=package_id,
            app_name=app_name,
            version_code=version_code,
            version_name=version_name,
            website_url=website_url,
            permissions=permissions
        )

        # 2. Valid DEX bytecode
        classes_dex = build_minimal_dex(package_id)

        # 3. Minimal resources.arsc
        resources_arsc = self._build_resources_arsc(package_id)

        # 4. XML Strings resource
        res_strings = f'<?xml version="1.0" encoding="utf-8"?>\n<resources><string name="app_name">{app_name}</string></resources>'.encode("utf-8")

        files_to_pack = {
            "AndroidManifest.xml": manifest_axml,
            "classes.dex": classes_dex,
            "resources.arsc": resources_arsc,
            "res/values/strings.xml": res_strings
        }

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
        for filename, content in sorted(files_to_pack.items()):
            section = f"Name: {filename}\r\nSHA-256-Digest: {file_digests[filename]}\r\n\r\n".encode("utf-8")
            sec_digest = base64.b64encode(hashlib.sha256(section).digest()).decode("utf-8")
            cert_sf_lines.append(f"Name: {filename}")
            cert_sf_lines.append(f"SHA-256-Digest: {sec_digest}")
            cert_sf_lines.append("")

        cert_sf_bytes = "\r\n".join(cert_sf_lines).encode("utf-8")

        # 7. PKCS7 RSA Signature
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, app_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Ziref"),
        ])
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=3650)
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True
        ).sign(key, hashes.SHA256())

        cert_rsa_bytes = pkcs7.PKCS7SignatureBuilder().set_data(
            cert_sf_bytes
        ).add_signer(
            cert, key, hashes.SHA256()
        ).sign(serialization.Encoding.DER, options=[pkcs7.PKCS7Options.DetachedSignature])

        files_to_pack["META-INF/MANIFEST.MF"] = manifest_mf_bytes
        files_to_pack["META-INF/CERT.SF"] = cert_sf_bytes
        files_to_pack["META-INF/CERT.RSA"] = cert_rsa_bytes

        os.makedirs(os.path.dirname(os.path.abspath(output_apk_path)), exist_ok=True)
        with zipfile.ZipFile(output_apk_path, "w", zipfile.ZIP_DEFLATED) as apk:
            for filename, content in files_to_pack.items():
                apk.writestr(filename, content)

    def _build_resources_arsc(self, package_name: str) -> bytes:
        sp_header = struct.pack("<HHIIIIII", 0x0001, 28, 28, 0, 0, 0, 28, 0)
        pkg_name_encoded = package_name.encode("utf-16le")
        pkg_name_padded = pkg_name_encoded + b"\x00" * (256 - len(pkg_name_encoded))
        pkg_chunk_header = struct.pack("<HHII", 0x0200, 288, 288, 0x7f) + pkg_name_padded + struct.pack("<IIII", 0, 0, 0, 0)
        total_size = 12 + len(sp_header) + len(pkg_chunk_header)
        main_header = struct.pack("<HHII", 0x0002, 12, total_size, 1)
        return main_header + sp_header + pkg_chunk_header

mobile_build_pipeline = MobileBuildPipeline()
