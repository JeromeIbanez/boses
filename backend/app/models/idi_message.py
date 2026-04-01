import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class IDIMessage(Base):
    __tablename__ = "idi_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    persona_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "persona"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    simulation: Mapped["Simulation"] = relationship(back_populates="idi_messages")
    persona: Mapped["Persona | None"] = relationship()
