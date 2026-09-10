#!/usr/bin/env bash
set -u

BASE="http://127.0.0.1:8256"
PASS=0
FAIL=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS  $name"
    PASS=$((PASS+1))
  else
    echo "FAIL  $name"
    FAIL=$((FAIL+1))
  fi
}

echo "UNG-WAVE / UGANET LINK256 — Raspberry Pi Acceptance"
echo
check "ung-wave service active" systemctl is-active --quiet ung-wave.service
check "NetworkManager active" systemctl is-active --quiet NetworkManager
check "iw installed" command -v iw
check "hostapd installed" command -v hostapd
check "dnsmasq installed" command -v dnsmasq
check "iptables installed" command -v iptables
check "API health" curl --fail --silent "$BASE/health"
check "device discovery" curl --fail --silent "$BASE/api/v1/device"
check "radio discovery" curl --fail --silent "$BASE/api/v1/radios"
check "watchdog status" curl --fail --silent "$BASE/api/v1/watchdog/status"

echo
echo "Detected Wi-Fi interfaces:"
iw dev 2>/dev/null | awk '/Interface/ {print "  - "$2}' || true

echo
echo "IPv4 forwarding: $(sysctl -n net.ipv4.ip_forward 2>/dev/null || echo unknown)"
echo "Result: $PASS passed / $FAIL failed"

[ "$FAIL" -eq 0 ]
