import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LibraryPersonaResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    age: int
    gender: str
    location: str
    occupation: str
    income_level: str
    educational_background: Optional[str]
    family_situation: Optional[str]
    background: Optional[str]
    personality_traits: Optional[list[str]]
    goals: Optional[str]
    pain_points: Optional[str]
    tech_savviness: Optional[str]
    media_consumption: Optional[str]
    spending_habits: Optional[str]
    archetype_label: Optional[str]
    psychographic_segment: Optional[str]
    brand_attitudes: Optional[str]
    buying_triggers: Optional[str]
    aspirational_identity: Optional[str]
    digital_behavior: Optional[str]
    day_in_the_life: Optional[str]
    avatar_url: Optional[str]
    data_source: str
    data_source_references: Optional[list[str]]
    is_boses_curated: bool
    simulation_count: int
    is_retired: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LibraryPersonaListResponse(BaseModel):
    items: list[LibraryPersonaResponse]
    total: int
    limit: int
    offset: int


class LibraryPersonaProjectEntry(BaseModel):
    project_id: uuid.UUID
    project_name: str
    group_id: uuid.UUID
    group_name: str
    linked_at: datetime

    model_config = {"from_attributes": True}
