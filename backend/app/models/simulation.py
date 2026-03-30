import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    persona_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("persona_groups.id"), nullable=False)
    briefing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("briefings.id"), nullable=False)
    prompt_question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="simulations")
    persona_group: Mapped["PersonaGroup"] = relationship()
    briefing: Mapped["Briefing"] = relationship(back_populates="simulations")
    results: Mapped[list["SimulationResult"]] = relationship(back_populates="simulation", cascade="all, delete-orphan")
