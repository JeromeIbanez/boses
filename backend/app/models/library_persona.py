import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, DateTime, Float, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class LibraryPersona(Base):
    __tablename__ = "library_personas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation: Mapped[str] = mapped_column(String(255), nullable=False)
    income_level: Mapped[str] = mapped_column(String(100), nullable=False)

    educational_background: Mapped[str | None] = mapped_column(Text, nullable=True)
    family_situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality_traits: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    pain_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_savviness: Mapped[str | None] = mapped_column(String(100), nullable=True)
    media_consumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    spending_habits: Mapped[str | None] = mapped_column(Text, nullable=True)
    archetype_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    psychographic_segment: Mapped[str | None] = mapped_column(String(100), nullable=True)
    brand_attitudes: Mapped[str | None] = mapped_column(Text, nullable=True)
    buying_triggers: Mapped[str | None] = mapped_column(Text, nullable=True)
    aspirational_identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    digital_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    day_in_the_life: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_source: Mapped[str] = mapped_column(String(50), nullable=False, default="synthetic")
    data_source_references: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    simulation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_retired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    links: Mapped[list["PersonaLibraryLink"]] = relationship(back_populates="library_persona")


class PersonaLibraryLink(Base):
    __tablename__ = "persona_library_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, unique=True)
    library_persona_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("library_personas.id"), nullable=False)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # None = freshly generated
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    persona: Mapped["Persona"] = relationship(back_populates="library_link")
    library_persona: Mapped["LibraryPersona"] = relationship(back_populates="links")
