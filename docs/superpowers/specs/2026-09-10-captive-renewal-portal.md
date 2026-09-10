# UNG-WAVE Captive Renewal Portal Design

## Goal
Keep UGANET Wi-Fi available when a LINK256 subscription expires, block general Internet access, and provide a local renewal portal that lets the customer restore service without a technician or reboot.

## User flow
1. LINK256 keeps broadcasting UGANET-LINK256 regardless of subscription state.
2. When entitlement is active, forwarding works normally.
3. When entitlement is missing or expired, general WAN forwarding is rejected.
4. The customer can still reach the LINK256 local portal.
5. The portal shows device ID, subscription state, and WAVE Basic/Plus/Pro plans.
6. Selecting a plan requests a hosted checkout URL from the WAVE control plane.
7. The browser is redirected to the payment provider.
8. After the provider confirms payment, the control plane extends the device entitlement.
9. LINK256 billing sync downloads and verifies the signed entitlement and reapplies forwarding rules.
10. Internet access returns automatically without rebooting the device.

## Security
- The device never trusts a local 'paid' flag.
- Entitlements remain Ed25519 signed and bound to device_id.
- Checkout creation is performed by the cloud control plane, not by exposing provider secrets on LINK256.
- Expired devices retain only local management plus a configurable renewal walled garden; general WAN remains blocked.
- No payment keys or webhook secrets are stored in the public repository or on customer-facing pages.

## Interfaces
- GET /portal: local HTML renewal/status page.
- GET /api/v1/portal/status: device, plans, entitlement and checkout availability.
- POST /api/v1/portal/checkout: request checkout for one plan and return hosted checkout URL.
- Existing billing sync is responsible for post-payment entitlement retrieval and enforcement.

## Failure behavior
If the cloud control plane or payment provider is unavailable, the local Wi-Fi and portal remain available and show a retryable service-unavailable state. The device must never grant Internet access because checkout failed.