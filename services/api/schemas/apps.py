from pydantic import BaseModel, Field
from typing import Optional, List
from services.api.core.models import MobileAppStatus

class MobileAppCreate(BaseModel):
    app_name: str = Field(..., min_length=2, max_length=50)
    package_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    version: str = "1.0.0"
    version_code: int = 1
    theme: str = "system"  # light, dark, system
    orientation: str = "portrait"  # portrait, landscape, sensor
    permissions: Optional[List[str]] = []
    icon_base64: Optional[str] = None
    website_url: Optional[str] = None  # Optional target URL override (e.g. Wi-Fi LAN IP)

class MobileBuildResponse(BaseModel):
    id: str
    mobile_app_id: str
    project_id: str
    status: MobileAppStatus
    build_target: str = "android"
    apk_artifact_id: Optional[str] = None
    source_artifact_id: Optional[str] = None
    apk_download_url: Optional[str] = None
    source_download_url: Optional[str] = None
    # APK artifact metadata (populated when status=APP_READY)
    apk_filename: Optional[str] = None
    apk_sha256: Optional[str] = None
    apk_size_bytes: Optional[int] = None
    apk_package_name: Optional[str] = None
    apk_version_name: Optional[str] = None
    apk_version_code: Optional[int] = None
    apk_signed: bool = False
    apk_verified: bool = False
    apk_target_url: Optional[str] = None
    apk_url_is_localhost: bool = False
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str

class MobileAppResponse(BaseModel):
    id: str
    project_id: str
    app_name: str
    package_id: str
    version: str
    version_code: int
    theme: str
    orientation: str
    permissions: List[str] = []
    icon_base64: Optional[str] = None
    website_url: str
    website_url_is_localhost: bool = False
    latest_build: Optional[MobileBuildResponse] = None
    updated_at: Optional[str] = None
    created_at: str

class NetworkInfoResponse(BaseModel):
    lan_ip: str
    port: int
    lan_url: str
    localhost_url: str
    active_url: Optional[str] = None
