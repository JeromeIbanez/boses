"""
Benchmarking service — three trust layers:
  Phase 1: Cross-simulation convergence (no new tables)
  Phase 2: Reproducibility / confidence scoring
  Phase 3: External benchmark case scoring
"""
import logging
import math
import itertools
from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopwords for theme word extraction
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "a", "an", "the", "of", "in", "is", "it", "to", "for", "and", "or",
    "its", "this", "that", "are", "was", "were", "be", "been", "being",
    "with", "as", "at", "by", "from", "on", "but", "not", "we", "our",
    "their", "they", "have", "has", "had", "will", "would", "could", "about",
}

# Maps simulation_type → expected aggregate result_type
_AGGREGATE_RESULT_TYPES = {
    "concept_test": "aggregate",
    "focus_group": "focus_group_aggregate",
    "idi_ai": "idi_aggregate",
    "idi_manual": "idi_aggregate",
    "survey": "survey_aggregate",
    "conjoint": "conjoint_aggregate",
}

# ---------------------------------------------------------------------------
# Math primitives
# ---------------------------------------------------------------------------


def _normalize_dist(dist: dict) -> list[float]:
    """Convert sentiment distribution dict to [pos, neu, neg] probability list."""
    pos = float(dist.get("Positive") or 0)
    neu = float(dist.get("Neutral") or 0)
    neg = float(dist.get("Negative") or 0)
    total = pos + neu + neg
    if total == 0:
        return [1 / 3, 1 / 3, 1 / 3]
    return [pos / total, neu / total, neg / total]


def _jsd(p: dict, q: dict) -> float:
    """Jensen-Shannon divergence between two sentiment distribution dicts. Result in [0, 1]."""
    pv = _normalize_dist(p)
    qv = _normalize_dist(q)
    m = [(pv[i] + qv[i]) / 2 for i in range(3)]

    def kl(a: list[float], b: list[float]) -> float:
        return sum(ai * math.log(ai / bi) for ai, bi in zip(a, b) if ai > 0 and bi > 0)

    return (kl(pv, m) + kl(qv, m)) / 2


def _theme_words(themes: list[str] | None) -> set[str]:
    if not themes:
        return set()
    raw = " ".join(t.lower() for t in themes).split()
    return {w for w in raw if w not in _STOPWORDS and len(w) > 2}


def _theme_jaccard(themes_a: list[str] | None, themes_b: list[str] | None) -> float:
    """Word-level Jaccard overlap between two theme lists, ignoring stopwords."""
    wa = _theme_words(themes_a)
    wb = _theme_words(themes_b)
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _dominant_sentiment(dist: dict | None) -> str | None:
    if not dist:
        return None
    return max(dist, key=lambda k: dist.get(k) or 0)


# ---------------------------------------------------------------------------
# Phase 1: Cross-simulation convergence
# ---------------------------------------------------------------------------


