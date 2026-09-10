#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/samtumwesigye2-create/UNG-WAVE-.git"
INSTALL_DIR="/opt/ung-wave"
SERVICE="ung-wave.service"

echo "[UNG-WAVE] Installing UGANET LINK256..."
if [ "${EUID}" -ne 0 ]; then
  echo "Run with sudo: sudo bash deploy/install-pi.sh"
  exit 1
fi

NM_WAS_ACTIVE=0
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
  NM_WAS_ACTIVE=1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git python3 python3-venv python3-pip \
  network-manager modemmanager usb-modeswitch \
  iw hostapd dnsmasq iptables iproute2 curl

# Avoid silently replacing the host's active networking stack during a remote install.
# Existing NetworkManager systems continue normally. A deliberate conversion requires
# UNG_WAVE_ALLOW_NETWORK_SWITCH=1 and should be performed from a local console.
if [ "$NM_WAS_ACTIVE" -eq 1 ]; then
  systemctl unmask NetworkManager || true
  systemctl enable --now NetworkManager
elif [ "${UNG_WAVE_ALLOW_NETWORK_SWITCH:-0}" = "1" ]; then
  systemctl unmask NetworkManager || true
  systemctl enable --now NetworkManager
else
  echo "[UNG-WAVE] NetworkManager was not active; leaving current host networking unchanged."
  echo "[UNG-WAVE] Run from a local console with UNG_WAVE_ALLOW_NETWORK_SWITCH=1 if conversion is required."
fi

# ModemManager is independent of the customer Wi-Fi AP and manages supported 4G/5G modems.
systemctl unmask ModemManager 2>/dev/null || true
systemctl enable --now ModemManager

# UNG-WAVE launches its own hostapd/dnsmasq instances.
systemctl disable --now hostapd 2>/dev/null || true
systemctl disable --now dnsmasq 2>/dev/null || true

if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  rm -rf "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

install -d -m 700 /var/lib/ung-wave
install -m 644 "$INSTALL_DIR/deploy/ung-wave.service" /etc/systemd/system/ung-wave.service

cat >/etc/sysctl.d/99-ung-wave.conf <<'EOF'
net.ipv4.ip_forward=1
EOF
sysctl --system >/dev/null

systemctl daemon-reload
systemctl enable --now "$SERVICE"
sleep 2

echo
echo "[UNG-WAVE] Service state:"
systemctl --no-pager --full status "$SERVICE" || true

echo
echo "[UNG-WAVE] Hardware/API acceptance:"
curl --fail --silent http://127.0.0.1:8256/health && echo
curl --fail --silent http://127.0.0.1:8256/api/v1/radios && echo
curl --fail --silent http://127.0.0.1:8256/api/v1/cellular/modems && echo
curl --fail --silent http://127.0.0.1:8256/api/v1/wan/status && echo

echo
echo "[UNG-WAVE] LINK256 installation complete."
