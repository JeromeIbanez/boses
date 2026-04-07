import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class BriefingResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: Optional[str]
    file_name: str
    file_type: str
    extracted_text: Optional[str]
    summary_text: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
