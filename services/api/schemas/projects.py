from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from services.api.core.models import ProjectStatus, AnalysisResult

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    slug: Optional[str] = Field(None, min_length=2, max_length=50)

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    build_command: Optional[str] = None
    output_directory: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: ProjectStatus
    framework: Optional[str] = None
    language: Optional[str] = None
    package_manager: Optional[str] = None
    build_command: Optional[str] = None
    output_directory: Optional[str] = None
    active_deployment_id: Optional[str] = None
    active_url: Optional[str] = None
    created_at: str
    updated_at: str

class UploadResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_size: int
    checksum: str
    analysis: Optional[AnalysisResult] = None
    created_at: str