def compute_convergence(
    project_id: str,
    briefing_id: str | None,
    persona_group_id: str,
    db: Session,
) -> dict:
    """
    Compute cross-simulation convergence for all completed simulations sharing the
    same briefing + persona group within a project. Returns pairwise convergence
    scores and an overall score.
    """
    from app.models.simulation import Simulation
    from app.models.simulation_result import SimulationResult

    query = select(Simulation).where(
        Simulation.project_id == project_id,
        Simulation.persona_group_id == persona_group_id,
        Simulation.status == "complete",
    )
    if briefing_id:
        from app.models.simulation_briefing import SimulationBriefing
        query = query.join(
            SimulationBriefing,
            SimulationBriefing.simulation_id == Simulation.id,
        ).where(SimulationBriefing.briefing_id == briefing_id)

    sims = db.execute(query).scalars().all()

    if len(sims) < 2:
        return {
            "simulations_analysed": [],
            "pairwise_convergence": [],
            "overall_convergence_score": None,
            "interpretation": None,
            "message": "At least 2 completed simulations on the same persona group are needed.",
        }

    # Fetch aggregate result for each simulation
    sim_data = []
    for sim in sims:
        agg_type = _AGGREGATE_RESULT_TYPES.get(sim.simulation_type, "aggregate")
        agg = db.execute(
            select(SimulationResult).where(
                SimulationResult.simulation_id == sim.id,
                SimulationResult.result_type == agg_type,
            )
        ).scalar_one_or_none()
        if not agg:
            continue

        # top_themes may live in report_sections for IDI/survey
        top_themes = agg.top_themes
        if not top_themes and agg.report_sections:
            rs = agg.report_sections
            top_themes = (
                rs.get("cross_persona_themes")
                or rs.get("themes")
                or rs.get("top_themes")
                or None
            )

        sim_data.append({
            "simulation_id": str(sim.id),
            "simulation_type": sim.simulation_type,
            "completed_at": sim.completed_at.isoformat() if sim.completed_at else None,
            "sentiment_distribution": agg.sentiment_distribution,
            "top_themes": top_themes,
        })

    if len(sim_data) < 2:
        return {
            "simulations_analysed": [],
            "pairwise_convergence": [],
            "overall_convergence_score": None,
            "interpretation": None,
            "message": "Not enough simulations with aggregate results found.",
        }

    pairs = [_pairwise_convergence(a, b) for a, b in itertools.combinations(sim_data, 2)]
    overall = sum(p["convergence_score"] for p in pairs) / len(pairs)

    if overall >= 0.75:
        interpretation = "strong"
    elif overall >= 0.5:
        interpretation = "moderate"
    else:
        interpretation = "weak"

    return {
        "simulations_analysed": [
            {
                "simulation_id": d["simulation_id"],
                "simulation_type": d["simulation_type"],
                "completed_at": d["completed_at"],
            }
            for d in sim_data
        ],
        "pairwise_convergence": pairs,
        "overall_convergence_score": round(overall, 3),
        "interpretation": interpretation,
    }


def _pairwise_convergence(a: dict, b: dict) -> dict:
    dist_a = a.get("sentiment_distribution")
    dist_b = b.get("sentiment_distribution")
    has_dist = bool(dist_a and dist_b)

    if has_dist:
        dom_a = _dominant_sentiment(dist_a)
        dom_b = _dominant_sentiment(dist_b)
        direction_match = dom_a == dom_b
        direction_score = 1.0 if direction_match else 0.0
        dist_score = round(1.0 - _jsd(dist_a, dist_b), 3)
        convergence_score = round(0.50 * direction_score + 0.30 * dist_score + 0.20 * _theme_jaccard(a.get("top_themes"), b.get("top_themes")), 3)
    else:
        direction_match = None
        direction_score = None
        dist_score = None
        convergence_score = round(_theme_jaccard(a.get("top_themes"), b.get("top_themes")), 3)

    theme_score = round(_theme_jaccard(a.get("top_themes"), b.get("top_themes")), 3)

    wa = _theme_words(a.get("top_themes"))
    wb = _theme_words(b.get("top_themes"))

    return {
        "sim_a_id": a["simulation_id"],
        "sim_a_type": a["simulation_type"],
        "sim_b_id": b["simulation_id"],
        "sim_b_type": b["simulation_type"],
        "convergence_score": convergence_score,
        "direction_match": direction_match,
        "distribution_similarity": dist_score,
        "theme_overlap": theme_score,
        "shared_themes": sorted(wa & wb)[:5],
        "diverging_themes": sorted((wa | wb) - (wa & wb))[:5],
    }


# ---------------------------------------------------------------------------
# Phase 2: Reproducibility scoring
# ---------------------------------------------------------------------------


