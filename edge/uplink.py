from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""


def run(cmd: list[str], timeout: int = 20) -> CommandResult:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return CommandResult(proc.returncode == 0, proc.stdout.strip(), proc.stderr.strip())
    except FileNotFoundError as exc:
        return CommandResult(False, stderr=str(exc))
    except subprocess.TimeoutExpired:
        return CommandResult(False, stderr="command timed out")


def connect_wifi(interface: str, ssid: str, password: str | None = None) -> dict:
    cmd = ["nmcli", "device", "wifi", "connect", ssid, "ifname", interface]
    if password:
        cmd += ["password", password]
    result = run(cmd, timeout=30)
    return {
        "ok": result.ok,
        "interface": interface,
        "ssid": ssid,
        "message": result.stdout or result.stderr,
    }


def disconnect(interface: str) -> dict:
    result = run(["nmcli", "device", "disconnect", interface])
    return {
        "ok": result.ok,
        "interface": interface,
        "message": result.stdout or result.stderr,
    }


def connectivity_check(host: str = "1.1.1.1", port: int = 53, timeout: float = 3.0) -> dict:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"online": True, "target": f"{host}:{port}"}
    except OSError as exc:
        return {"online": False, "target": f"{host}:{port}", "error": str(exc)}


def active_connections() -> list[dict]:
    result = run(["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"])
    if not result.ok:
        return []
    rows = []
    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3:
            rows.append({"name": parts[0], "type": parts[1], "device": parts[2]})
    return rows
