#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

# Run against the installed production tree.
os.chdir("/opt/ung-wave")
sys.path.insert(0, "/opt/ung-wave")

from edge.router import start_router, stop_router


def main() -> int:
    # Clear any stale AP/dnsmasq state from a previous attempt.
    try:
        stop_router()
    except Exception:
        pass

    result = start_router(
        uplink="eth0",
        ap_interface="wlan0",
        ssid="UGANET-LINK256",
        password="UGANET256",
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
