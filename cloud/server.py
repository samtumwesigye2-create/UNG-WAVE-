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
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from edge.entitlement import canonical_payload
from edge.plans import get_plan, list_plans

STATE_DIR = Path(os.environ.get("WAVE_CLOUD_STATE_DIR", "/var/lib/ung-wave-cloud"))
DB_FILE = STATE_DIR / "wave-cloud.sqlite3"
PRIVATE_KEY_FILE = STATE_DIR / "entitlement-private.pem"

app = FastAPI(title="UNG-WAVE Subscription Control Plane", version="0.1.0")


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    model: str = Field(default="UGANET LINK256", max_length=64)


class PaymentConfirmRequest(BaseModel):
    device_id: str = Field(min_length=8, max_length=64)
    plan: str = Field(min_length=1, max_length=64)
    payment_reference: str = Field(min_length=1, max_length=128)
    paid_at: int | None = None


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


@app.get("/health")
def health():
    return {"status": "ready", "service": "UNG-WAVE subscription control plane"}


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


@app.post("/api/v1/payments/confirm")
def confirm_payment(request: PaymentConfirmRequest, authorization: str | None = Header(default=None)):
    _require_admin(authorization)
    plan = get_plan(request.plan)
    if not plan:
        raise HTTPException(status_code=404, detail="unknown plan")

    issued_at = int(request.paid_at or time.time())
    period_seconds = int(plan["billing_period_days"]) * 86400
    with db() as conn:
        device = conn.execute("SELECT device_id FROM devices WHERE device_id = ?", (request.device_id,)).fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="device is not registered")

        current = conn.execute("SELECT expires_at FROM entitlements WHERE device_id = ?", (request.device_id,)).fetchone()
        starts_at = max(issued_at, int(current["expires_at"])) if current else issued_at
        expires_at = starts_at + period_seconds
        try:
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
                (request.device_id, request.plan, issued_at, expires_at, request.payment_reference),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="payment reference already used")

        row = conn.execute("SELECT * FROM entitlements WHERE device_id = ?", (request.device_id,)).fetchone()

    return {"ok": True, **_envelope(row)}


@app.get("/api/v1/entitlements/{device_id}")
def get_entitlement(device_id: str):
    with db() as conn:
        row = conn.execute("SELECT * FROM entitlements WHERE device_id = ?", (device_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="no entitlement")
    return _envelope(row)
