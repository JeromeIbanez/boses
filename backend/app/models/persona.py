import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("persona_groups.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation: Mapped[str] = mapped_column(String(255), nullable=False)
    income_level: Mapped[str] = mapped_column(String(100), nullable=False)
    educational_background: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality_traits: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    values_and_motivations: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_consumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    purchase_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)

    day_in_the_life: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), default="synthetic", nullable=False)
    data_source_references: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    raw_profile_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    library_persona_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("library_personas.id"), nullable=True)

    persona_group: Mapped["PersonaGroup"] = relationship(back_populates="personas")
    simulation_results: Mapped[list["SimulationResult"]] = relationship(back_populates="persona", passive_deletes=True)
    library_link: Mapped["PersonaLibraryLink | None"] = relationship(back_populates="persona", uselist=False, passive_deletes=True)
