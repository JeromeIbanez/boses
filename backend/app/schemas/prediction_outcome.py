import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PredictionOutcomeCreate(BaseModel):
    kpi_description: str
    outcome_due_date: datetime
    predicted_sentiment: Optional[str] = None
    predicted_themes: Optional[list[str]] = None


class PredictionOutcomeUpdate(BaseModel):
    actual_outcome_description: Optional[str] = None
    directional_match: Optional[bool] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class PredictionOutcomeResponse(BaseModel):
    id: uuid.UUID
    simulation_id: uuid.UUID
    project_id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID]
    predicted_sentiment: Optional[str]
    predicted_themes: Optional[list[str]]
    kpi_description: str
    outcome_due_date: datetime
    actual_outcome_description: Optional[str]
    directional_match: Optional[bool]
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
