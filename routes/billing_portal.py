import os

import stripe
from fastapi import APIRouter, Depends, HTTPException

from routes.user_management import get_current_user

router = APIRouter()


def stripe_value(obj, key, default=None):
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)
    except Exception:
        return default


def get_stripe_secret_key() -> str:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        raise HTTPException(status_code=500, detail="Stripe secret key is not configured")
    return secret_key


@router.post("/subscriptions/customer-portal")
async def create_customer_portal_session(
    return_url: str = "https://jobreadytools.com.au/account/",
    current_user: dict = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session for billing and subscription management."""
    customer_id = current_user.get("stripe_customer_id")

    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe customer found for this account. Please upgrade to a paid plan first.",
        )

    stripe.api_key = get_stripe_secret_key()

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return {
            "success": True,
            "portal_url": stripe_value(portal_session, "url"),
            "message": "Stripe customer portal session created",
        }
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Stripe customer portal error: {str(error)}")
