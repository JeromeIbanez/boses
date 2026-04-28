"""
Billing endpoints — Stripe Checkout, Customer Portal, and webhook handler.

The webhook route (/billing/webhook) must NOT use get_current_user because
Stripe calls it server-to-server.  All other routes require authentication.
"""
import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutSessionResponse,
    PortalSessionResponse,
)
from app.services.stripe_service import PLAN_LIMITS, get_stripe, get_stripe_price_ids

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@router.get("/status", response_model=BillingStatusResponse)
def billing_status(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current plan, usage counter, and billing period for the workspace."""
    company = db.get(Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return BillingStatusResponse(
        plan=company.plan,
        simulations_used=company.simulations_used,
        plan_limit=PLAN_LIMITS.get(company.plan, 0),
        billing_period_ends_at=(
            company.billing_period_ends_at.isoformat() if company.billing_period_ends_at else None
        ),
        stripe_customer_id=company.stripe_customer_id,
    )


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    plan: str  # "starter" | "pro" | "agency"


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    body: CheckoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for the requested plan.
    Returns a redirect URL — the frontend should do window.location.href = url.
    """
    price_ids = get_stripe_price_ids()
    if body.plan not in price_ids:
        raise HTTPException(status_code=422, detail=f"Invalid plan '{body.plan}'. Choose: starter, pro, agency.")

    price_id = price_ids[body.plan]
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail="Stripe is not configured yet. Contact support.",
        )

    company = db.get(Company, current_user.company_id)
    user = db.get(User, current_user.id)
    if not company or not user:
        raise HTTPException(status_code=404, detail="Company or user not found")

    s = get_stripe()
    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{settings.FRONTEND_URL}/settings/billing?checkout=success",
        "cancel_url": f"{settings.FRONTEND_URL}/settings/billing?checkout=cancelled",
        "metadata": {"company_id": str(company.id), "plan": body.plan},
    }
    if company.stripe_customer_id:
        params["customer"] = company.stripe_customer_id
    else:
        params["customer_email"] = user.email

    try:
        session = s.checkout.Session.create(**params)
    except stripe.StripeError as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=502, detail="Failed to create checkout session. Try again.")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# Customer Portal
# ---------------------------------------------------------------------------


@router.post("/portal", response_model=PortalSessionResponse)
def create_portal_session(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Billing Portal session so the user can manage their
    subscription, update payment methods, and view invoices.
    """
    company = db.get(Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No active subscription found.")

    s = get_stripe()
    try:
        session = s.billing_portal.Session.create(
            customer=company.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/settings/billing",
        )
    except stripe.StripeError as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(status_code=502, detail="Failed to open billing portal. Try again.")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# Webhook (no auth — Stripe verifies via signature)
# ---------------------------------------------------------------------------


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe sends events here.  We verify the signature and update the DB.

    Events handled:
      - checkout.session.completed      → link customer, activate plan, reset counter
      - customer.subscription.updated   → sync plan after upgrade/downgrade
      - customer.subscription.deleted   → downgrade to free
      - invoice.paid                    → reset simulations_used for the new period
    """
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature check (dev mode)")
        try:
            import json
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
    else:
        try:
            event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    data = event["data"]["object"]
    event_type = event["type"]
    logger.info("Stripe webhook: %s", event_type)

    price_ids = get_stripe_price_ids()
    price_to_plan = {v: k for k, v in price_ids.items()}

    # ------------------------------------------------------------------
    if event_type == "checkout.session.completed":
        company_id = data.get("metadata", {}).get("company_id")
        plan = data.get("metadata", {}).get("plan")
        if not company_id or not plan:
            logger.warning("checkout.session.completed missing metadata")
            return {"received": True}

        company = db.get(Company, company_id)
        if company:
            company.stripe_customer_id = data.get("customer")
            company.stripe_subscription_id = data.get("subscription")
            company.plan = plan
            company.simulations_used = 0
            db.commit()
            logger.info("Company %s upgraded to %s", company_id, plan)

    # ------------------------------------------------------------------
    elif event_type == "customer.subscription.updated":
        sub_id = data.get("id")
        company = db.execute(
            select(Company).where(Company.stripe_subscription_id == sub_id)
        ).scalar_one_or_none()
        if company:
            price_id = data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id")
            new_plan = price_to_plan.get(price_id, company.plan)
            company.plan = new_plan
            db.commit()
            logger.info("Company %s plan synced to %s", company.id, new_plan)

    # ------------------------------------------------------------------
    elif event_type == "customer.subscription.deleted":
        sub_id = data.get("id")
        company = db.execute(
            select(Company).where(Company.stripe_subscription_id == sub_id)
        ).scalar_one_or_none()
        if company:
            company.plan = "free"
            company.stripe_subscription_id = None
            db.commit()
            logger.info("Company %s subscription cancelled → free", company.id)

    # ------------------------------------------------------------------
    elif event_type == "invoice.paid":
        customer_id = data.get("customer")
        company = db.execute(
            select(Company).where(Company.stripe_customer_id == customer_id)
        ).scalar_one_or_none()
        if company:
            company.simulations_used = 0
            # Extract period end from the first line item
            try:
                period_end = data["lines"]["data"][0]["period"]["end"]
                company.billing_period_ends_at = datetime.fromtimestamp(period_end, tz=timezone.utc)
            except (KeyError, IndexError, TypeError):
                pass
            db.commit()
            logger.info("invoice.paid for company %s — counter reset", company.id)

    return {"received": True}
