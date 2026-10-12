import logging
from typing import Dict, Any
from bson import ObjectId

from services.api.core.database import get_database
from services.api.core.redis_client import push_job

logger = logging.getLogger("ziref.job_recovery")

async def recover_stalled_jobs() -> Dict[str, int]:
    """Recovers any queued builds or deploys that were orphaned across process restarts."""
    stats = {"builds": 0, "mobile_apps": 0, "deploys": 0}
    try:
        db = get_database()

        # 1. Recover queued web builds
        cursor = db.builds.find({"status": "QUEUED"})
        async for b in cursor:
            build_id = str(b["_id"])
            pending = await db.job_queue.find_one({"payload.build_id": build_id, "status": "pending"})
            if not pending:
                res = await db.job_queue.update_one(
                    {"payload.build_id": build_id, "status": "processing"},
                    {"$set": {"status": "pending"}}
                )
                if res.matched_count == 0:
                    await push_job("build", {
                        "build_id": build_id,
                        "project_id": b["project_id"],
                        "upload_id": b["upload_id"],
                        "package_manager": b.get("package_manager"),
                        "runtime": b.get("runtime", "static"),
                        "build_command": b.get("build_command"),
                        "output_directory": b.get("output_directory")
                    })
            stats["builds"] += 1

        if stats["builds"] > 0:
            logger.info(f"Recovered {stats['builds']} queued build jobs.")

        # 2. Recover queued mobile app builds
        m_cursor = db.mobile_builds.find({"status": "APP_QUEUED"})
        async for mb in m_cursor:
            mobile_build_id = str(mb["_id"])
            pending = await db.job_queue.find_one({"payload.mobile_build_id": mobile_build_id, "status": "pending"})
            if not pending:
                res = await db.job_queue.update_one(
                    {"payload.mobile_build_id": mobile_build_id, "status": "processing"},
                    {"$set": {"status": "pending"}}
                )
                if res.matched_count == 0:
                    await push_job("app_build", {
                        "mobile_build_id": mobile_build_id,
                        "mobile_app_id": mb["mobile_app_id"],
                        "project_id": mb["project_id"]
                    })
            stats["mobile_apps"] += 1

        if stats["mobile_apps"] > 0:
            logger.info(f"Recovered {stats['mobile_apps']} queued mobile app build jobs.")

        # 3. Recover deploy jobs for BUILT projects missing active deployments
        b_cursor = db.builds.find({"status": "BUILT"})
        async for built_b in b_cursor:
            build_id = str(built_b["_id"])
            dep = await db.deployments.find_one({"build_id": build_id})
            if not dep:
                pending_deploy = await db.job_queue.find_one({"payload.build_id": build_id, "queue": "deploy", "status": "pending"})
                if not pending_deploy:
                    res = await db.job_queue.update_one(
                        {"payload.build_id": build_id, "queue": "deploy", "status": "processing"},
                        {"$set": {"status": "pending"}}
                    )
                    if res.matched_count == 0 and built_b.get("artifact_path"):
                        await push_job("deploy", {
                            "build_id": build_id,
                            "project_id": built_b["project_id"],
                            "artifact_path": built_b["artifact_path"],
                            "runtime": built_b.get("runtime", "static")
                        })
                stats["deploys"] += 1

    except Exception as e:
        logger.warning(f"Job recovery notice: {e}")

    return stats
