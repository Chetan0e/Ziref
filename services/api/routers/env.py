from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any

from services.api.core.datetime_util import utc_now_iso
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token, encrypt_secret, decrypt_secret
from services.api.schemas.env import EnvVarCreate, EnvVarResponse

router = APIRouter(tags=["Environment Variables"])

@router.get("/projects/{project_id}/env", response_model=List[EnvVarResponse])
async def list_env_vars(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.environment_variables.find({"project_id": project_id})
    res = []
    async for ev in cursor:
        val = "••••••••" if ev.get("is_secret", True) else decrypt_secret(ev["encrypted_value"])
        res.append(EnvVarResponse(
            id=str(ev["_id"]),
            key=ev["key"],
            value=val,
            is_secret=ev.get("is_secret", True),
            created_at=ev.get("created_at", ""),
            updated_at=ev.get("updated_at", "")
        ))
    return res

@router.post("/projects/{project_id}/env", response_model=EnvVarResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_env_var(
    project_id: str,
    payload: EnvVarCreate,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    now_str = utc_now_iso()
    encrypted = encrypt_secret(payload.value)

    res = await db.environment_variables.find_one_and_update(
        {"project_id": project_id, "key": payload.key.upper()},
        {"$set": {
            "encrypted_value": encrypted,
            "is_secret": payload.is_secret,
            "updated_at": now_str
        }, "$setOnInsert": {
            "project_id": project_id,
            "created_at": now_str
        }},
        upsert=True,
        return_document=True
    )

    return EnvVarResponse(
        id=str(res["_id"]),
        key=res["key"],
        value="••••••••" if payload.is_secret else payload.value,
        is_secret=payload.is_secret,
        created_at=res.get("created_at", now_str),
        updated_at=now_str
    )

@router.delete("/projects/{project_id}/env/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_env_var(project_id: str, key: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    res = await db.environment_variables.delete_one({"project_id": project_id, "key": key.upper()})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Environment variable not found")
    return None
