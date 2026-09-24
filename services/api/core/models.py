from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ProjectStatus(str, Enum):
    CREATED = "CREATED"
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    ANALYZING = "ANALYZING"
    ANALYZED = "ANALYZED"
    BUILD_QUEUED = "BUILD_QUEUED"
    BUILDING = "BUILDING"
    BUILD_FAILED = "BUILD_FAILED"
    BUILT = "BUILT"
    DEPLOY_QUEUED = "DEPLOY_QUEUED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    DEPLOY_FAILED = "DEPLOY_FAILED"
    ARCHIVED = "ARCHIVED"

class BuildStatus(str, Enum):
    QUEUED = "QUEUED"
    PREPARING = "PREPARING"
    BUILDING = "BUILDING"
    BUILT = "BUILT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class DeploymentStatus(str, Enum):
    QUEUED = "QUEUED"
    DEPLOYING = "DEPLOYING"
    READY = "READY"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class MobileAppStatus(str, Enum):
    APP_CREATED = "APP_CREATED"
    APP_QUEUED = "APP_QUEUED"
    APP_CONFIGURING = "APP_CONFIGURING"
    APP_BUILDING = "APP_BUILDING"
    APP_READY = "APP_READY"
    APP_FAILED = "APP_FAILED"

class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class BuildStage(str, Enum):
    INIT = "init"
    VALIDATION = "validation"
    ANALYSIS = "analysis"
    SANDBOX_INIT = "sandbox_init"
    DEPENDENCIES = "dependencies"
    BUILD = "build"
    PACKAGING = "packaging"
    ARTIFACT_STORAGE = "artifact_storage"
    DEPLOYMENT = "deployment"
    CLEANUP = "cleanup"

class BuildLogEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    stage: str
    level: LogLevel = LogLevel.INFO
    message: str

class AnalysisResult(BaseModel):
    projectType: str = "web"
    framework: str
    frameworkVersion: Optional[str] = None
    language: str
    packageManager: str
    runtime: str = "static"
    buildCommand: Optional[str] = None
    startCommand: Optional[str] = None
    outputDirectory: str = "dist"
    port: Optional[int] = None
    confidence: float = 1.0
    warnings: List[str] = []
