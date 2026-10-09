import asyncio
import signal
import logging
import sys
from typing import Dict, Any

from services.api.core.config import settings
from services.api.core.database import connect_to_database, close_database_connection
from services.api.core.redis_client import pop_job, close_redis
from services.builder.build_executor import build_pipeline_executor
from services.deployer.deployer_service import deployer_service
from services.app_builder.apk_builder import mobile_build_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [ziref.worker] %(message)s"
)
logger = logging.getLogger("ziref.worker")

running = True

def handle_exit(sig, frame):
    global running
    logger.info("Shutdown signal received. Stopping worker gracefully...")
    running = False

import json
import time
from services.api.core.datetime_util import utc_now_iso
from services.api.core.database import get_database
from services.api.core.redis_client import get_redis

async def _publish_heartbeat():
    try:
        docker_available = False
        try:
            import docker
            c = docker.from_env()
            c.ping()
            docker_available = True
        except Exception:
            docker_available = False

        heartbeat_doc = {
            "status": "online",
            "source": "worker_daemon",
            "timestamp": utc_now_iso(),
            "time": time.time(),
            "docker_available": docker_available,
            "sandbox_mode": "docker" if docker_available else "subprocess"
        }
        redis_client = await get_redis()
        if redis_client:
            await redis_client.set("ziref:worker:heartbeat", json.dumps(heartbeat_doc), ex=25)
        db = get_database()
        await db.system_status.update_one({"_id": "worker_heartbeat"}, {"$set": heartbeat_doc}, upsert=True)
    except Exception as e:
        logger.debug(f"Heartbeat write note: {e}")

async def worker_loop():
    logger.info(f"Ziref Worker started in environment: {settings.APP_ENV}")
    await connect_to_database()
    last_heartbeat = 0.0

    while running:
        try:
            # Emit periodic heartbeat every 5 seconds
            now = time.time()
            if now - last_heartbeat >= 5.0:
                last_heartbeat = now
                await _publish_heartbeat()

            # Check build queue
            build_job = await pop_job("build", timeout=1)
            if build_job:
                logger.info(f"Processing build job for build ID: {build_job.get('build_id')}")
                asyncio.create_task(build_pipeline_executor.process_build_job(build_job))
                continue

            # Check deploy queue
            deploy_job = await pop_job("deploy", timeout=1)
            if deploy_job:
                logger.info(f"Processing deploy job for build ID: {deploy_job.get('build_id')}")
                asyncio.create_task(deployer_service.process_deploy_job(deploy_job))
                continue

            # Check mobile app build queue
            app_job = await pop_job("app_build", timeout=1)
            if app_job:
                logger.info(f"Processing mobile app build job: {app_job.get('mobile_build_id')}")
                asyncio.create_task(mobile_build_pipeline.process_mobile_build_job(app_job))
                continue

            await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in worker queue loop: {e}")
            await asyncio.sleep(2)

    logger.info("Closing worker connections...")
    try:
        db = get_database()
        await db.system_status.update_one(
            {"_id": "worker_heartbeat"},
            {"$set": {"status": "offline", "timestamp": utc_now_iso(), "time": 0.0}},
            upsert=True
        )
        redis_client = await get_redis()
        if redis_client:
            await redis_client.delete("ziref:worker:heartbeat")
    except Exception:
        pass
    await close_database_connection()
    await close_redis()
    logger.info("Worker stopped.")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        pass
