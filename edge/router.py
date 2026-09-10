from __future__ import annotations

from edge.ap import start_ap, stop_ap
from edge.network import assign_ap_address, configure_nat, start_dnsmasq, stop_dnsmasq
from edge.radio import discover_radios
from edge.subscription import enforce as enforce_subscription


def assign_roles() -> dict:
    radios = [r["interface"] for r in discover_radios()]
    if not radios:
        return {"ok": False, "error": "no Wi-Fi interface detected", "radios": radios}
    if len(radios) == 1:
        return {"ok": True, "mode": "gateway", "uplink": None, "ap": radios[0], "radios": radios}
    return {"ok": True, "mode": "gateway+wifi-backup", "uplink": radios[0], "ap": radios[1], "radios": radios}


def start_router(uplink: str, ap_interface: str, ssid: str, password: str) -> dict:
    addr = assign_ap_address(ap_interface)
    if not addr["ok"]:
        return {"ok": False, "stage": "address", "detail": addr}

    ap = start_ap(ap_interface, ssid, password)
    if not ap["ok"]:
        return {"ok": False, "stage": "access_point", "detail": ap}

    dhcp = start_dnsmasq(ap_interface)
    if not dhcp["ok"]:
        stop_ap()
        return {"ok": False, "stage": "dhcp_dns", "detail": dhcp}

    nat = configure_nat(uplink, ap_interface)
    if not nat["ok"]:
        stop_dnsmasq()
        stop_ap()
        return {"ok": False, "stage": "nat", "detail": nat}

    subscription = enforce_subscription(uplink, ap_interface)
    if not subscription["ok"]:
        stop_dnsmasq()
        stop_ap()
        return {"ok": False, "stage": "subscription_gate", "detail": subscription}

    return {
        "ok": True,
        "status": "ready" if subscription["internet_access"] else "subscription_required",
        "uplink": uplink,
        "ap_interface": ap_interface,
        "ssid": ssid,
        "gateway": "10.25.6.1",
        "dhcp_range": "10.25.6.20-10.25.6.200",
        "internet_access": subscription["internet_access"],
        "subscription": subscription["subscription"],
    }


def stop_router() -> dict:
    stop_dnsmasq()
    ap = stop_ap()
    return {"ok": ap.get("ok", False), "status": "stopped"}
