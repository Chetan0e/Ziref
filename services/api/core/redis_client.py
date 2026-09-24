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
            await asyncio.wait_for(pool.ping(), timeout=1.5)
            _redis_pool = pool
            _use_memory_fallback = False
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.info(f"Redis not available ({e}). Activating embedded async memory queue and event broker.")
            _use_memory_fallback = True
            _redis_pool = None
    return _redis_pool

async def close_redis():
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None

async def push_job(queue_name: str, payload: Dict[str, Any]) -> None:
    client = await get_redis()
    if client:
        try:
            await client.rpush(f"ziref:queue:{queue_name}", json.dumps(payload))
            return
        except Exception:
            pass

    # Memory fallback
    if queue_name not in _memory_queues:
        _memory_queues[queue_name] = asyncio.Queue()
    await _memory_queues[queue_name].put(payload)

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

    # Memory fallback
    if queue_name not in _memory_queues:
        _memory_queues[queue_name] = asyncio.Queue()
    try:
        return await asyncio.wait_for(_memory_queues[queue_name].get(), timeout=float(timeout))
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

    # Memory fallback
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
                            yield json.loads(message["data"])
                        except Exception:
                            yield {"message": message["data"]}
            finally:
                await pubsub.unsubscribe(channel_name)
                await pubsub.aclose()
            return
        except Exception:
            pass

    # Memory fallback
    q: asyncio.Queue = asyncio.Queue()
    _memory_subscribers.setdefault(channel, []).append(q)
    try:
        while True:
            evt = await q.get()
            yield evt
            if evt.get("stage") in ["done", "completed"] or "[STREAM_CLOSED]" in evt.get("message", ""):
                break
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
