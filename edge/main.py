from __future__ import annotations

import json
import platform
import socket
import subprocess
import time
from pathlib import Path

import psutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from edge.radio import connection_status, discover_radios, scan
from edge.uplink import active_connections, connect_wifi, connectivity_check, disconnect

APP_NAME = "UNG-WAVE"
MODEL = "UGANET LINK256"
VERSION = "0.2.0"
STATE_DIR = Path("/var/lib/ung-wave")
STARTED = time.time()

app = FastAPI(title=f"{APP_NAME} — {MODEL}", version=VERSION)


class WifiConnectRequest(BaseModel):
    interface: str = Field(min_length=1, max_length=32)
    ssid: str = Field(min_length=1, max_length=32)
    password: str | None = Field(default=None, min_length=8, max_length=63)


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=False).stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def wireless_interfaces() -> set[str]:
    names: set[str] = set()
    text = run(["iw", "dev"])
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Interface "):
            names.add(line.split(maxsplit=1)[1])
    return names


def interfaces() -> list[dict]:
    wifi = wireless_interfaces()
    stats = psutil.net_if_stats()
    addresses = psutil.net_if_addrs()
    result = []
    for name in sorted(stats):
        addrs = []
        for addr in addresses.get(name, []):
            family = getattr(addr.family, "name", str(addr.family))
            if family in {"AF_INET", "AF_INET6"}:
                addrs.append({"family": family, "address": addr.address})
        result.append({
            "name": name,
            "kind": "wifi" if name in wifi or name.startswith(("wl", "wlan")) else "ethernet" if name.startswith(("eth", "en")) else "other",
            "up": stats[name].isup,
            "speed_mbps": stats[name].speed,
            "addresses": addrs,
        })
    return result


def temperature_c():
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return round(int(path.read_text().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def device_state() -> dict:
    return {
        "system": APP_NAME,
        "product": MODEL,
        "version": VERSION,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "uptime_seconds": int(time.time() - STARTED),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "temperature_c": temperature_c(),
        "internet": connectivity_check(),
        "interfaces": interfaces(),
        "radios": discover_radios(),
        "active_connections": active_connections(),
    }


@app.on_event("startup")
def persist_boot_state() -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        (STATE_DIR / "last_boot.json").write_text(json.dumps(device_state(), indent=2))
    except PermissionError:
        pass


@app.get("/health")
def health():
    internet = connectivity_check()
    return {
        "status": "ready",
        "system": APP_NAME,
        "product": MODEL,
        "version": VERSION,
        "internet": internet,
    }


@app.get("/api/v1/device")
def device():
    return device_state()


@app.get("/api/v1/interfaces")
def network_interfaces():
    return {"interfaces": interfaces()}


@app.get("/api/v1/radios")
def radios():
    return {"radios": discover_radios()}


@app.get("/api/v1/radios/{interface}/status")
def radio_status(interface: str):
    return connection_status(interface)


@app.get("/api/v1/radios/{interface}/scan")
def radio_scan(interface: str):
    known = {radio["interface"] for radio in discover_radios()}
    if interface not in known:
        raise HTTPException(status_code=404, detail="wireless interface not found")
    return {"interface": interface, "networks": scan(interface)}


@app.post("/api/v1/uplink/wifi/connect")
def wifi_connect(request: WifiConnectRequest):
    known = {radio["interface"] for radio in discover_radios()}
    if request.interface not in known:
        raise HTTPException(status_code=404, detail="wireless interface not found")
    result = connect_wifi(request.interface, request.ssid, request.password)
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result)
    return result


@app.post("/api/v1/uplink/{interface}/disconnect")
def uplink_disconnect(interface: str):
    result = disconnect(interface)
    if not result["ok"]:
        raise HTTPException(status_code=502, detail=result)
    return result


@app.get("/api/v1/uplink/status")
def uplink_status():
    return {
        "internet": connectivity_check(),
        "active_connections": active_connections(),
    }
