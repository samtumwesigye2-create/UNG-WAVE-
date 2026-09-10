from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from edge.device_identity import device_id
from edge.plans import get_plan
from edge.subscription import save_verified_entitlement

PUBLIC_KEY_FILE = Path("/etc/ung-wave/entitlement-public.pem")


def canonical_payload(entitlement: dict) -> bytes:
    payload = {
        "device_id": entitlement["device_id"],
        "plan": entitlement["plan"],
        "issued_at": int(entitlement["issued_at"]),
        "expires_at": int(entitlement["expires_at"]),
        "payment_reference": entitlement.get("payment_reference"),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _load_public_key() -> Ed25519PublicKey:
    pem = os.environ.get("WAVE_ENTITLEMENT_PUBLIC_KEY")
    data = pem.encode() if pem else PUBLIC_KEY_FILE.read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise ValueError("entitlement public key must be Ed25519")
    return key


def verify_and_store(envelope: dict) -> dict:
    entitlement = envelope.get("entitlement") or {}
    signature_text = envelope.get("signature") or ""

    if entitlement.get("device_id") != device_id():
        return {"ok": False, "error": "entitlement is for a different LINK256 device"}
    if not get_plan(str(entitlement.get("plan", ""))):
        return {"ok": False, "error": "unknown subscription plan"}
    try:
        signature = base64.urlsafe_b64decode(signature_text.encode())
        _load_public_key().verify(signature, canonical_payload(entitlement))
    except (OSError, ValueError, InvalidSignature, base64.binascii.Error) as exc:
        return {"ok": False, "error": f"invalid entitlement signature: {exc}"}

    save_verified_entitlement(entitlement)
    return {"ok": True, "entitlement": entitlement}
