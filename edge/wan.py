from __future__ import annotations

from edge.cellular import list_modems, modem_status
from edge.uplink import active_connections

PRIORITY = {
    "5g": 500,
    "lte": 400,
    "ethernet": 300,
    "satellite": 200,
    "wifi": 100,
}


def select_preferred(candidates: list[dict]) -> dict | None:
    online = [item for item in candidates if item.get("online")]
    if not online:
        return None
    return max(online, key=lambda item: PRIORITY.get(str(item.get("kind", "")).lower(), 0))


def _connection_candidates() -> list[dict]:
    candidates: list[dict] = []

    for modem in list_modems():
        state = modem_status(modem["id"])
        if not state.get("ok"):
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

    for connection in active_connections():
        connection_type = str(connection.get("type", "")).lower()
        device = connection.get("device")
        if not device:
            continue
        if connection_type in {"ethernet", "802-3-ethernet"}:
            kind = "ethernet"
        elif connection_type in {"wifi", "802-11-wireless"}:
            kind = "wifi"
        else:
            continue
        candidates.append({"kind": kind, "interface": device, "online": True, "connection": connection.get("name")})

    return candidates


def status() -> dict:
    candidates = _connection_candidates()
    preferred = select_preferred(candidates)
    return {
        "preferred": preferred,
        "candidates": candidates,
        "priority": ["5g", "lte", "ethernet", "satellite", "wifi"],
        "mode": "online" if preferred else "local_only",
    }
