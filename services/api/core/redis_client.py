import asyncio
import json
import logging
from typing import Optional, AsyncGenerator, Dict, Any, List
import redis.asyncio as aioredis
from services.api.core.config import settings

logger = logging.getLogger("ziref.redis")

_redis_pool: Optional[aioredis.Redis] = None
_use_memory_fallback = False

# Memory fallback structures
_memory_queues: Dict[str, asyncio.Queue] = {}
_memory_subscribers: Dict[str, List[asyncio.Queue]] = {}
_memory_routing_cache: Dict[str, Dict[str, str]] = {}

async def get_redis() -> Optional[aioredis.Redis]:
    global _redis_pool, _use_memory_fallback
    if _use_memory_fallback:
        return None

    if _redis_pool is None:
        try:
            pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await asyncio.wait_for(pool.ping(), timeout=1.0)
            _redis_pool = pool
            _use_memory_fallback = False
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.info(f"Redis daemon not directly available ({e}). Activating embedded database queue and event broker.")
            _use_memory_fallback = True
            _redis_pool = None
    return _redis_pool

async def close_redis():
    global _redis_pool
    if _redis_pool:
        try:
            await _redis_pool.aclose()
        except Exception:
            pass
        _redis_pool = None

async def _execute_job_in_background(queue_name: str, payload: Dict[str, Any]):
    """Executes jobs in background when external worker daemon or Redis is not active (e.g. pytest, standalone)."""
    try:
        from services.api.core.database import get_database
        import time
        db = get_database()
        hb = await db.system_status.find_one({"_id": "worker_heartbeat"})
        if hb and hb.get("source") == "worker_daemon" and (time.time() - hb.get("time", 0)) < 15.0:
            # Dedicated worker daemon is active; let it process the job via queue
            return

        if queue_name == "build":
            from services.builder.build_executor import build_pipeline_executor
            await build_pipeline_executor.process_build_job(payload)
        elif queue_name == "deploy":
            from services.deployer.deployer_service import deployer_service
            await deployer_service.process_deploy_job(payload)
        elif queue_name == "app_build":
            from services.app_builder.apk_builder import mobile_build_pipeline
            await mobile_build_pipeline.process_mobile_build_job(payload)
    except Exception as e:
        logger.error(f"Local job background execution error for {queue_name}: {e}")

async def push_job(queue_name: str, payload: Dict[str, Any]) -> None:
    client = await get_redis()
    if client:
        try:
            await client.rpush(f"ziref:queue:{queue_name}", json.dumps(payload))
            return
        except Exception:
            pass

    # 1. Record in persistent database queue
    try:
        from services.api.core.database import get_database
        from services.api.core.datetime_util import utc_now_iso
        db = get_database()
        await db.job_queue.insert_one({
            "queue": queue_name,
            "payload": payload,
            "status": "pending",
            "created_at": utc_now_iso()
        })
    except Exception as e:
        logger.warning(f"Could not persist job to db.job_queue: {e}")

    # 2. Local memory queue put
    if queue_name not in _memory_queues:
        _memory_queues[queue_name] = asyncio.Queue()
    await _memory_queues[queue_name].put(payload)

    # 3. Trigger fallback in-process execution (auto-yields if worker_daemon is running)
    asyncio.create_task(_execute_job_in_background(queue_name, payload))

async def pop_job(queue_name: str, timeout: int = 2) -> Optional[Dict[str, Any]]:
    client = await get_redis()
    if client:
        try:
            result = await client.blpop(f"ziref:queue:{queue_name}", timeout=timeout)
            if result:
                _, data = result
                return json.loads(data)
            return None
        except Exception:
            pass

    # Check local in-process queue first
    if queue_name in _memory_queues and not _memory_queues[queue_name].empty():
        try:
            return _memory_queues[queue_name].get_nowait()
        except (asyncio.QueueEmpty, Exception):
            pass

    # Check persistent database queue fallback (for cross-process support)
    try:
        from services.api.core.database import get_database
        from services.api.core.datetime_util import utc_now_iso
        db = get_database()
        job = await db.job_queue.find_one_and_update(
            {"queue": queue_name, "status": "pending"},
            {"$set": {"status": "processing", "processed_at": utc_now_iso()}}
        )
        if job and "payload" in job:
            return job["payload"]
    except Exception:
        pass

    # Wait briefly on in-process memory queue if configured
    if queue_name not in _memory_queues:
        _memory_queues[queue_name] = asyncio.Queue()
    try:
        return await asyncio.wait_for(_memory_queues[queue_name].get(), timeout=min(float(timeout), 0.5))
    except (asyncio.TimeoutError, TimeoutError):
        return None

