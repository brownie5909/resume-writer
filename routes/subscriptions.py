from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import os
import stripe

from .user_management import get_current_user, get_db

router = APIRouter()


class SubscriptionResponse(BaseModel):
    subscription_id: Optional[str]
    customer_id: Optional[str]
    status: str
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    tier: str
    amount: Optional[int]
    currency: Optional[str]


PRICE_ENV_BY_TIER = {
    "premium": "STRIPE_PREMIUM_PRICE_ID",
    "professional": "STRIPE_PROFESSIONAL_PRICE_ID",
}


def get_stripe_secret_key() -> str:
    secret_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret_key:
        raise HTTPException(status_code=500, detail="Stripe secret key is not configured")
    return secret_key


def get_price_id_for_tier(tier: str) -> str:
    price_env_name = PRICE_ENV_BY_TIER.get(tier)
    if not price_env_name:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")

    price_id = os.getenv(price_env_name, "").strip()
    if not price_id:
        raise HTTPException(status_code=500, detail=f"Stripe price ID is not configured for {tier}")

    return price_id


def update_user_stripe_customer_id(user_id: str, customer_id: str) -> None:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET stripe_customer_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (customer_id, user_id),
        )
        conn.commit()


def update_user_subscription(
    user_id: str,
    tier: str,
    customer_id: Optional[str],
    subscription_id: Optional[str],
) -> None:
    if tier not in PRICE_ENV_BY_TIER:
        raise ValueError("Invalid subscription tier")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET tier = ?,
                stripe_customer_id = COALESCE(?, stripe_customer_id),
                stripe_subscription_id = COALESCE(?, stripe_subscription_id),
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (tier, customer_id, subscription_id, user_id),
        )
        conn.commit()


def cancel_user_subscription_access(subscription_id: Optional[str]) -> None:
    if not subscription_id:
        return

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET tier = 'basic',
                stripe_subscription_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE stripe_subscription_id = ?
            """,
            (subscription_id,),
        )
        conn.commit()


@router.post("/subscriptions/create-checkout")
async def create_checkout_session(
    tier: str,
    current_user: dict = Depends(get_current_user),
):
    """Create a real Stripe Checkout session for a paid subscription tier."""
    tier = (tier or "").strip().lower()

    if tier not in PRICE_ENV_BY_TIER:
        raise HTTPException(status_code=400, detail="Invalid subscription tier")

    if tier == current_user.get("tier"):
        raise HTTPException(status_code=400, detail="Already subscribed to this tier")

    stripe.api_key = get_stripe_secret_key()
    price_id = get_price_id_for_tier(tier)
    success_url = os.getenv("STRIPE_SUCCESS_URL", "https://jobreadytools.com.au/dashboard/").strip()
    cancel_url = os.getenv("STRIPE_CANCEL_URL", "https://jobreadytools.com.au/pricing/").strip()

    try:
        session_params = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": f"{success_url}?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{cancel_url}?checkout=cancelled",
            "client_reference_id": current_user["user_id"],
            "metadata": {
                "user_id": current_user["user_id"],
                "tier": tier,
            },
            "subscription_data": {
                "metadata": {
                    "user_id": current_user["user_id"],
                    "tier": tier,
                }
            },
            "allow_promotion_codes": True,
        }

        existing_customer_id = current_user.get("stripe_customer_id")
        if existing_customer_id:
            session_params["customer"] = existing_customer_id
        else:
            session_params["customer_email"] = current_user.get("email")

        checkout_session = stripe.checkout.Session.create(**session_params)

        if checkout_session.customer and not existing_customer_id:
            update_user_stripe_customer_id(current_user["user_id"], checkout_session.customer)

        return {
            "checkout_url": checkout_session.url,
            "session_id": checkout_session.id,
            "tier": tier,
        }

    except stripe.error.StripeError as error:
        raise HTTPException(status_code=502, detail=f"Stripe checkout error: {str(error)}")


@router.get("/subscriptions/current")
async def get_current_subscription(current_user: dict = Depends(get_current_user)):
    """Get current user's subscription details."""
    try:
        subscription_data = SubscriptionResponse(
            subscription_id=current_user.get("stripe_subscription_id"),
            customer_id=current_user.get("stripe_customer_id"),
            status="active" if current_user["tier"] not in ("free", "basic") else "inactive",
            current_period_start=datetime.now() if current_user["tier"] not in ("free", "basic") else None,
            current_period_end=datetime.now() + timedelta(days=30) if current_user["tier"] not in ("free", "basic") else None,
            tier=current_user["tier"],
            amount=1900 if current_user["tier"] == "premium" else 3900 if current_user["tier"] == "professional" else None,
            currency="usd",
        )
        return subscription_data
    except Exception:
        return SubscriptionResponse(
            subscription_id=None,
            customer_id=current_user.get("stripe_customer_id"),
            status="active" if current_user["tier"] not in ("free", "basic") else "inactive",
            current_period_start=None,
            current_period_end=None,
            tier=current_user["tier"],
            amount=None,
            currency=None,
        )


