from typing import Optional
from pydantic import BaseModel


class CheckoutSessionResponse(BaseModel):
    url: str


class PortalSessionResponse(BaseModel):
    url: str


class BillingStatusResponse(BaseModel):
    plan: str
    simulations_used: int
    plan_limit: int
    billing_period_ends_at: Optional[str] = None
    stripe_customer_id: Optional[str] = None
