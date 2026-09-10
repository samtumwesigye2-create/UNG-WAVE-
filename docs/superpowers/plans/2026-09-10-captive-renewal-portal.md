# Captive Renewal Portal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local LINK256 renewal portal that preserves Wi-Fi during subscription expiry and automatically restores Internet after verified payment.

**Architecture:** The edge portal is a local FastAPI HTML/API surface. It reads existing device identity, plans, and subscription state, delegates checkout creation to the WAVE cloud control plane, and relies on the existing billing-sync + subscription enforcement path for reactivation. Provider secrets remain cloud-side.

**Tech Stack:** Python 3, FastAPI, urllib, pytest, existing Ed25519 entitlement path, Stripe-hosted checkout.

**Spec:** `docs/superpowers/specs/2026-09-10-captive-renewal-portal.md`

## Global Constraints
- Keep UGANET Wi-Fi available when the subscription is expired.
- Never grant access based only on a local payment claim.
- Keep payment-provider secrets out of LINK256 and the public repository.
- Preserve the existing signed-entitlement enforcement path.
- No reboot should be required after successful renewal.

---

### Task 1: Portal state and checkout client

**Files:**
- Create: `tests/test_portal.py`
- Create: `edge/portal.py`

**Interfaces:**
- Consumes: `edge.device_identity.identity`, `edge.plans.list_plans`, `edge.subscription.load`, `edge.cloud_client.control_url`
- Produces: `portal_status() -> dict`, `create_checkout(plan_id: str) -> dict`, `render_portal() -> str`

- [ ] Write failing tests for expired status, plan validation, and cloud checkout failure.
- [ ] Run tests and confirm failure because `edge.portal` does not exist.
- [ ] Implement minimal portal state/client/rendering code.
- [ ] Run tests and confirm pass.

### Task 2: FastAPI portal routes

**Files:**
- Modify: `edge/main.py`
- Test: `tests/test_portal_api.py`

**Interfaces:**
- Produces: `GET /portal`, `GET /api/v1/portal/status`, `POST /api/v1/portal/checkout`

- [ ] Write failing API tests.
- [ ] Run tests and confirm missing routes.
- [ ] Add routes using `HTMLResponse` and validated plan input.
- [ ] Run tests and confirm pass.

### Task 3: Continuous post-payment unlock

**Files:**
- Modify: `edge/billing_sync.py`
- Test: `tests/test_billing_reactivation.py`

**Interfaces:**
- Existing `sync_once()` must fetch signed entitlement and immediately call subscription enforcement using saved router config.

- [ ] Add regression test proving enforcement runs after successful entitlement sync.
- [ ] Run test and verify current behavior.
- [ ] Make only changes required by the regression test.
- [ ] Run tests and confirm pass.

### Task 4: CI and documentation

**Files:**
- Create: `requirements-dev.txt`
- Create: `.github/workflows/test.yml`
- Modify: `README.md`

- [ ] Add pytest/httpx test dependencies.
- [ ] Add GitHub Actions test workflow.
- [ ] Document local portal and renewal flow.
- [ ] Run full suite in CI and review failures before completion.