import os
import shutil
import tarfile
import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId

from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.models import BuildStatus, BuildStage, LogLevel, BuildLogEvent, ProjectStatus
from services.api.core.redis_client import publish_event, push_job
from services.api.core.security import decrypt_secret
from services.analyzer.archive_validator import archive_validator, ArchiveSecurityError
from services.analyzer.detector import project_detector
from services.builder.docker_sandbox import docker_sandbox, SandboxExecutionError
from services.builder.diagnostics import build_diagnostic_engine

logger = logging.getLogger("ziref.build_executor")

class BuildPipelineExecutor:
    async def process_build_job(self, job_data: Dict[str, Any]) -> None:
        build_id = job_data["build_id"]
        project_id = job_data["project_id"]
        upload_id = job_data["upload_id"]

        db = get_database()
        start_time = time.time()

        # Update build status to BUILDING
        await db.builds.update_one(
            {"_id": ObjectId(build_id)},
            {"$set": {
                "status": BuildStatus.BUILDING.value,
                "started_at": datetime.now(timezone.utc).isoformat() + "Z"
            }}
        )
        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"status": ProjectStatus.BUILDING.value}}
        )

        collected_logs: list[str] = []

        async def emit_log(event: BuildLogEvent):
            collected_logs.append(event.message)
            # 1. Save to MongoDB
            await db.build_events.insert_one({
                "build_id": build_id,
                "timestamp": event.timestamp,
                "stage": event.stage,
                "level": event.level.value,
                "message": event.message
            })
            # 2. Publish to Redis channel for live SSE
            await publish_event(f"build:{build_id}:logs", event.model_dump())

        # Ephemeral workspace directory
        workspace_dir = os.path.join(settings.STORAGE_PATH, "workspaces", build_id)
        os.makedirs(workspace_dir, exist_ok=True)

        try:
            await emit_log(BuildLogEvent(
                stage=BuildStage.INIT.value,
                level=LogLevel.INFO,
                message=f"Build initialized for build ID: {build_id}"
            ))

            # Retrieve upload record
            upload_record = await db.uploads.find_one({"_id": ObjectId(upload_id)})
            if not upload_record:
                raise Exception(f"Upload record not found for ID: {upload_id}")

            zip_abs_path = os.path.join(settings.STORAGE_PATH, upload_record["storage_path"])

            # Stage: Archive Validation & Extraction
            await emit_log(BuildLogEvent(
                stage=BuildStage.VALIDATION.value,
                level=LogLevel.INFO,
                message="Validating upload archive integrity and path safety..."
            ))

            success, msg, files = archive_validator.validate_and_extract(zip_abs_path, workspace_dir)
            await emit_log(BuildLogEvent(
                stage=BuildStage.VALIDATION.value,
                level=LogLevel.INFO,
                message=f"Archive validated: extracted {len(files)} files into isolated workspace."
            ))

            # Stage: Analysis & Plan Confirmation
            await emit_log(BuildLogEvent(
                stage=BuildStage.ANALYSIS.value,
                level=LogLevel.INFO,
                message="Confirming build configuration and framework detection..."
            ))

            analysis = project_detector.analyze(workspace_dir)
            package_manager = job_data.get("package_manager") or analysis.packageManager or "npm"
            build_command = job_data.get("build_command") or analysis.buildCommand or "npm run build"
            output_directory = job_data.get("output_directory") or analysis.outputDirectory or "dist"

            await emit_log(BuildLogEvent(
                stage=BuildStage.ANALYSIS.value,
                level=LogLevel.INFO,
                message=f"Framework: {analysis.framework} | PM: {package_manager} | Output: {output_directory}"
            ))

            # Load and decrypt project environment variables
            env_vars: Dict[str, str] = {}
            cursor = db.environment_variables.find({"project_id": project_id})
            async for ev in cursor:
                decrypted = decrypt_secret(ev["encrypted_value"])
                env_vars[ev["key"]] = decrypted

            if env_vars:
                await emit_log(BuildLogEvent(
                    stage=BuildStage.SANDBOX_INIT.value,
                    level=LogLevel.INFO,
                    message=f"Injected {len(env_vars)} secure environment variables."
                ))

            # Stage: Build execution in sandbox
            out_path = await docker_sandbox.execute_build(
                workspace_dir=workspace_dir,
                package_manager=package_manager,
                build_command=build_command,
                output_directory=output_directory,
                env_vars=env_vars,
                log_callback=emit_log
            )

            # Stage: Packaging Artifact
            await emit_log(BuildLogEvent(
                stage=BuildStage.PACKAGING.value,
                level=LogLevel.INFO,
                message="Creating immutable distribution artifact..."
            ))

            artifact_filename = f"artifact-{build_id}.tar.gz"
            artifact_rel_path = os.path.join("artifacts", artifact_filename)
            artifact_abs_path = os.path.join(settings.STORAGE_PATH, artifact_rel_path)

            with tarfile.open(artifact_abs_path, "w:gz") as tar:
                tar.add(out_path, arcname=".")

            duration = round(time.time() - start_time, 2)
            await emit_log(BuildLogEvent(
                stage=BuildStage.ARTIFACT_STORAGE.value,
                level=LogLevel.INFO,
                message=f"Build artifact saved successfully in {duration}s."
            ))

            # Update build record in DB
            await db.builds.update_one(
                {"_id": ObjectId(build_id)},
                {"$set": {
                    "status": BuildStatus.BUILT.value,
                    "completed_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "duration_seconds": duration,
                    "exit_code": 0,
                    "artifact_path": artifact_rel_path
                }}
            )

            await db.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"status": ProjectStatus.BUILT.value}}
            )

            # Dispatch outbound webhook
            try:
                from services.api.core.webhooks import webhook_dispatcher
                asyncio.create_task(webhook_dispatcher.dispatch_event(
                    project_id=project_id,
                    event_type="build.completed",
                    data={"build_id": build_id, "status": "BUILT", "duration_seconds": duration}
                ))
            except Exception:
                pass

            # Trigger auto-deployment
            await push_job("deploy", {
                "build_id": build_id,
                "project_id": project_id,
                "artifact_path": artifact_rel_path
            })

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            error_msg = str(e)
            logger.error(f"Build failed for {build_id}: {error_msg}")

            await emit_log(BuildLogEvent(
                stage=BuildStage.BUILD.value,
                level=LogLevel.ERROR,
                message=f"Build failed: {error_msg}"
            ))

            # Run intelligent diagnostic engine
            diagnosis = build_diagnostic_engine.diagnose(
                collected_logs,
                exit_code=getattr(e, "exit_code", 1),
                error_message=error_msg
            )

            await emit_log(BuildLogEvent(
                stage="diagnosis",
                level=LogLevel.WARN,
                message=f"[DIAGNOSIS: {diagnosis.category}] {diagnosis.summary} -> Fix: {diagnosis.actionable_fix}"
            ))

            await db.builds.update_one(
                {"_id": ObjectId(build_id)},
                {"$set": {
                    "status": BuildStatus.FAILED.value,
                    "completed_at": datetime.now(timezone.utc).isoformat() + "Z",
                    "duration_seconds": duration,
                    "exit_code": getattr(e, "exit_code", 1),
                    "error_message": error_msg,
                    "diagnosis": diagnosis.model_dump()
                }}
            )

            await db.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"status": ProjectStatus.BUILD_FAILED.value}}
            )

            # Dispatch outbound webhook
            try:
                from services.api.core.webhooks import webhook_dispatcher
                asyncio.create_task(webhook_dispatcher.dispatch_event(
                    project_id=project_id,
                    event_type="build.failed",
                    data={
                        "build_id": build_id,
                        "status": "FAILED",
                        "error": error_msg,
                        "diagnosis": diagnosis.model_dump()
                    }
                ))
            except Exception:
                pass

        finally:
            # Cleanup workspace
            if os.path.exists(workspace_dir):
                shutil.rmtree(workspace_dir, ignore_errors=True)

build_pipeline_executor = BuildPipelineExecutor()
