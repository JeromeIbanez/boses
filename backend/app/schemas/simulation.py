import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, model_validator


class SimulationCreate(BaseModel):
    simulation_type: str = "concept_test"
    persona_group_id: uuid.UUID
    briefing_ids: list[uuid.UUID] = []
    prompt_question: Optional[str] = None
    idi_script_text: Optional[str] = None
    idi_persona_id: Optional[uuid.UUID] = None
    survey_schema: Optional[dict[str, Any]] = None


class SimulationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    persona_group_id: uuid.UUID
    briefing_ids: list[uuid.UUID] = []
    prompt_question: Optional[str]
    simulation_type: str
    idi_script_text: Optional[str]
    idi_persona_id: Optional[uuid.UUID]
    survey_schema: Optional[dict[str, Any]]
    status: str
    error_message: Optional[str]
    failed_personas: Optional[list[dict[str, Any]]]
    progress: Optional[dict[str, Any]]
    share_token: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_briefing_ids(cls, data: Any) -> Any:
        # When constructing from an ORM object, pull IDs from the relationship
        if hasattr(data, "briefings"):
            data.__dict__.setdefault("briefing_ids", [b.id for b in (data.briefings or [])])
        return data


class SimulationResultResponse(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    persona_id: Optional[uuid.UUID]
    result_type: str
    # Concept test individual
    sentiment: Optional[str]
    sentiment_score: Optional[float]
    reaction_text: Optional[str]
    key_themes: Optional[list[str]]
    notable_quote: Optional[str]
    # Concept test aggregate
    summary_text: Optional[str]
    sentiment_distribution: Optional[dict[str, Any]]
    top_themes: Optional[list[str]]
    recommendations: Optional[str]
    # IDI
    transcript: Optional[str]
    report_sections: Optional[dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConjointAttributeSchema(BaseModel):
    name: str
    levels: list[str]


class ConjointDesignCreate(BaseModel):
    attributes: list[ConjointAttributeSchema]
    n_tasks: int = 10


class IDIMessageCreate(BaseModel):
    content: str


class IDIMessageResponse(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    persona_id: Optional[uuid.UUID]
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
