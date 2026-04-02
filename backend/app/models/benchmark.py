import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.database import Base


class BenchmarkCase(Base):
    """Platform-managed historical cases with known ground truth outcomes."""
    __tablename__ = "benchmark_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # product_launch | ad_campaign | brand_perception
    description: Mapped[str] = mapped_column(Text, nullable=False)
    briefing_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_question: Mapped[str] = mapped_column(Text, nullable=False)
    simulation_type: Mapped[str] = mapped_column(String(50), default="concept_test", nullable=False)
    # ground_truth: {"sentiment": "Negative", "positive_pct": 20, "neutral_pct": 15, "negative_pct": 65, "top_themes": [...], "outcome_summary": "...", "source_notes": "..."}
    ground_truth: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_citations: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    runs: Mapped[list["BenchmarkRun"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class BenchmarkRun(Base):
    """A user's simulation run against a benchmark case, with accuracy scores."""
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("benchmark_cases.id", ondelete="CASCADE"), nullable=False)
    simulation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Computed accuracy scores (0.0–1.0)
    sentiment_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    distribution_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    theme_overlap_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_accuracy_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    case: Mapped["BenchmarkCase"] = relationship(back_populates="runs")
