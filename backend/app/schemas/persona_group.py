import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PersonaGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    age_min: int
    age_max: int
    gender: str
    location: str
    occupation: str
    income_level: str
    psychographic_notes: Optional[str] = None
    persona_count: int = 5


class PersonaGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    income_level: Optional[str] = None
    psychographic_notes: Optional[str] = None
    persona_count: Optional[int] = None


class PersonaGroupResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    description: Optional[str]
    age_min: int
    age_max: int
    gender: str
    location: str
    occupation: str
    income_level: str
    psychographic_notes: Optional[str]
    persona_count: int
    generation_status: str
    generation_progress: Optional[Any] = None
    generation_metadata: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
