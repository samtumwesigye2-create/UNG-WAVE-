from __future__ import annotations

import subprocess


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"


def enable_ipv4_forwarding() -> dict:
    rc, out, err = run(["sysctl", "-w", "net.ipv4.ip_forward=1"])
    return {"ok": rc == 0, "stdout": out, "stderr": err}


def assign_ap_address(interface: str, cidr: str = "10.25.6.1/24") -> dict:
    run(["ip", "addr", "flush", "dev", interface])
    rc, out, err = run(["ip", "addr", "add", cidr, "dev", interface])
    if rc == 0:
        run(["ip", "link", "set", interface, "up"])
    return {"ok": rc == 0, "stdout": out, "stderr": err, "interface": interface, "cidr": cidr}


def configure_nat(uplink: str, lan: str) -> dict:
    enable_ipv4_forwarding()
    cmds = [
        ["iptables", "-t", "nat", "-C", "POSTROUTING", "-o", uplink, "-j", "MASQUERADE"],
        ["iptables", "-C", "FORWARD", "-i", lan, "-o", uplink, "-j", "ACCEPT"],
        ["iptables", "-C", "FORWARD", "-i", uplink, "-o", lan, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
    ]
    adds = [
        ["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", uplink, "-j", "MASQUERADE"],
        ["iptables", "-A", "FORWARD", "-i", lan, "-o", uplink, "-j", "ACCEPT"],
        ["iptables", "-A", "FORWARD", "-i", uplink, "-o", lan, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"],
    ]
    errors = []
    for check, add in zip(cmds, adds):
        rc, _, _ = run(check)
        if rc != 0:
            rc2, _, err2 = run(add)
            if rc2 != 0:
                errors.append(err2)
    return {"ok": not errors, "uplink": uplink, "lan": lan, "errors": errors}


def start_dnsmasq(interface: str) -> dict:
    cmd = [
        "dnsmasq", "--interface=" + interface, "--bind-interfaces",
        "--dhcp-range=10.25.6.20,10.25.6.200,255.255.255.0,12h",
        "--dhcp-option=3,10.25.6.1", "--dhcp-option=6,10.25.6.1",
        "--pid-file=/run/ung-wave-dnsmasq.pid",
    ]
    rc, out, err = run(cmd)
    return {"ok": rc == 0, "stdout": out, "stderr": err}


def stop_dnsmasq() -> None:
    run(["pkill", "-F", "/run/ung-wave-dnsmasq.pid"])
