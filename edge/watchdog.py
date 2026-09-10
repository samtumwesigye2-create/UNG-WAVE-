from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from edge.radio import discover_radios
from edge.router import assign_roles, start_router
from edge.uplink import active_connections, connectivity_check

STATE_DIR = Path('/var/lib/ung-wave')
CONFIG_PATH = STATE_DIR / 'router.json'

_lock = threading.Lock()
_thread: threading.Thread | None = None
_stop = threading.Event()
_state: dict = {
    'running': False,
    'last_check': None,
    'last_action': None,
    'failures': 0,
    'last_error': None,
}


def save_router_config(config: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def load_router_config() -> dict | None:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def status() -> dict:
    with _lock:
        return dict(_state)


def _set(**values) -> None:
    with _lock:
        _state.update(values)


def _loop(interval: int) -> None:
    _set(running=True)
    try:
        while not _stop.wait(interval):
            now = int(time.time())
            _set(last_check=now)

            internet = connectivity_check()
            config = load_router_config()
            radios = discover_radios()
            roles = assign_roles()

            if not config:
                _set(last_error='router config not saved')
                continue

            if not roles.get('ok'):
                _set(last_error='required Wi-Fi radios unavailable')
                continue

            uplink = config.get('uplink') or roles['uplink']
            ap_interface = config.get('ap_interface') or roles['ap']

            if internet.get('ok'):
                _set(failures=0, last_error=None)
                continue

            failures = status()['failures'] + 1
            _set(failures=failures, last_error='internet connectivity lost')

            # Avoid flapping: require two consecutive failed checks.
            if failures < 2:
                continue

            # NetworkManager is expected to autoconnect the saved uplink.
            # If the AP/routing path is gone, rebuild it from persisted config.
            result = start_router(
                uplink=uplink,
                ap_interface=ap_interface,
                ssid=config['ssid'],
                password=config['password'],
            )
            _set(
                last_action='router_restart',
                last_error=None if result.get('ok') else str(result),
                failures=0 if result.get('ok') else failures,
            )
    finally:
        _set(running=False)


def start(interval: int = 15) -> dict:
    global _thread
    if _thread and _thread.is_alive():
        return {'ok': True, 'status': 'already_running', 'watchdog': status()}

    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(interval,), daemon=True, name='ung-wave-watchdog')
    _thread.start()
    return {'ok': True, 'status': 'started', 'interval_seconds': interval}


def stop() -> dict:
    _stop.set()
    return {'ok': True, 'status': 'stopping'}
