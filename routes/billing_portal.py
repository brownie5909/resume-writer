import os
from datetime import datetime, timezone

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


def timestamp_to_iso(value):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return None


def get_subscription_item(subscription):
    items = stripe_value(subscription, "items", {}) or {}
    data = stripe_value(items, "data", []) or []
    if isinstance(data, list) and data:
        return data[0]
    return None


@router.get("/subscriptions/live-status")
async def get_live_subscription_status(current_user: dict = Depends(get_current_user)):
    """Return live Stripe subscription status for the current user when available."""
    subscription_id = current_user.get("stripe_subscription_id")
    customer_id = current_user.get("stripe_customer_id")
    tier = current_user.get("tier", "basic")

    if not subscription_id:
        return {
            "success": True,
            "tier": tier,
            "customer_id": customer_id,
            "subscription_id": None,
            "status": "inactive" if tier in ("basic", "free") else "unknown",
            "cancel_at_period_end": False,
            "current_period_end": None,
            "current_period_start": None,
            "access_until": None,
        }

    stripe.api_key = get_stripe_secret_key()

    try:
        subscription = stripe.Subscription.retrieve(subscription_id)
        subscription_item = get_subscription_item(subscription)
        status = stripe_value(subscription, "status", "unknown")
        cancel_at_period_end = bool(stripe_value(subscription, "cancel_at_period_end", False))

        period_end_raw = stripe_value(subscription, "current_period_end")
        period_start_raw = stripe_value(subscription, "current_period_start")

        if not period_end_raw and subscription_item:
            period_end_raw = stripe_value(subscription_item, "current_period_end")

        if not period_start_raw and subscription_item:
            period_start_raw = stripe_value(subscription_item, "current_period_start")

        current_period_end = timestamp_to_iso(period_end_raw)
        current_period_start = timestamp_to_iso(period_start_raw)

        return {
            "success": True,
            "tier": tier,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "status": status,
            "cancel_at_period_end": cancel_at_period_end,
            "current_period_end": current_period_end,
            "current_period_start": current_period_start,
            "access_until": current_period_end,
        }
    except Exception as error:
        return {
            "success": False,
            "tier": tier,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "status": "unknown",
            "cancel_at_period_end": False,
            "current_period_end": None,
            "current_period_start": None,
            "access_until": None,
            "error": str(error),
        }


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
