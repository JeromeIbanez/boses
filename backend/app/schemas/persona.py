import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PersonaResponse(BaseModel):
    id: uuid.UUID
    persona_group_id: uuid.UUID
    full_name: str
    age: int
    gender: str
    location: str
    occupation: str
    income_level: str
    educational_background: Optional[str]
    family_situation: Optional[str]
    personality_traits: Optional[list[str]]
    values_and_motivations: Optional[str]
    pain_points: Optional[str]
    media_consumption: Optional[str]
    purchase_behavior: Optional[str]
    day_in_the_life: Optional[str]
    persona_code: str
    data_source: Optional[str]
    data_source_references: Optional[list[str]]
    library_persona_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}
