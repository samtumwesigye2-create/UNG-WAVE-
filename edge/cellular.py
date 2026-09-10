from __future__ import annotations

import json
import re
import subprocess


def _run(cmd: list[str], timeout: int = 30) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip(), "code": proc.returncode}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "stdout": "", "stderr": str(exc), "code": -1}


def normalize_access_technology(value: str | None) -> str:
    text = (value or "").lower().replace("_", "-")
    if any(token in text for token in ("5gnr", "5g-nr", "5g nr", "nr5g", "nr")):
        return "5g"
    if "lte" in text or "4g" in text:
        return "lte"
    if "umts" in text or "hspa" in text or "3g" in text:
        return "3g"
    if "gsm" in text or "edge" in text or "2g" in text:
        return "2g"
    return "unknown"


def parse_modem_list(text: str) -> list[dict]:
    rows: list[dict] = []
    pattern = re.compile(r"(?P<path>/org/freedesktop/ModemManager1/Modem/(?P<id>\d+))\s+(?P<label>.+)$")
    for raw in text.splitlines():
        line = raw.strip()
        match = pattern.search(line)
        if match:
            rows.append({"id": match.group("id"), "path": match.group("path"), "label": match.group("label").strip()})
    return rows


def list_modems() -> list[dict]:
    result = _run(["mmcli", "-L"])
    if not result["ok"]:
        return []
    return parse_modem_list(result["stdout"])


def _flatten_strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_flatten_strings(item))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_flatten_strings(item))
        return out
    return []


def modem_status(modem_id: str) -> dict:
    result = _run(["mmcli", "-m", str(modem_id), "--output-json"])
    if not result["ok"]:
        return {"ok": False, "modem_id": str(modem_id), "error": result["stderr"] or result["stdout"]}
    try:
        data = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return {"ok": False, "modem_id": str(modem_id), "error": "invalid mmcli JSON response"}

    strings = _flatten_strings(data)
    tech_text = ", ".join(strings)
    technology = normalize_access_technology(tech_text)
    return {
        "ok": True,
        "modem_id": str(modem_id),
        "technology": technology,
        "raw": data,
    }


def connect(modem_id: str, apn: str | None = None) -> dict:
    properties = []
    if apn:
        properties.append(f"apn={apn}")
    value = ",".join(properties)
    cmd = ["mmcli", "-m", str(modem_id), f"--simple-connect={value}"]
    result = _run(cmd)
    return {
        "ok": result["ok"],
        "modem_id": str(modem_id),
        "message": result["stdout"] or result["stderr"],
    }


def disconnect(modem_id: str) -> dict:
    result = _run(["mmcli", "-m", str(modem_id), "--simple-disconnect"])
    return {
        "ok": result["ok"],
        "modem_id": str(modem_id),
        "message": result["stdout"] or result["stderr"],
    }
