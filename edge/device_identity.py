from __future__ import annotations

import hashlib
import json
import socket
from pathlib import Path

STATE_DIR = Path("/var/lib/ung-wave")
IDENTITY_FILE = STATE_DIR / "device_identity.json"


def _machine_material() -> str:
    candidates = [Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")]
    for path in candidates:
        try:
            value = path.read_text().strip()
            if value:
                return value
        except OSError:
            pass
    return socket.gethostname()


def device_id() -> str:
    raw = f"UNG-WAVE|LINK256|{_machine_material()}".encode()
    digest = hashlib.sha256(raw).hexdigest().upper()
    return f"WVE-{digest[:16]}"


def identity() -> dict:
    return {
        "device_id": device_id(),
        "system": "UNG-WAVE",
        "product": "UGANET LINK256",
    }


def persist_identity() -> dict:
    data = identity()
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        IDENTITY_FILE.write_text(json.dumps(data, indent=2))
    except PermissionError:
        pass
    return data
