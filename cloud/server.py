from __future__ import annotations

import base64
import hmac
import json
import os
import sqlite3
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl

from cloud.payments import create_checkout, payment_from_event, verify_webhook
from edge.entitlement import canonical_payload
from edge.plans import get_plan, list_plans

STATE_DIR = Path(os.environ.get("WAVE_CLOUD_STATE_DIR", "/var/lib/ung-wave-cloud"))
DB_FILE = STATE_DIR / "wave-cloud.sqlite3"
PRIVATE_KEY_FILE = STATE_DIR / "entitlement-private.pem"

app = FastAPI(title="UNG-WAVE Subscription Control Plane", version="0.2.0")


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    model: str = Field(default="UGANET LINK256", max_length=64)


class PaymentConfirmRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    plan: str = Field(min_length=1, max_length=64)
    payment_reference: str = Field(min_length=1, max_length=128)
    paid_at: int | None = None


class CheckoutRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    plan: str = Field(min_length=1, max_length=64)
    success_url: HttpUrl
    cancel_url: HttpUrl


def db() -> sqlite3.Connection:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entitlements (
            device_id TEXT PRIMARY KEY,
            plan TEXT NOT NULL,
            issued_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            payment_reference TEXT NOT NULL UNIQUE,
            FOREIGN KEY(device_id) REFERENCES devices(device_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_events (
            payment_reference TEXT PRIMARY KEY,
            device_id TEXT NOT NULL,
            plan TEXT NOT NULL,
            paid_at INTEGER NOT NULL,
            processed_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def _private_key() -> Ed25519PrivateKey:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    env_pem = os.environ.get("WAVE_ENTITLEMENT_PRIVATE_KEY")
    if env_pem:
        key = serialization.load_pem_private_key(env_pem.encode(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise RuntimeError("WAVE_ENTITLEMENT_PRIVATE_KEY must be Ed25519")
        return key

    if PRIVATE_KEY_FILE.exists():
        key = serialization.load_pem_private_key(PRIVATE_KEY_FILE.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise RuntimeError("stored entitlement key must be Ed25519")
        return key

    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    PRIVATE_KEY_FILE.write_bytes(pem)
    PRIVATE_KEY_FILE.chmod(0o600)
    return key


def _public_pem() -> str:
    return _private_key().public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def _require_admin(authorization: str | None) -> None:
    expected = os.environ.get("WAVE_BILLING_ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="billing admin token is not configured")
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="invalid billing authorization")


def _envelope(row: sqlite3.Row) -> dict:
    entitlement = {
        "device_id": row["device_id"],
        "plan": row["plan"],
        "issued_at": int(row["issued_at"]),
        "expires_at": int(row["expires_at"]),
        "payment_reference": row["payment_reference"],
    }
    signature = _private_key().sign(canonical_payload(entitlement))
    return {
        "entitlement": entitlement,
        "signature": base64.urlsafe_b64encode(signature).decode(),
    }


def _apply_payment(device_id: str, plan_id: str, payment_reference: str, paid_at: int | None = None) -> dict:
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="unknown plan")

    issued_at = int(paid_at or time.time())
    period_seconds = int(plan["billing_period_days"]) * 86400

    with db() as conn:
        device = conn.execute("SELECT device_id FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="device is not registered")

        already = conn.execute(
            "SELECT payment_reference FROM payment_events WHERE payment_reference = ?",
            (payment_reference,),
        ).fetchone()
        if already:
            row = conn.execute("SELECT * FROM entitlements WHERE device_id = ?", (device_id,)).fetchone()
            if not row:
                raise HTTPException(status_code=409, detail="payment was processed but entitlement is missing")
            return {"ok": True, "duplicate": True, **_envelope(row)}

        current = conn.execute("SELECT expires_at FROM entitlements WHERE device_id = ?", (device_id,)).fetchone()
        starts_at = max(issued_at, int(current["expires_at"])) if current else issued_at
        expires_at = starts_at + period_seconds

        conn.execute(
            """
            INSERT INTO payment_events(payment_reference, device_id, plan, paid_at, processed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payment_reference, device_id, plan_id, issued_at, int(time.time())),
        )
        conn.execute(
            """
            INSERT INTO entitlements(device_id, plan, issued_at, expires_at, payment_reference)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                plan=excluded.plan,
                issued_at=excluded.issued_at,
                expires_at=excluded.expires_at,
                payment_reference=excluded.payment_reference
            """,
            (device_id, plan_id, issued_at, expires_at, payment_reference),
        )
        row = conn.execute("SELECT * FROM entitlements WHERE device_id = ?", (device_id,)).fetchone()

    return {"ok": True, "duplicate": False, **_envelope(row)}


@app.get("/health")
def health():
    return {"status": "ready", "service": "UNG-WAVE subscription control plane", "version": "0.2.0"}


@app.get("/api/v1/plans")
def plans():
    return {"plans": list_plans()}


@app.get("/api/v1/public-key")
def public_key():
    return {"algorithm": "Ed25519", "public_key_pem": _public_pem()}


@app.post("/api/v1/devices/register")
def register_device(request: DeviceRegisterRequest):
    now = int(time.time())
    with db() as conn:
        conn.execute(
            """
            INSERT INTO devices(device_id, model, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET model=excluded.model, updated_at=excluded.updated_at
            """,
            (request.device_id, request.model, now, now),
        )
    return {"ok": True, "device_id": request.device_id}


@app.post("/api/v1/billing/checkout")
def start_checkout(request: CheckoutRequest):
    if not get_plan(request.plan):
        raise HTTPException(status_code=404, detail="unknown plan")
    with db() as conn:
        device = conn.execute("SELECT device_id FROM devices WHERE device_id = ?", (request.device_id,)).fetchone()
    if not device:
        raise HTTPException(status_code=404, detail="device is not registered")
    try:
        checkout = create_checkout(
            request.device_id,
            request.plan,
            str(request.success_url),
            str(request.cancel_url),
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return {
        "ok": True,
        "provider": checkout.provider,
        "checkout_url": checkout.checkout_url,
        "session_id": checkout.session_id,
    }


@app.post("/api/v1/billing/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: str | None = Header(default=None, alias="stripe-signature")):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="missing Stripe signature")
    payload = await request.body()
    try:
        event = verify_webhook(payload, stripe_signature)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid billing webhook: {exc}")

    payment = payment_from_event(event)
    if not payment:
        return {"ok": True, "processed": False, "event_type": event.get("type")}

    result = _apply_payment(
        payment["device_id"],
        payment["plan"],
        payment["payment_reference"],
        payment.get("paid_at"),
    )
    return {"processed": True, **result}


@app.post("/api/v1/payments/confirm")
def confirm_payment(request: PaymentConfirmRequest, authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    return _apply_payment(
        request.device_id,
        request.plan,
        request.payment_reference,
        request.paid_at,
    )


@app.get("/api/v1/entitlements/{device_id}")
def get_entitlement(device_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM entitlements WHERE device_id = ?", (device_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="no entitlement")
    return _envelope(row)
