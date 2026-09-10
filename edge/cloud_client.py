from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from edge.device_identity import device_id
from edge.entitlement import verify_and_store


def control_url() -> str | None:
    value = os.environ.get("WAVE_CONTROL_URL", "").strip().rstrip("/")
    return value or None


def sync_entitlement(timeout: int = 10) -> dict:
    base = control_url()
    if not base:
        return {"ok": False, "error": "WAVE_CONTROL_URL is not configured"}
    url = f"{base}/api/v1/entitlements/{urllib.parse.quote(device_id())}"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            envelope = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}
    return verify_and_store(envelope)
