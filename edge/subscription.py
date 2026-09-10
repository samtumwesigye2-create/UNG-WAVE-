from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

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
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "verified": True,
        "device_id": entitlement["device_id"],
        "plan": entitlement["plan"],
        "expires_at": int(entitlement["expires_at"]),
    }
    ENTITLEMENT_FILE.write_text(json.dumps(payload, indent=2))
    ENTITLEMENT_FILE.chmod(0o600)


def renewal_hosts() -> set[str]:
    hosts = {
        value.strip()
        for value in os.environ.get("WAVE_RENEWAL_ALLOWED_HOSTS", "").split(",")
        if value.strip()
    }
    control = os.environ.get("WAVE_CONTROL_URL", "").strip()
    if control:
        parsed = urlparse(control)
        if parsed.hostname:
            hosts.add(parsed.hostname)
    return hosts


def renewal_ips() -> set[str]:
    ips: set[str] = set()
    for host in renewal_hosts():
        try:
            for result in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
                address = result[4][0]
                if ":" not in address:  # current firewall path is IPv4/iptables
                    ips.add(address)
        except socket.gaierror:
            continue
    return ips


def enforce(uplink: str, ap_interface: str) -> dict:
    """Gate Internet forwarding while preserving a minimal renewal walled garden."""
    state = load()
    chain = "UNG_WAVE_SUBSCRIPTION"
    _run(["iptables", "-N", chain])
    _run(["iptables", "-F", chain])

    if not _run(["iptables", "-C", "FORWARD", "-i", ap_interface, "-o", uplink, "-j", chain])["ok"]:
        _run(["iptables", "-I", "FORWARD", "1", "-i", ap_interface, "-o", uplink, "-j", chain])

    if state["active"]:
        rule = _run(["iptables", "-A", chain, "-j", "ACCEPT"])
        return {
            "ok": rule["ok"],
            "internet_access": True,
            "renewal_only": False,
            "subscription": state,
        }

    allowed_ips = sorted(renewal_ips())
    for ip in allowed_ips:
        _run(["iptables", "-A", chain, "-p", "tcp", "-d", ip, "--dport", "443", "-j", "ACCEPT"])

    reject = _run(["iptables", "-A", chain, "-j", "REJECT"])
    return {
        "ok": reject["ok"],
        "internet_access": False,
        "renewal_only": True,
        "renewal_ips": allowed_ips,
        "subscription": state,
    }
