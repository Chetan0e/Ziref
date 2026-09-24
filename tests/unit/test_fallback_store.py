import pytest
from services.api.core.database import MemoryDatabase
from services.api.core.redis_client import push_job, pop_job, publish_event, subscribe_events, set_project_routing, get_project_routing
import asyncio

@pytest.mark.asyncio
async def test_memory_database_crud():
    db = MemoryDatabase()
    # Insert
    res = await db.test_collection.insert_one({"name": "Ziref", "type": "platform"})
    doc_id = res.inserted_id
    assert doc_id is not None

    # Find one
    doc = await db.test_collection.find_one({"name": "Ziref"})
    assert doc is not None
    assert doc["type"] == "platform"

    # Update
    up_res = await db.test_collection.update_one({"name": "Ziref"}, {"$set": {"status": "active"}})
    assert up_res.modified_count == 1
    updated = await db.test_collection.find_one({"name": "Ziref"})
    assert updated["status"] == "active"

    # Delete
    del_res = await db.test_collection.delete_one({"name": "Ziref"})
    assert del_res.deleted_count == 1
    assert await db.test_collection.find_one({"name": "Ziref"}) is None

@pytest.mark.asyncio
async def test_memory_queue_push_pop():
    payload = {"task": "build", "id": 101}
    await push_job("test_queue", payload)

    popped = await pop_job("test_queue", timeout=1)
    assert popped is not None
    assert popped["task"] == "build"
    assert popped["id"] == 101

@pytest.mark.asyncio
async def test_memory_routing_cache():
    await set_project_routing("my-slug", "dep_456", "static")
    routing = await get_project_routing("my-slug")
    assert routing is not None
    assert routing["deployment_id"] == "dep_456"
    assert routing["runtime"] == "static"
