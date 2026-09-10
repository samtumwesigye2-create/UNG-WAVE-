# UNG-WAVE

**Wireless Access & Virtualized Edge**

UNG-WAVE is the control and networking platform for the **UGANET LINK256** portable router/repeater.

## LINK256 software stack

Current implementation provides:

- network-interface and Wi-Fi radio discovery
- upstream Wi-Fi scanning and connection control
- independent uplink/AP radio roles
- UGANET access point control
- DHCP and DNS service
- IPv4 forwarding and NAT/firewall rules
- persistent device/router state
- automatic connectivity watchdog and recovery
- hardware health reporting
- REST management API
- systemd boot service
- Raspberry Pi installer and acceptance test

## Raspberry Pi installation

LINK256 repeater mode is designed for two independent Wi-Fi interfaces: one uplink radio and one UGANET AP radio.

```bash
git clone https://github.com/samtumwesigye2-create/UNG-WAVE-.git
cd UNG-WAVE-
sudo bash deploy/install-pi.sh
```

Run acceptance checks:

```bash
sudo bash /opt/ung-wave/deploy/acceptance-pi.sh
```

Management API listens on port `8256`.

Useful endpoints:

- `/health`
- `/api/v1/device`
- `/api/v1/radios`
- `/api/v1/uplink/status`
- `/api/v1/router/roles`
- `/api/v1/watchdog/status`

## Hardware target

Prototype: Raspberry Pi / Linux

Product family: UGANET

Hardware model: LINK256
