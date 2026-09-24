from pydantic import BaseModel, Field
from typing import Optional

class EnvVarCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern=r"^[A-Z0-9_]+$")
    value: str
    is_secret: bool = True

class EnvVarResponse(BaseModel):
    id: str
    key: str
    value: str  # Masked if is_secret
    is_secret: bool
    created_at: str
    updated_at: str
