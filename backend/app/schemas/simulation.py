import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, model_validator


class SimulationCreate(BaseModel):
    simulation_type: str = "concept_test"
    # New canonical field — list of one or more persona group IDs
    persona_group_ids: list[uuid.UUID] = []
    # Legacy field — old clients send this; reconciled by the validator below
    persona_group_id: Optional[uuid.UUID] = None
    briefing_ids: list[uuid.UUID] = []
    prompt_question: Optional[str] = None
    idi_script_text: Optional[str] = None
    idi_persona_id: Optional[uuid.UUID] = None
    survey_schema: Optional[dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def reconcile_persona_group_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            pg_id = data.get("persona_group_id")
            pg_ids = data.get("persona_group_ids") or []
            if pg_id and not pg_ids:
                data["persona_group_ids"] = [pg_id]
        return data

    @model_validator(mode="after")
    def validate_has_groups(self) -> "SimulationCreate":
        if not self.persona_group_ids:
            raise ValueError("At least one persona_group_id must be specified")
        return self


class SimulationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    persona_group_id: Optional[uuid.UUID]
    persona_group_ids: list[uuid.UUID] = []
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
    def extract_group_and_briefing_ids(cls, data: Any) -> Any:
        if hasattr(data, "persona_groups"):
            ids = [g.id for g in (data.persona_groups or [])]
            data.__dict__.setdefault("persona_group_ids", ids)
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