@router.post("/subscriptions/change-tier")
async def change_subscription_tier(
    new_tier: str,
    current_user: dict = Depends(get_current_user),
):
    """Change subscription tier (mock for testing)."""
    if new_tier not in ["free", "basic", "premium", "professional"]:
        raise HTTPException(status_code=400, detail="Invalid tier")

    current_tier = current_user["tier"]

    if new_tier == current_tier:
        raise HTTPException(status_code=400, detail="Already on this tier")

    if new_tier in ("free", "basic"):
        return {
            "message": "Subscription would be canceled (mock)",
            "tier": "basic",
            "note": "In production, this would cancel the Stripe subscription",
        }
    elif current_tier in ("free", "basic"):
        return {
            "message": f"Would create new {new_tier} subscription (mock)",
            "tier": new_tier,
            "note": "In production, this would create a new Stripe subscription",
        }
    else:
        return {
            "message": f"Would change from {current_tier} to {new_tier} (mock)",
            "tier": new_tier,
            "note": "In production, this would modify the existing subscription",
        }


@router.post("/subscriptions/cancel")
async def cancel_user_subscription(current_user: dict = Depends(get_current_user)):
    """Cancel current subscription (mock for testing)."""
    if current_user["tier"] in ("free", "basic"):
        raise HTTPException(status_code=400, detail="No active subscription to cancel")

    return {
        "message": f"Would cancel {current_user['tier']} subscription (mock)",
        "tier": "basic",
        "note": "In production, this would cancel the Stripe subscription at period end",
    }


@router.post("/subscriptions/billing-portal")
async def create_billing_portal_session(
    return_url: str,
    current_user: dict = Depends(get_current_user),
):
    """Create billing portal session (mock for testing)."""
    customer_id = current_user.get("stripe_customer_id")
    if not customer_id:
        return {
            "portal_url": f"https://billing.stripe.com/mock?return_url={return_url}",
            "message": "Mock billing portal - would redirect to Stripe in production",
        }

    return {
        "portal_url": f"https://billing.stripe.com/mock/{customer_id}?return_url={return_url}",
        "message": "Mock billing portal for existing customer",
    }


@router.get("/subscriptions/invoices")
async def get_invoices(
    current_user: dict = Depends(get_current_user),
    limit: int = 10,
):
    """Get user's billing invoices (mock for testing)."""
    customer_id = current_user.get("stripe_customer_id")
    if not customer_id:
        return {"invoices": []}

    mock_invoices = [
        {
            "id": f"inv_mock_{i}",
            "amount_paid": 1900 if current_user["tier"] == "premium" else 3900,
            "amount_due": 0,
            "currency": "usd",
            "status": "paid",
            "created": datetime.now() - timedelta(days=30 * i),
            "period_start": datetime.now() - timedelta(days=30 * (i + 1)),
            "period_end": datetime.now() - timedelta(days=30 * i),
            "invoice_pdf": f"https://invoice.stripe.com/mock_{i}.pdf",
            "hosted_invoice_url": f"https://invoice.stripe.com/mock_{i}",
        }
        for i in range(min(3, limit))
    ]

    return {"invoices": mock_invoices}


@router.post("/subscriptions/webhook")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events that update Hire Ready user subscription access."""
    stripe.api_key = get_stripe_secret_key()
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
        else:
            event = stripe.Event.construct_from(await request.json(), stripe.api_key)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature")

    event_type = event.get("type")
    event_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        metadata = event_object.get("metadata", {}) or {}
        user_id = metadata.get("user_id") or event_object.get("client_reference_id")
        tier = metadata.get("tier")
        customer_id = event_object.get("customer")
        subscription_id = event_object.get("subscription")

        if user_id and tier in PRICE_ENV_BY_TIER:
            update_user_subscription(
                user_id=user_id,
                tier=tier,
                customer_id=customer_id,
                subscription_id=subscription_id,
            )
            return {"success": True, "handled": event_type, "user_id": user_id, "tier": tier}

        return {"success": False, "handled": event_type, "message": "Missing user_id or tier metadata"}

    if event_type == "customer.subscription.deleted":
        subscription_id = event_object.get("id")
        cancel_user_subscription_access(subscription_id)
        return {"success": True, "handled": event_type, "subscription_id": subscription_id}

    return {"success": True, "handled": False, "event_type": event_type}
