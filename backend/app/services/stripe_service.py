"""
Stripe billing helpers.

PLAN_LIMITS maps plan name → max simulations per billing period.
check_quota_or_402 is the single point where quota is enforced and the
simulations_used counter is incremented — call it at the top of create_simulation
before any DB rows are written.
"""
import stripe as _stripe

from app.config import settings

# ---------------------------------------------------------------------------
# Plan configuration
# ---------------------------------------------------------------------------

PLAN_LIMITS: dict[str, int] = {
    "free": 3,
    "starter": 10,
    "pro": 35,
    "agency": 100,
    "enterprise": 9_999,
}

PLAN_SEAT_LIMITS: dict[str, int] = {
    "free": 3,
    "starter": 3,
    "pro": 10,
    "agency": 9_999,
    "enterprise": 9_999,
}

OVERAGE_CENTS: dict[str, int] = {
    "starter": 2_000,   # $20
    "pro": 1_500,        # $15
    "agency": 1_000,     # $10
}


def get_stripe_price_ids() -> dict[str, str]:
    """Return price-id map, evaluated lazily so tests can patch config."""
    return {
        "starter": settings.STRIPE_STARTER_PRICE_ID,
        "pro": settings.STRIPE_PRO_PRICE_ID,
        "agency": settings.STRIPE_AGENCY_PRICE_ID,
    }


# ---------------------------------------------------------------------------
# Stripe client
# ---------------------------------------------------------------------------

def get_stripe() -> _stripe:
    """Return the stripe module with api_key configured."""
    _stripe.api_key = settings.STRIPE_SECRET_KEY
    return _stripe


# ---------------------------------------------------------------------------
# Quota gate
# ---------------------------------------------------------------------------

UNLIMITED_DOMAIN = "temujintechnologies.com"


def check_quota_or_402(company, db, user_email: str = "") -> None:
    """
    Raise HTTP 402 if the company has reached its simulation limit for the
    current billing period.  Otherwise increment simulations_used and commit.

    Pass the *already-loaded* Company ORM object so we avoid a redundant DB
    hit (the caller fetched it to build the simulation anyway).

    Users with a @temujintechnologies.com email bypass the quota entirely.
    """
    # Internal team — unlimited access, no counter increment
    if user_email.lower().endswith(f"@{UNLIMITED_DOMAIN}"):
        return

    limit = PLAN_LIMITS.get(company.plan, 0)
    if company.simulations_used >= limit:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "plan": company.plan,
                "limit": limit,
                "used": company.simulations_used,
                "message": (
                    "You've used all simulations in your plan for this period. "
                    "Upgrade to run more."
                ),
            },
        )
    company.simulations_used += 1
    db.commit()


def check_seat_quota_or_402(company, db, inviter_email: str = "") -> None:
    """
    Raise HTTP 402 if the workspace has reached its seat limit.

    Counts active members + non-expired pending invites so that the limit is
    enforced even before an invite is accepted.

    Users with a @temujintechnologies.com email bypass the check entirely.
    """
    if inviter_email.lower().endswith(f"@{UNLIMITED_DOMAIN}"):
        return

    from datetime import datetime, timezone
    from sqlalchemy import select, func
    from app.models.user import User
    from app.models.company_invite import CompanyInvite

    limit = PLAN_SEAT_LIMITS.get(company.plan, 1)

    active_members = db.execute(
        select(func.count()).where(
            User.company_id == company.id,
            User.is_active == True,  # noqa: E712
        )
    ).scalar_one()

    now = datetime.now(timezone.utc)
    pending_invites = db.execute(
        select(func.count()).where(
            CompanyInvite.company_id == company.id,
            CompanyInvite.accepted_at == None,  # noqa: E711
            CompanyInvite.expires_at > now,
        )
    ).scalar_one()

    current_count = active_members + pending_invites

    if current_count >= limit:
        from fastapi import HTTPException

        plan_label = company.plan.capitalize()
        raise HTTPException(
            status_code=402,
            detail={
                "error": "seat_limit_exceeded",
                "plan": company.plan,
                "limit": limit,
                "current_count": current_count,
                "message": (
                    f"Your {plan_label} plan allows up to {limit} seat{'s' if limit != 1 else ''}. "
                    "Upgrade your plan to invite more team members."
                ),
            },
        )
