import json
import asyncio
from typing import List, Dict, Any
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse

from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.redis_client import subscribe_events

router = APIRouter(tags=["Runtime Logs"])

@router.get("/projects/{project_id}/runtime-logs")
async def get_runtime_logs(
    project_id: str,
    limit: int = 100,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.runtime_logs.find({"project_id": project_id}).sort("timestamp", -1).limit(limit)
    logs = []
    async for entry in cursor:
        entry["id"] = str(entry["_id"])
        del entry["_id"]
        logs.append(entry)
    return logs

@router.get("/projects/{project_id}/runtime-logs/stream")
async def stream_runtime_logs(project_id: str):
    async def event_generator():
        # First yield the recent history
        db = get_database()
        cursor = db.runtime_logs.find({"project_id": project_id}).sort("timestamp", -1).limit(20)
        history = []
        async for entry in cursor:
            entry["id"] = str(entry["_id"])
            del entry["_id"]
            history.append(entry)

        for evt in reversed(history):
            yield f"data: {json.dumps(evt)}\n\n"

        # Subscribe to live channel
        try:
            async for live_evt in subscribe_events(f"project:{project_id}:runtime_logs"):
                yield f"data: {json.dumps(live_evt)}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
