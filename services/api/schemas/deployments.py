from pydantic import BaseModel
from typing import Optional
from services.api.core.models import DeploymentStatus

class DeploymentResponse(BaseModel):
    id: str
    project_id: str
    build_id: str
    status: DeploymentStatus
    url: str
    subdomain: str
    runtime: str
    created_at: str
    completed_at: Optional[str] = None

class RollbackRequest(BaseModel):
    deployment_id: str
