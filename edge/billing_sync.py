from __future__ import annotations

import threading
import time

from edge.cloud_client import sync_entitlement
from edge.subscription import enforce, load
from edge.watchdog import load_router_config

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop = threading.Event()
_state = {
    "running": False,
    "last_sync": None,
    "last_result": None,
    "last_enforcement": None,
}


def _set(**values) -> None:
    with _lock:
        _state.update(values)


def status() -> dict:
    with _lock:
        return {**_state, "subscription": load()}


def sync_once() -> dict:
    result = sync_entitlement()
    _set(last_sync=int(time.time()), last_result=result)

    config = load_router_config()
    enforcement = None
    if config and config.get("uplink") and config.get("ap_interface"):
        enforcement = enforce(config["uplink"], config["ap_interface"])
        _set(last_enforcement=enforcement)

    return {"sync": result, "enforcement": enforcement, "subscription": load()}


def _loop(interval: int) -> None:
    _set(running=True)
    try:
        sync_once()
        while not _stop.wait(interval):
            sync_once()
    finally:
        _set(running=False)


def start(interval: int = 60) -> dict:
    global _thread
    if _thread and _thread.is_alive():
        return {"ok": True, "status": "already_running", "billing_sync": status()}
    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(interval,), daemon=True, name="ung-wave-billing-sync")
    _thread.start()
    return {"ok": True, "status": "started", "interval_seconds": interval}


def stop() -> dict:
    _stop.set()
    return {"ok": True, "status": "stopping"}
