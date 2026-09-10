from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import stripe
except ImportError:  # keeps non-billing edge installs importable
    stripe = None


@dataclass(frozen=True)
class CheckoutResult:
    provider: str
    checkout_url: str
    session_id: str


def _require_stripe():
    if stripe is None:
        raise RuntimeError("stripe package is not installed")
    secret = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = secret
    return stripe


def price_id_for(plan_id: str) -> str:
    env_name = {
        "wave-basic": "STRIPE_PRICE_WAVE_BASIC",
        "wave-plus": "STRIPE_PRICE_WAVE_PLUS",
        "wave-pro": "STRIPE_PRICE_WAVE_PRO",
    }.get(plan_id)
    if not env_name:
        raise ValueError("unknown plan")
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise RuntimeError(f"{env_name} is not configured")
    return value


def create_checkout(device_id: str, plan_id: str, success_url: str, cancel_url: str) -> CheckoutResult:
    client = _require_stripe()
    session = client.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id_for(plan_id), "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=device_id,
        metadata={"device_id": device_id, "plan": plan_id},
        subscription_data={"metadata": {"device_id": device_id, "plan": plan_id}},
    )
    return CheckoutResult(provider="stripe", checkout_url=session.url, session_id=session.id)


def verify_webhook(payload: bytes, signature: str):
    client = _require_stripe()
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    return client.Webhook.construct_event(payload, signature, secret)


def payment_from_event(event) -> dict | None:
    """Normalize successful Stripe billing events into WAVE payment records.

    checkout.session.completed activates the first paid period. invoice.paid renews
    later periods. Event IDs are used as idempotent payment references.
    """
    event_type = event.get("type")
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        if obj.get("payment_status") != "paid":
            return None
        metadata = obj.get("metadata") or {}
        device_id = metadata.get("device_id") or obj.get("client_reference_id")
        plan = metadata.get("plan")
        if not device_id or not plan:
            return None
        return {
            "device_id": device_id,
            "plan": plan,
            "payment_reference": f"stripe:{event['id']}",
            "paid_at": int(event.get("created", 0) or 0),
        }

    if event_type == "invoice.paid":
        subscription_id = obj.get("subscription")
        if not subscription_id:
            return None
        client = _require_stripe()
        subscription = client.Subscription.retrieve(subscription_id)
        metadata = subscription.get("metadata") or {}
        device_id = metadata.get("device_id")
        plan = metadata.get("plan")
        if not device_id or not plan:
            return None
        return {
            "device_id": device_id,
            "plan": plan,
            "payment_reference": f"stripe:{event['id']}",
            "paid_at": int(event.get("created", 0) or 0),
        }

    return None
