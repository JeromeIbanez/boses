"""
CulturalContextSnapshot model

Stores the output of the automated web ethnography pipeline.
One active snapshot per market_code at a time. When a new snapshot is
activated, the previous is archived. If no active snapshot exists for a
market, persona generation falls back to its existing behaviour (safe default).

Status lifecycle:
    draft    → extraction completed but quality gate not met (<0.5 score)
    active   → quality gate passed; injected into persona generation
    archived → superseded by a newer active snapshot
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class CulturalContextSnapshot(Base):
    __tablename__ = "cultural_context_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # "ID", "PH", "VN" — ISO 3166-1 alpha-2 country code for the SEA markets we support
    market_code = Column(String(5), nullable=False, index=True)

    # draft | active | archived
    status = Column(String(20), nullable=False, default="draft")

    # Auto-increments per market on each successful activation
    version = Column(Integer, nullable=False, default=1)

    # Structured behavioral signals extracted by the LLM.
    # Schema: {
    #   "market": "PH",
    #   "top_spending_categories": [...],
    #   "trusted_brands": [...],
    #   "distrusted_brands": [...],
    #   "dominant_anxieties": [...],
    #   "aspirations": [...],
    #   "cultural_behaviors": [...],
    #   "digital_habits": [...],
    #   "price_sensitivity_signals": [...],
    #   "source_summary": "Synthesized from N posts across ..."
    # }
    signals_json = Column(JSONB, nullable=True)

    # List of {source: str, post_count: int} for each source crawled.
    # Used to verify that crawl actually returned data (Step 1 of verification).
    raw_sources = Column(JSONB, nullable=True)

    # Quality score 0.0–1.0 computed from signal completeness.
    # Snapshots with score < 0.5 stay as "draft" and are never injected.
    quality_score = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Set when status transitions to "active"
    activated_at = Column(DateTime, nullable=True)
