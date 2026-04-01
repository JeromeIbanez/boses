import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.id"), nullable=False)
    persona_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    result_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "individual" | "aggregate"

    # Individual result fields
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reaction_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_themes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    notable_quote: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Aggregate result fields
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_distribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    top_themes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # IDI result fields
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_sections: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    simulation: Mapped["Simulation"] = relationship(back_populates="results")
    persona: Mapped["Persona | None"] = relationship(back_populates="simulation_results")
