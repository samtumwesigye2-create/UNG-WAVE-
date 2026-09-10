from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

STATE_DIR = Path("/var/lib/ung-wave")
ENTITLEMENT_FILE = STATE_DIR / "subscription.json"


def _run(cmd: list[str]) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
        return {"ok": p.returncode == 0, "code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(exc)}


def load() -> dict:
    try:
        data = json.loads(ENTITLEMENT_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        data = {}
    expires_at = int(data.get("expires_at", 0) or 0)
    now = int(time.time())
    active = bool(data.get("verified", False) and expires_at > now)
    return {
        "active": active,
        "plan": data.get("plan"),
        "expires_at": expires_at or None,
        "seconds_remaining": max(0, expires_at - now),
        "device_id": data.get("device_id"),
        "reason": "active" if active else ("expired" if expires_at else "no_entitlement"),
    }


def save_verified_entitlement(entitlement: dict) -> None:
    """Persist only an entitlement already verified by the future WAVE cloud client.

    This function is deliberately not exposed as a public API activation endpoint.
    Production activation must verify a server signature before calling it.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "verified": True,
        "device_id": entitlement["device_id"],
        "plan": entitlement["plan"],
        "expires_at": int(entitlement["expires_at"]),
    }
    ENTITLEMENT_FILE.write_text(json.dumps(payload, indent=2))
    ENTITLEMENT_FILE.chmod(0o600)


def enforce(uplink: str, ap_interface: str) -> dict:
    """Gate Internet forwarding while keeping local UGANET available for renewal/support."""
    state = load()
    chain = "UNG_WAVE_SUBSCRIPTION"
    _run(["iptables", "-N", chain])
    _run(["iptables", "-F", chain])
    # Ensure a single jump from FORWARD into the subscription gate.
    if not _run(["iptables", "-C", "FORWARD", "-i", ap_interface, "-o", uplink, "-j", chain])["ok"]:
        _run(["iptables", "-I", "FORWARD", "1", "-i", ap_interface, "-o", uplink, "-j", chain])
    verdict = "ACCEPT" if state["active"] else "REJECT"
    rule = _run(["iptables", "-A", chain, "-j", verdict])
    return {"ok": rule["ok"], "internet_access": state["active"], "subscription": state}
