import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class PersonaGroup(Base):
    __tablename__ = "persona_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    age_min: Mapped[int] = mapped_column(Integer, nullable=False)
    age_max: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation: Mapped[str] = mapped_column(String(255), nullable=False)
    income_level: Mapped[str] = mapped_column(String(100), nullable=False)
    psychographic_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    persona_count: Mapped[int] = mapped_column(Integer, default=5)
    generation_status: Mapped[str] = mapped_column(String(50), default="pending")
    generation_progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="persona_groups")
    personas: Mapped[list["Persona"]] = relationship(back_populates="persona_group", cascade="all, delete-orphan")
