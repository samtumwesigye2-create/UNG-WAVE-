# UNG-WAVE

**Wireless Access & Virtualized Edge**

UNG-WAVE is the control and networking platform for the **UGANET LINK256** portable autonomous Wi-Fi gateway. External Wi-Fi is an optional backup uplink; LINK256 is designed to provide its own UGANET Wi-Fi to customers and use cellular/Ethernet/other WAN backhaul as available.

## LINK256 software stack

Current implementation provides:

- network-interface and Wi-Fi radio discovery
- autonomous gateway/AP role selection
- optional upstream Wi-Fi scanning and connection control
- UGANET access point control
- DHCP and DNS service
- IPv4 forwarding and NAT/firewall rules
- persistent device/router state
- automatic connectivity watchdog and recovery
- stable per-device WVE identity
- signed subscription entitlements
- subscription enforcement with renewal-only walled garden
- background billing/entitlement synchronization
- local captive renewal portal
- hosted checkout handoff to the WAVE control plane
- automatic Internet restoration after a verified renewal
- hardware health reporting
- REST management API
- systemd boot service
- Raspberry Pi prototype installer and acceptance test

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
- `WAVE_RENEWAL_ALLOWED_HOSTS` — comma-separated HTTPS hostnames reachable while service is expired. Include the WAVE control-plane host and all payment-host dependencies required by the configured provider.

Stripe deployments normally need payment-host entries such as `checkout.stripe.com` and `js.stripe.com`; validate the final allowlist against the production Stripe checkout flow before launch.

## Management endpoints

Management API listens on port `8256`.

Useful endpoints:

- `/health`
- `/portal`
- `/api/v1/portal/status`
- `/api/v1/portal/checkout`
- `/api/v1/device`
- `/api/v1/device/identity`
- `/api/v1/plans`
- `/api/v1/radios`
- `/api/v1/uplink/status`
- `/api/v1/router/roles`
- `/api/v1/subscription/status`
- `/api/v1/subscription/sync`
- `/api/v1/billing-sync/status`
- `/api/v1/watchdog/status`

## Prototype deployment

The Raspberry Pi remains the prototype platform. Do not run the current installer over a remote-only Wi-Fi/SSH session until its network-manager preflight/rollback hardening is completed; changing the host network manager can interrupt remote connectivity.

## Hardware target

Prototype: Raspberry Pi / Linux

Product family: UGANET

Hardware model: LINK256
