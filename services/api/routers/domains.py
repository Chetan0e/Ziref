from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token

router = APIRouter(tags=["Custom Domains"])

class DomainCreate(BaseModel):
    domain: str = Field(..., pattern=r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$")

class DomainResponse(BaseModel):
    id: str
    project_id: str
    domain: str
    status: str  # PENDING_DNS, VERIFIED, SSL_ACTIVE
    cname_target: str
    created_at: str
    verified_at: str = None

@router.get("/projects/{project_id}/domains", response_model=List[DomainResponse])
async def list_project_domains(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.domains.find({"project_id": project_id})
    res = []
    async for d in cursor:
        res.append(DomainResponse(
            id=str(d["_id"]),
            project_id=d["project_id"],
            domain=d["domain"],
            status=d.get("status", "PENDING_DNS"),
            cname_target=f"cname.{settings.BASE_DOMAIN.split(':')[0]}",
            created_at=d.get("created_at", ""),
            verified_at=d.get("verified_at")
        ))
    return res

@router.post("/projects/{project_id}/domains", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
async def add_project_domain(
    project_id: str,
    payload: DomainCreate,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    domain = payload.domain.lower().strip()
    existing = await db.domains.find_one({"domain": domain})
    if existing:
        if existing.get("project_id") == project_id:
            return DomainResponse(
                id=str(existing["_id"]),
                project_id=existing["project_id"],
                domain=existing["domain"],
                status=existing.get("status", "PENDING_DNS"),
                cname_target=f"cname.{settings.BASE_DOMAIN.split(':')[0]}",
                created_at=existing.get("created_at", ""),
                verified_at=existing.get("verified_at")
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Domain already configured on another Ziref project.")

    now_str = datetime.now(timezone.utc).isoformat() + "Z"
    doc = {
        "project_id": project_id,
        "user_id": token_data["sub"],
        "domain": domain,
        "status": "PENDING_DNS",
        "created_at": now_str,
        "verified_at": None
    }

    res = await db.domains.insert_one(doc)
    doc["_id"] = res.inserted_id

    return DomainResponse(
        id=str(doc["_id"]),
        project_id=doc["project_id"],
        domain=doc["domain"],
        status=doc["status"],
        cname_target=f"cname.{settings.BASE_DOMAIN.split(':')[0]}",
        created_at=doc["created_at"]
    )

@router.post("/projects/{project_id}/domains/{domain_id}/verify", response_model=DomainResponse)
async def verify_domain(
    project_id: str,
    domain_id: str,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    domain = await db.domains.find_one({"_id": ObjectId(domain_id), "project_id": project_id, "user_id": token_data["sub"]})
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")

    now_str = datetime.now(timezone.utc).isoformat() + "Z"
    await db.domains.update_one(
        {"_id": ObjectId(domain_id)},
        {"$set": {
            "status": "VERIFIED",
            "verified_at": now_str
        }}
    )

    domain["status"] = "VERIFIED"
    domain["verified_at"] = now_str

    return DomainResponse(
        id=str(domain["_id"]),
        project_id=domain["project_id"],
        domain=domain["domain"],
        status="VERIFIED",
        cname_target=f"cname.{settings.BASE_DOMAIN.split(':')[0]}",
        created_at=domain.get("created_at", ""),
        verified_at=now_str
    )

@router.delete("/projects/{project_id}/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain(project_id: str, domain_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    res = await db.domains.delete_one({"_id": ObjectId(domain_id), "project_id": project_id, "user_id": token_data["sub"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    return None
