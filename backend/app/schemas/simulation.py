import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel


class SimulationCreate(BaseModel):
    persona_group_id: uuid.UUID
    briefing_id: uuid.UUID
    prompt_question: str


class SimulationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    persona_group_id: uuid.UUID
    briefing_id: uuid.UUID
    prompt_question: str
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SimulationResultResponse(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    persona_id: Optional[uuid.UUID]
    result_type: str
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    reaction_text: Optional[str]
    key_themes: Optional[list[str]]
    notable_quote: Optional[str]
    summary_text: Optional[str]
    sentiment_distribution: Optional[dict[str, Any]]
    top_themes: Optional[list[str]]
    recommendations: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
