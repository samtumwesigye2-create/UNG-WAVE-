from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass


def run(cmd: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"


@dataclass
class Radio:
    interface: str
    phy: str | None = None
    mac: str | None = None
    channel: str | None = None
    ssid: str | None = None


def discover_radios() -> list[dict]:
    rc, out, _ = run(["iw", "dev"])
    if rc != 0 or not out:
        return []

    radios: list[Radio] = []
    phy: str | None = None
    current: Radio | None = None

    for raw in out.splitlines():
        line = raw.strip()
        if line.startswith("phy#"):
            phy = line
        elif line.startswith("Interface "):
            current = Radio(interface=line.split(maxsplit=1)[1], phy=phy)
            radios.append(current)
        elif current and line.startswith("addr "):
            current.mac = line.split(maxsplit=1)[1]
        elif current and line.startswith("channel "):
            current.channel = line.split()[1]
        elif current and line.startswith("ssid "):
            current.ssid = line.split(maxsplit=1)[1]

    return [asdict(r) for r in radios]


def scan(interface: str) -> list[dict]:
    rc, out, err = run([
        "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,FREQ", "device", "wifi", "list",
        "ifname", interface, "--rescan", "yes",
    ], timeout=20)
    if rc != 0:
        return [{"error": err or "wifi scan failed"}]

    networks: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) < 4:
            continue
        ssid, signal, security, freq = parts[0], parts[1], parts[2], parts[3]
        if not ssid:
            continue
        key = (ssid, security)
        if key in seen:
            continue
        seen.add(key)
        networks.append({
            "ssid": ssid,
            "signal": int(signal) if signal.isdigit() else None,
            "security": security or "OPEN",
            "frequency_mhz": int(freq) if freq.isdigit() else None,
        })

    return sorted(networks, key=lambda n: n.get("signal") or 0, reverse=True)


def connection_status(interface: str) -> dict:
    rc, out, err = run([
        "nmcli", "-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION", "device", "show", interface
    ])
    if rc != 0:
        return {"interface": interface, "connected": False, "error": err}

    state = ""
    connection = ""
    for line in out.splitlines():
        if line.startswith("GENERAL.STATE:"):
            state = line.split(":", 1)[1]
        elif line.startswith("GENERAL.CONNECTION:"):
            connection = line.split(":", 1)[1]

    return {
        "interface": interface,
        "connected": state.startswith("100"),
        "state": state,
        "connection": connection,
    }