def score_reproducibility_study(study_id: str) -> None:
    """Compute and persist reproducibility scores for a completed study."""
    from app.models.reproducibility import ReproducibilityStudy, ReproducibilityRun
    from app.models.simulation import Simulation
    from app.models.simulation_result import SimulationResult

    db = SessionLocal()
    try:
        study = db.get(ReproducibilityStudy, study_id)
        if not study:
            return

        all_runs = db.execute(
            select(ReproducibilityRun).where(ReproducibilityRun.study_id == study.id)
        ).scalars().all()

        # Collect aggregate results from completed runs only
        agg_results = []
        for run in all_runs:
            sim = db.get(Simulation, run.simulation_id)
            if not sim or sim.status != "complete":
                continue
            agg_type = _AGGREGATE_RESULT_TYPES.get(sim.simulation_type, "aggregate")
            agg = db.execute(
                select(SimulationResult).where(
                    SimulationResult.simulation_id == sim.id,
                    SimulationResult.result_type == agg_type,
                )
            ).scalar_one_or_none()
            if agg:
                agg_results.append(agg)

        if len(agg_results) < 2:
            study.status = "complete"
            study.confidence_score = None
            study.score_breakdown = {"error": "Not enough successful runs to score"}
            study.completed_at = datetime.utcnow()
            db.commit()
            return

        # Metric 1: Sentiment agreement rate (40%)
        dominants = [_dominant_sentiment(r.sentiment_distribution) for r in agg_results if r.sentiment_distribution]
        if dominants:
            mode_sentiment, mode_count = Counter(dominants).most_common(1)[0]
            sentiment_agreement: float | None = round(mode_count / len(dominants), 3)
        else:
            mode_sentiment = None
            sentiment_agreement = None

        # Metric 2: Distribution variance — mean pairwise JSD, inverted (35%)
        dists = [r.sentiment_distribution for r in agg_results if r.sentiment_distribution]
        if len(dists) >= 2:
            jsds = [_jsd(da, db_) for da, db_ in itertools.combinations(dists, 2)]
            distribution_variance: float | None = round(1.0 - (sum(jsds) / len(jsds)), 3)
        else:
            distribution_variance = None

        # Metric 3: Theme overlap coefficient (25%)
        all_theme_tokens: list[str] = []
        for r in agg_results:
            for t in (r.top_themes or []):
                all_theme_tokens.append(t.lower().strip())

        if all_theme_tokens:
            theme_counts = Counter(all_theme_tokens)
            threshold = len(agg_results) * 0.6
            stable = {t for t, c in theme_counts.items() if c >= threshold}
            theme_overlap: float | None = round(len(stable) / max(len(theme_counts), 1), 3)
        else:
            theme_overlap = None

        # Composite confidence score
        parts: list[float] = []
        weight_sum = 0.0
        if sentiment_agreement is not None:
            parts.append(0.40 * sentiment_agreement)
            weight_sum += 0.40
        if distribution_variance is not None:
            parts.append(0.35 * distribution_variance)
            weight_sum += 0.35
        if theme_overlap is not None:
            parts.append(0.25 * theme_overlap)
            weight_sum += 0.25

        confidence: float | None = round(sum(parts) / weight_sum, 3) if parts else None

        study.sentiment_agreement_rate = sentiment_agreement
        study.distribution_variance_score = distribution_variance
        study.theme_overlap_coefficient = theme_overlap
        study.confidence_score = confidence
        study.score_breakdown = {
            "sentiment_agreement_rate": sentiment_agreement,
            "distribution_variance_score": distribution_variance,
            "theme_overlap_coefficient": theme_overlap,
            "confidence_score": confidence,
            "n_runs_scored": len(agg_results),
            "dominant_sentiment": mode_sentiment,
        }
        study.status = "complete"
        study.completed_at = datetime.utcnow()
        db.commit()
        logger.info(f"Reproducibility study {study_id} scored: confidence={confidence}")

    except Exception as e:
        logger.error(f"Failed to score reproducibility study {study_id}: {e}")
        try:
            study = db.get(ReproducibilityStudy, study_id)
            if study:
                study.status = "failed"
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


def maybe_score_reproducibility(simulation_id: str) -> None:
    """Called after a simulation finishes. Triggers study scoring if all runs are done."""
    from app.models.reproducibility import ReproducibilityRun, ReproducibilityStudy
    from app.models.simulation import Simulation

    db = SessionLocal()
    study_id: str | None = None
    try:
        repro_run = db.execute(
            select(ReproducibilityRun).where(ReproducibilityRun.simulation_id == simulation_id)
        ).scalar_one_or_none()
        if not repro_run:
            return

        study = db.get(ReproducibilityStudy, repro_run.study_id)
        if not study or study.status not in ("running", "pending"):
            return

        all_runs = db.execute(
            select(ReproducibilityRun).where(ReproducibilityRun.study_id == study.id)
        ).scalars().all()

        all_sims = [db.get(Simulation, str(r.simulation_id)) for r in all_runs]
        all_done = all(s and s.status in ("complete", "failed") for s in all_sims)

        if all_done:
            study_id = str(study.id)
    except Exception as e:
        logger.error(f"maybe_score_reproducibility lookup failed for {simulation_id}: {e}")
    finally:
        db.close()

    if study_id:
        score_reproducibility_study(study_id)

