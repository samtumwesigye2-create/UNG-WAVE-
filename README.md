# UNG-WAVE

**Wireless Access & Virtualized Edge**

UNG-WAVE is the control and networking platform for the **UGANET LINK256** portable autonomous Wi-Fi gateway. LINK256 provides its own UGANET Wi-Fi to customers and can use 5G/LTE, Ethernet, satellite, or external Wi-Fi backhaul.

## LINK256 software stack

Current implementation provides:

- autonomous UGANET access point control
- DHCP/DNS and IPv4 NAT/firewall
- 5G NR / LTE modem discovery through ModemManager
- cellular connect/disconnect and modem status APIs
- preferred WAN policy: 5G → LTE → Ethernet → satellite → Wi-Fi
- optional upstream Wi-Fi scanning and connection control
- persistent device/router state and automatic recovery
- stable per-device WVE identity
- signed subscription entitlements
- subscription enforcement with renewal-only walled garden
- background billing/entitlement synchronization
- local captive renewal portal and hosted checkout handoff
- automatic Internet restoration after verified renewal
- hardware health reporting and REST management API
- systemd boot service and Raspberry Pi prototype installer

## 5G / LTE operation

LINK256 uses ModemManager (`mmcli`) for supported USB or M.2 cellular modems. A 5G-capable modem and SIM/data plan are hardware/service requirements; software alone cannot turn an LTE-only modem into 5G hardware.

Normal cellular path:

1. LINK256 boots and keeps `UGANET-LINK256` available independently of WAN state.
2. ModemManager discovers the attached cellular modem.
3. `/api/v1/cellular/modems` lists discovered modems.
4. LINK256 can establish the data session with `/api/v1/cellular/{modem_id}/connect`.
5. The WAN selector prefers a working 5G connection; if the modem/network falls back to LTE, LTE becomes the cellular path automatically.
6. Ethernet, satellite, and external Wi-Fi remain lower-priority backup transports.
7. Subscription enforcement continues to control customer Internet forwarding regardless of which WAN is active.

APN values are runtime configuration and must not be committed to this public repository. SIM PINs, carrier passwords, private keys, and billing credentials must also remain outside source control.

### 5G management endpoints

- `/api/v1/cellular/modems`
- `/api/v1/cellular/{modem_id}/status`
- `/api/v1/cellular/{modem_id}/connect`
- `/api/v1/cellular/{modem_id}/disconnect`
- `/api/v1/wan/status`

ModemManager exposes cellular access technology including LTE and 5G-class technology information, which UNG-WAVE normalizes into the WAN selection policy.

## Subscription flow

1. Customer connects to `UGANET-LINK256`.
2. Active entitlement: normal Internet forwarding is enabled.
3. Missing/expired entitlement: UGANET Wi-Fi remains available, but general WAN forwarding is blocked.
4. Customer opens `http://10.25.6.1:8256/portal`.
5. The portal displays the device ID, subscription status, and available WAVE plans.
6. Checkout is created by the WAVE cloud control plane; payment-provider secrets never live on LINK256.
7. The payment webhook extends the device entitlement.
8. LINK256 fetches and verifies the Ed25519-signed entitlement and reapplies forwarding rules automatically.
9. Internet access returns without a reboot.

Required edge configuration:

- `WAVE_CONTROL_URL` — public HTTPS URL of the WAVE subscription control plane.
- `WAVE_ENTITLEMENT_PUBLIC_KEY` — trusted Ed25519 public key used to verify cloud-issued entitlements.
- `WAVE_RENEWAL_ALLOWED_HOSTS` — comma-separated HTTPS hostnames reachable while service is expired.

## Prototype deployment

The Raspberry Pi remains the prototype platform. The installer now installs ModemManager and `usb-modeswitch` for supported cellular hardware. It no longer silently replaces an existing non-NetworkManager networking stack; deliberate conversion requires `UNG_WAVE_ALLOW_NETWORK_SWITCH=1` from a local-console maintenance session.

## Hardware target

Prototype: Raspberry Pi / Linux

Product family: UGANET

Hardware model: LINK256

5G target: USB 3 or M.2 B-Key 5G NR modem with LTE fallback and appropriate carrier-certified antennas/SIM.
