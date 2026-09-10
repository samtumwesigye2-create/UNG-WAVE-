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


def _json_request(url: str, payload: dict | None = None, timeout: int = 10) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def register_device(timeout: int = 10) -> dict:
    base = control_url()
    if not base:
        return {"ok": False, "error": "WAVE_CONTROL_URL is not configured"}
    try:
        return _json_request(
            f"{base}/api/v1/devices/register",
            {"device_id": device_id(), "model": "UGANET LINK256"},
            timeout,
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def sync_entitlement(timeout: int = 10) -> dict:
    base = control_url()
    if not base:
        return {"ok": False, "error": "WAVE_CONTROL_URL is not configured"}
    url = f"{base}/api/v1/entitlements/{urllib.parse.quote(device_id())}"
    try:
        envelope = _json_request(url, timeout=timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"ok": False, "error": "no active entitlement"}
        return {"ok": False, "error": f"control plane HTTP {exc.code}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}
    return verify_and_store(envelope)
