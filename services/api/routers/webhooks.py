from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import secrets

from services.api.core.datetime_util import utc_now_iso
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.webhooks import webhook_dispatcher

router = APIRouter(tags=["Webhooks"])

class WebhookCreate(BaseModel):
    url: str
    description: Optional[str] = "Deployment notification webhook"
    events: Optional[List[str]] = ["build.completed", "build.failed", "deployment.ready"]

class WebhookResponse(BaseModel):
    id: str
    project_id: str
    url: str
    description: Optional[str]
    events: List[str]
    secret: str
    is_active: bool
    created_at: str

@router.get("/projects/{project_id}/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.webhooks.find({"project_id": project_id}).sort("created_at", -1)
    webhooks = []
    async for wh in cursor:
        webhooks.append(WebhookResponse(
            id=str(wh["_id"]),
            project_id=wh["project_id"],
            url=wh["url"],
            description=wh.get("description"),
            events=wh.get("events", []),
            secret=wh.get("secret", ""),
            is_active=wh.get("is_active", True),
            created_at=wh.get("created_at", "")
        ))
    return webhooks

@router.post("/projects/{project_id}/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(project_id: str, payload: WebhookCreate, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    now_str = utc_now_iso()
    generated_secret = secrets.token_hex(20)

    doc = {
        "project_id": project_id,
        "user_id": token_data["sub"],
        "url": payload.url.strip(),
        "description": payload.description,
        "events": payload.events or ["build.completed", "build.failed", "deployment.ready"],
        "secret": generated_secret,
        "is_active": True,
        "created_at": now_str
    }

    res = await db.webhooks.insert_one(doc)
    doc["_id"] = res.inserted_id

    return WebhookResponse(
        id=str(doc["_id"]),
        project_id=project_id,
        url=doc["url"],
        description=doc["description"],
        events=doc["events"],
        secret=doc["secret"],
        is_active=doc["is_active"],
        created_at=now_str
    )

@router.delete("/projects/{project_id}/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(project_id: str, webhook_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id) or not ObjectId.is_valid(webhook_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    res = await db.webhooks.delete_one({"_id": ObjectId(webhook_id), "project_id": project_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return None

@router.post("/projects/{project_id}/webhooks/{webhook_id}/test", status_code=status.HTTP_200_OK)
async def test_webhook(project_id: str, webhook_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id) or not ObjectId.is_valid(webhook_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID")

    wh = await db.webhooks.find_one({"_id": ObjectId(webhook_id), "project_id": project_id})
    if not wh:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    await webhook_dispatcher.dispatch_event(
        project_id=project_id,
        event_type="test.ping",
        data={"message": "This is a test notification from Ziref platform."}
    )
    return {"message": "Test ping dispatched"}
