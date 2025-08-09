"""
Request models - Pydantic modellen voor API request validatie

Dit bestand definieert alle inkomende request data structuren voor de API.
Deze modellen zorgen voor:
- Automatische validatie van input data
- Type checking en conversie
- Swagger/OpenAPI documentatie generatie
- Duidelijke error messages bij ongeldige input

Elk model representeert een specifiek request type dat de API accepteert.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JobCreateRequest(BaseModel):
    video_path: str = Field(..., description="Path to video file")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    priority: int = Field(default=5, ge=1, le=10, description="Job priority")

class JobUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="Job status")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Job progress")
    error_message: Optional[str] = Field(None, description="Error message")

class UserCreateRequest(BaseModel):
    email: str = Field(..., description="User email address")
    name: str = Field(..., description="User name")
    password: str = Field(..., min_length=8, description="User password")

class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="User name")
    credits: Optional[int] = Field(None, ge=0, description="User credits")
    subscription_tier: Optional[str] = Field(None, description="Subscription tier")
