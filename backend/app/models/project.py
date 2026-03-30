import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    persona_groups: Mapped[list["PersonaGroup"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    briefings: Mapped[list["Briefing"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    simulations: Mapped[list["Simulation"]] = relationship(back_populates="project", cascade="all, delete-orphan")
