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

async def worker_loop():
    logger.info(f"Ziref Worker started in environment: {settings.APP_ENV}")
    await connect_to_database()

    while running:
        try:
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
