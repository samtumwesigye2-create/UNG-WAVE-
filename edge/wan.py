from __future__ import annotations

import os

from edge.cellular import list_modems, modem_status
from edge.uplink import active_connections

PRIORITY = {
    "5g": 500,
    "satellite": 450,
    "lte": 400,
    "ethernet": 300,
    "wifi": 100,
}


def configured_starlink_connections() -> set[str]:
    raw = os.getenv("WAVE_STARLINK_CONNECTIONS", "")
    return {item.strip().casefold() for item in raw.split(",") if item.strip()}


def classify_connection(connection: dict, starlink_connections: set[str] | None = None) -> dict | None:
    connection_type = str(connection.get("type", "")).lower()
    device = connection.get("device")
    name = str(connection.get("name") or "")
    if not device:
        return None

    if connection_type in {"ethernet", "802-3-ethernet"}:
        configured = starlink_connections if starlink_connections is not None else configured_starlink_connections()
        if name.casefold() in configured:
            return {
                "kind": "satellite",
                "provider": "starlink",
                "interface": device,
                "online": True,
                "connection": name,
            }
        kind = "ethernet"
    elif connection_type in {"wifi", "802-11-wireless"}:
        kind = "wifi"
    else:
        return None

    return {"kind": kind, "interface": device, "online": True, "connection": name or None}


def select_preferred(candidates: list[dict]) -> dict | None:
    online = [item for item in candidates if item.get("online")]
    if not online:
        return None
    return max(online, key=lambda item: PRIORITY.get(str(item.get("kind", "")).lower(), 0))


def _connection_candidates() -> list[dict]:
    candidates: list[dict] = []

    for modem in list_modems():
        state = modem_status(modem["id"])
        if not state.get("ok") or state.get("connected") is not True:
            continue
        technology = state.get("technology", "unknown")
        if technology in {"5g", "lte"}:
            candidates.append({
                "kind": technology,
                "interface": f"modem:{modem['id']}",
                "online": True,
                "modem_id": modem["id"],
                "label": modem.get("label"),
            })

    starlink_connections = configured_starlink_connections()
    for connection in active_connections():
        candidate = classify_connection(connection, starlink_connections)
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def status() -> dict:
    candidates = _connection_candidates()
    preferred = select_preferred(candidates)
    return {
        "preferred": preferred,
        "candidates": candidates,
        "priority": ["5g", "satellite", "lte", "ethernet", "wifi"],
        "mode": "online" if preferred else "local_only",
    }