async def publish_event(channel: str, event_data: Dict[str, Any]) -> None:
    client = await get_redis()
    if client:
        try:
            await client.publish(f"ziref:events:{channel}", json.dumps(event_data))
            return
        except Exception:
            pass

    # In-process subscriber queues
    subs = _memory_subscribers.get(channel, [])
    for q in subs:
        await q.put(event_data)

async def subscribe_events(channel: str) -> AsyncGenerator[Dict[str, Any], None]:
    client = await get_redis()
    if client:
        try:
            pubsub = client.pubsub()
            channel_name = f"ziref:events:{channel}"
            await pubsub.subscribe(channel_name)
            try:
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            yield data
                            if data.get("stage") in ["done", "completed"] or "[STREAM_CLOSED]" in data.get("message", ""):
                                break
                        except Exception:
                            yield {"message": message["data"]}
            finally:
                await pubsub.unsubscribe(channel_name)
                await pubsub.aclose()
            return
        except Exception:
            pass

    # Resilient memory fallback with active database status check
    q: asyncio.Queue = asyncio.Queue()
    _memory_subscribers.setdefault(channel, []).append(q)
    seen_event_keys = set()
    try:
        while True:
            try:
                evt = await asyncio.wait_for(q.get(), timeout=1.0)
                evt_key = f"{evt.get('stage')}_{evt.get('message')}"
                seen_event_keys.add(evt_key)
                yield evt
                if evt.get("stage") in ["done", "completed"] or "[STREAM_CLOSED]" in evt.get("message", ""):
                    break
            except (asyncio.TimeoutError, TimeoutError):
                # Inspect database status to detect if job already reached completion
                parts = channel.split(":")
                if len(parts) >= 2:
                    target_type = parts[0]
                    target_id = parts[1]
                    try:
                        from services.api.core.database import get_database
                        from bson import ObjectId
                        db = get_database()
                        if target_type == "build":
                            # Relay events from other processes recorded in DB
                            cursor = db.build_events.find({"build_id": target_id}).sort("timestamp", 1)
                            async for b_evt in cursor:
                                b_key = f"{b_evt.get('stage')}_{b_evt.get('message')}"
                                if b_key not in seen_event_keys:
                                    seen_event_keys.add(b_key)
                                    yield {
                                        "stage": b_evt.get("stage"),
                                        "level": b_evt.get("level"),
                                        "message": b_evt.get("message"),
                                        "timestamp": b_evt.get("timestamp")
                                    }
                            if ObjectId.is_valid(target_id):
                                doc = await db.builds.find_one({"_id": ObjectId(target_id)})
                                if doc and doc.get("status") in ["BUILT", "FAILED", "CANCELLED"]:
                                    yield {"stage": "done", "level": "info", "message": f"[STREAM_CLOSED] Build finished with status: {doc.get('status')}"}
                                    break
                        elif target_type == "mobile" and ObjectId.is_valid(target_id):
                            doc = await db.mobile_builds.find_one({"_id": ObjectId(target_id)})
                            if doc and doc.get("status") in ["APP_READY", "APP_FAILED"]:
                                yield {"stage": "done", "level": "info", "message": "[STREAM_CLOSED]"}
                                break
                    except Exception:
                        pass
    finally:
        if channel in _memory_subscribers and q in _memory_subscribers[channel]:
            _memory_subscribers[channel].remove(q)

async def set_project_routing(slug: str, deployment_id: str, runtime: str = "static") -> None:
    _memory_routing_cache[slug] = {
        "deployment_id": deployment_id,
        "runtime": runtime
    }
    client = await get_redis()
    if client:
        try:
            await client.hset(f"ziref:routing:{slug}", mapping={
                "deployment_id": deployment_id,
                "runtime": runtime
            })
        except Exception:
            pass

async def get_project_routing(slug: str) -> Optional[Dict[str, str]]:
    client = await get_redis()
    if client:
        try:
            data = await client.hgetall(f"ziref:routing:{slug}")
            if data:
                return data
        except Exception:
            pass
    return _memory_routing_cache.get(slug)
