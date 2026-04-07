import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    persona_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("persona_groups.id", ondelete="CASCADE"), nullable=False)
    prompt_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    simulation_type: Mapped[str] = mapped_column(String(50), default="concept_test", nullable=False)
    idi_script_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    idi_persona_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    survey_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="simulations")
    persona_group: Mapped["PersonaGroup"] = relationship()
    briefings: Mapped[list["Briefing"]] = relationship(
        "Briefing", secondary="simulation_briefings", back_populates="simulations"
    )
    idi_persona: Mapped["Persona | None"] = relationship(foreign_keys="[Simulation.idi_persona_id]", passive_deletes=True)
    results: Mapped[list["SimulationResult"]] = relationship(back_populates="simulation", cascade="all, delete-orphan")
    idi_messages: Mapped[list["IDIMessage"]] = relationship(back_populates="simulation", cascade="all, delete-orphan")
