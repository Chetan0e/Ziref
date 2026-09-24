from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from services.api.core.models import BuildStatus, BuildLogEvent

class BuildTriggerRequest(BaseModel):
    upload_id: str
    build_command: Optional[str] = None
    output_directory: Optional[str] = None

class BuildResponse(BaseModel):
    id: str
    project_id: str
    upload_id: str
    status: BuildStatus
    framework: Optional[str] = None
    build_command: Optional[str] = None
    output_directory: Optional[str] = None
    exit_code: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    diagnosis: Optional[Dict[str, Any]] = None
    created_at: str

class BuildLogsResponse(BaseModel):
    build_id: str
    events: List[BuildLogEvent]

class BuildDiagnosisResponse(BaseModel):
    build_id: str
    category: str
    summary: str
    root_cause: str
    confidence: float
    actionable_fix: str
    detected_snippet: Optional[str] = None
