import os
import tarfile
import shutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from bson import ObjectId

from services.api.core.datetime_util import utc_now_iso
from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.models import DeploymentStatus, ProjectStatus
from services.api.core.redis_client import set_project_routing, publish_event
from services.api.core.deployment_url import deployment_url_service

logger = logging.getLogger("ziref.deployer")

class DeployerService:
    async def process_deploy_job(self, job_data: Dict[str, Any]) -> str:
        build_id = job_data["build_id"]
        project_id = job_data["project_id"]
        artifact_path = job_data["artifact_path"]

        db = get_database()

        # Find project
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            raise Exception(f"Project not found: {project_id}")

        slug = project["slug"]

        # --- SINGLE CANONICAL URL ---
        # DeploymentUrlService is the only place deployment URLs are generated.
        # Frontend displays what the API returns — never invents its own URL.
        canonical_url = deployment_url_service.generate_public_url(slug)

        # Idempotency guard: prevent duplicate deployments from the same build_id
        existing_deployment = await db.deployments.find_one({"build_id": build_id})
        if existing_deployment:
            logger.warning(
                f"Deployment for build_id={build_id} already exists "
                f"({existing_deployment['_id']}). Skipping duplicate creation."
            )
            return str(existing_deployment["_id"])

        # Create Deployment Record
        deployment_doc = {
            "project_id": project_id,
            "build_id": build_id,
            "user_id": project.get("user_id"),
            "status": DeploymentStatus.DEPLOYING.value,
            "subdomain": slug,
            "url": canonical_url,
            "runtime": "static",
            "artifact_path": artifact_path,
            "created_at": utc_now_iso(),
            "completed_at": None
        }

        dep_res = await db.deployments.insert_one(deployment_doc)
        deployment_id = str(dep_res.inserted_id)


        target_deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments", deployment_id)
        os.makedirs(target_deploy_dir, exist_ok=True)

        try:
            artifact_abs_path = os.path.join(settings.STORAGE_PATH, artifact_path)
            if not os.path.exists(artifact_abs_path):
                raise Exception(f"Artifact tarball missing at: {artifact_abs_path}")

            # Extract artifact into immutable deployment directory
            with tarfile.open(artifact_abs_path, "r:gz") as tar:
                try:
                    tar.extractall(path=target_deploy_dir, filter='data')
                except TypeError:
                    tar.extractall(path=target_deploy_dir)

            # If target_deploy_dir has only 1 directory and no index.html at root, unwrap it
            if not os.path.exists(os.path.join(target_deploy_dir, "index.html")):
                entries = [e for e in os.listdir(target_deploy_dir) if not e.startswith(".")]
                if len(entries) == 1:
                    single_sub = os.path.join(target_deploy_dir, entries[0])
                    if os.path.isdir(single_sub):
                        for item in os.listdir(single_sub):
                            src = os.path.join(single_sub, item)
                            dst = os.path.join(target_deploy_dir, item)
                            if not os.path.exists(dst):
                                shutil.move(src, dst)
                        shutil.rmtree(single_sub, ignore_errors=True)

            # Mirror deployment to slug directory for direct filesystem routing resiliency
            slug_deploy_dir = os.path.join(settings.STORAGE_PATH, "deployments", slug)
            try:
                if os.path.exists(slug_deploy_dir):
                    shutil.rmtree(slug_deploy_dir, ignore_errors=True)
                shutil.copytree(target_deploy_dir, slug_deploy_dir, dirs_exist_ok=True)
            except Exception as e:
                logger.warning(f"Could not mirror deployment to slug directory {slug}: {e}")

            # Update routing cache in Redis
            await set_project_routing(slug, deployment_id, "static")

            # Mark deployment as READY
            now_str = utc_now_iso()
            await db.deployments.update_one(
                {"_id": ObjectId(deployment_id)},
                {"$set": {
                    "status": DeploymentStatus.READY.value,
                    "completed_at": now_str
                }}
            )

            # Update Project active deployment pointer
            await db.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {
                    "status": ProjectStatus.DEPLOYED.value,
                    "active_deployment_id": deployment_id,
                    "active_url": canonical_url,
                    "updated_at": now_str
                }}
            )

            logger.info(f"Deployment {deployment_id} for project '{slug}' successfully deployed to {canonical_url}")


            # Dispatch outbound webhook
            try:
                from services.api.core.webhooks import webhook_dispatcher
                import asyncio
                asyncio.create_task(webhook_dispatcher.dispatch_event(
                    project_id=project_id,
                    event_type="deployment.ready",
                    data={"deployment_id": deployment_id, "url": canonical_url, "status": "READY"}
                ))
            except Exception:
                pass


            return deployment_id

        except Exception as e:
            logger.error(f"Deployment failed for {deployment_id}: {e}")
            await db.deployments.update_one(
                {"_id": ObjectId(deployment_id)},
                {"$set": {
                    "status": DeploymentStatus.FAILED.value,
                    "completed_at": utc_now_iso()
                }}
            )
            await db.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"status": ProjectStatus.DEPLOY_FAILED.value}}
            )

            # Dispatch outbound webhook
            try:
                from services.api.core.webhooks import webhook_dispatcher
                import asyncio
                asyncio.create_task(webhook_dispatcher.dispatch_event(
                    project_id=project_id,
                    event_type="deployment.failed",
                    data={"deployment_id": deployment_id, "status": "FAILED", "error": str(e)}
                ))
            except Exception:
                pass

            raise

    async def rollback(self, project_id: str, target_deployment_id: str) -> bool:
        """Atomic rollback to a previous successful deployment."""
        db = get_database()
        project = await db.projects.find_one({"_id": ObjectId(project_id)})
        if not project:
            return False

        deployment = await db.deployments.find_one({
            "_id": ObjectId(target_deployment_id),
            "project_id": project_id,
            "status": DeploymentStatus.READY.value
        })

        if not deployment:
            return False

        slug = project["slug"]
        now_str = utc_now_iso()

        # Update Redis routing cache
        await set_project_routing(slug, target_deployment_id, "static")

        # Update project active deployment
        await db.projects.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {
                "active_deployment_id": target_deployment_id,
                "status": ProjectStatus.DEPLOYED.value,
                "updated_at": now_str
            }}
        )

        logger.info(f"Project '{slug}' rolled back to deployment {target_deployment_id}")
        return True

deployer_service = DeployerService()
