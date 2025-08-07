"""
Response models - Pydantic modellen voor API response structuren

Dit bestand definieert alle uitgaande response data structuren voor de API.
Deze modellen zorgen voor:
- Consistente response formats voor alle endpoints
- Automatische JSON serialisatie
- Type safety voor response data
- Swagger/OpenAPI response documentatie
- Data transformatie van database modellen naar API responses

Elk model representeert een specifiek response type dat de API teruggeeft.
Helper methoden zoals 'from_job' converteren database objecten naar API responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class JobResponse(BaseModel):
    id: str = Field(..., description="Job ID")
    user_id: str = Field(..., description="User ID")
    status: str = Field(..., description="Job status")
    progress: int = Field(..., description="Job progress")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    
    @classmethod
    def from_job(cls, job):
        """Create response from job model"""
        return cls(
            id=job.id,
            user_id=job.user_id,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            updated_at=job.updated_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            metadata=job.metadata or {}
        )

class UserResponse(BaseModel):
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User name")
    credits: int = Field(..., description="User credits")
    subscription_tier: str = Field(..., description="Subscription tier")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    @classmethod
    def from_user(cls, user):
        """Create response from user model"""
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            credits=user.credits,
            subscription_tier=user.subscription_tier,
            created_at=user.created_at
        )
