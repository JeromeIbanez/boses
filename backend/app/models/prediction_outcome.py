import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # What the simulation predicted (snapshot at commitment time)
    predicted_sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    predicted_themes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # Commitment details
    kpi_description: Mapped[str] = mapped_column(Text, nullable=False)
    outcome_due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Outcome data — filled in when the client reports back
    actual_outcome_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    directional_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # pending = awaiting outcome report; received = outcome logged
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
