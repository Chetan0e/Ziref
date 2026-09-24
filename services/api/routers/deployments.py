from fastapi import APIRouter, HTTPException, status, Depends
from bson import ObjectId
from typing import List, Dict, Any

from services.api.core.config import settings
from services.api.core.database import get_database
from services.api.core.security import get_current_user_token
from services.api.core.models import DeploymentStatus
from services.api.core.redis_client import push_job
from services.api.schemas.deployments import DeploymentResponse, RollbackRequest
from services.deployer.deployer_service import deployer_service

router = APIRouter(tags=["Deployments"])

@router.get("/projects/{project_id}/deployments", response_model=List[DeploymentResponse])
async def list_project_deployments(project_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(project_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project ID")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    cursor = db.deployments.find({"project_id": project_id}).sort("created_at", -1)
    deployments = []
    async for d in cursor:
        deployments.append(DeploymentResponse(
            id=str(d["_id"]),
            project_id=d["project_id"],
            build_id=d["build_id"],
            status=d.get("status", DeploymentStatus.QUEUED.value),
            url=d.get("url", ""),
            subdomain=d.get("subdomain", ""),
            runtime=d.get("runtime", "static"),
            created_at=d.get("created_at", ""),
            completed_at=d.get("completed_at")
        ))
    return deployments

@router.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: str, token_data: Dict[str, Any] = Depends(get_current_user_token)):
    db = get_database()
    if not ObjectId.is_valid(deployment_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid deployment ID")

    d = await db.deployments.find_one({"_id": ObjectId(deployment_id), "user_id": token_data["sub"]})
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deployment not found")

    return DeploymentResponse(
        id=str(d["_id"]),
        project_id=d["project_id"],
        build_id=d["build_id"],
        status=d.get("status", DeploymentStatus.QUEUED.value),
        url=d.get("url", ""),
        subdomain=d.get("subdomain", ""),
        runtime=d.get("runtime", "static"),
        created_at=d.get("created_at", ""),
        completed_at=d.get("completed_at")
    )

@router.post("/projects/{project_id}/rollback", response_model=DeploymentResponse)
async def rollback_deployment(
    project_id: str,
    payload: RollbackRequest,
    token_data: Dict[str, Any] = Depends(get_current_user_token)
):
    db = get_database()
    if not ObjectId.is_valid(project_id) or not ObjectId.is_valid(payload.deployment_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    project = await db.projects.find_one({"_id": ObjectId(project_id), "user_id": token_data["sub"]})
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    success = await deployer_service.rollback(project_id, payload.deployment_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rollback to specified deployment. Ensure it is marked READY."
        )

    d = await db.deployments.find_one({"_id": ObjectId(payload.deployment_id)})
    return DeploymentResponse(
        id=str(d["_id"]),
        project_id=d["project_id"],
        build_id=d["build_id"],
        status=d.get("status", DeploymentStatus.READY.value),
        url=d.get("url", ""),
        subdomain=d.get("subdomain", ""),
        runtime=d.get("runtime", "static"),
        created_at=d.get("created_at", ""),
        completed_at=d.get("completed_at")
    )
