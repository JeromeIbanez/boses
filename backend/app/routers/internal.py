"""
internal.py

Internal-only endpoints for platform operations.
Not exposed to end users. Protected by environment check.

Endpoints:
    POST /internal/ethnography/refresh/{market_code}
        Manually trigger a cultural context refresh for a market.
        Returns immediately; runs as a background task.
        Useful for: forcing a refresh before a demo, diagnosing stale context,
        or triggering from an external cron scheduler.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.config import settings
from app.services.ethnography_service import refresh_market_context

router = APIRouter(prefix="/internal", tags=["internal"])

_SUPPORTED_MARKETS = {"ID", "PH", "VN"}


def _check_internal_access() -> None:
    """
    Block this endpoint in production unless we add an internal API key.
    In development/staging it's open for testing.
    """
    if settings.is_production:
        raise HTTPException(
            status_code=403,
            detail="Internal endpoints are disabled in production. Use the scheduled trigger.",
        )


@router.post("/ethnography/refresh/{market_code}", status_code=202)
def trigger_ethnography_refresh(
    market_code: str,
    background_tasks: BackgroundTasks,
):
    """
    Manually trigger a cultural context refresh for a market.

    market_code must be one of: ID, PH, VN

    The refresh runs as a background task. To check results:
        SELECT status, quality_score, signals_json
        FROM cultural_context_snapshots
        WHERE market_code = '{market_code}'
        ORDER BY created_at DESC LIMIT 1;

    See verification steps in the plan for a full testing walkthrough.
    """
    _check_internal_access()

    market_code = market_code.upper()
    if market_code not in _SUPPORTED_MARKETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported market code '{market_code}'. Must be one of: {', '.join(sorted(_SUPPORTED_MARKETS))}",
        )

    background_tasks.add_task(refresh_market_context, market_code)
    return {"status": "queued", "market_code": market_code}
