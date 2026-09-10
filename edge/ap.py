from __future__ import annotations

import subprocess
from pathlib import Path

HOSTAPD_CONF = Path("/run/ung-wave-hostapd.conf")
HOSTAPD_PID = Path("/run/ung-wave-hostapd.pid")


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"


def start_ap(interface: str, ssid: str = "UGANET-LINK256", password: str = "UGANET256") -> dict:
    if len(password) < 8 or len(password) > 63:
        return {"ok": False, "error": "AP password must be 8-63 characters"}

    conf = f"""interface={interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
wmm_enabled=1
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
wpa_passphrase={password}
"""
    HOSTAPD_CONF.write_text(conf)
    rc, out, err = run(["hostapd", "-B", "-P", str(HOSTAPD_PID), str(HOSTAPD_CONF)])
    return {"ok": rc == 0, "interface": interface, "ssid": ssid, "stdout": out, "stderr": err}


def stop_ap() -> dict:
    if not HOSTAPD_PID.exists():
        return {"ok": True, "status": "already_stopped"}
    rc, out, err = run(["kill", HOSTAPD_PID.read_text().strip()])
    try:
        HOSTAPD_PID.unlink()
    except OSError:
        pass
    return {"ok": rc == 0, "stdout": out, "stderr": err}
