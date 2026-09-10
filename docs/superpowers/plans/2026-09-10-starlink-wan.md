# Starlink WAN Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Starlink-aware WAN classification/failover and ensure cellular WAN candidates are only considered online when ModemManager reports a connected state.

**Architecture:** Extend `edge.cellular` to parse connection state from `mmcli` JSON, then extend `edge.wan` with deterministic Starlink profile classification via `WAVE_STARLINK_CONNECTIONS`. Preserve the existing WAN status API while updating priority to 5G → satellite → LTE → Ethernet → Wi-Fi.

**Tech Stack:** Python 3, FastAPI, ModemManager/mmcli, NetworkManager/nmcli, pytest.

**Spec:** `docs/superpowers/specs/2026-09-10-starlink-wan-design.md`

## Global Constraints

- Starlink terminal remains external and connects over Ethernet.
- `WAVE_STARLINK_CONNECTIONS` explicitly identifies Starlink NetworkManager profiles.
- Unknown Ethernet profiles remain ordinary Ethernet.
- Cellular modem presence alone must never imply an online WAN.
- No direct Starlink dish control or phased-array implementation.

---

### Task 1: Cellular connected-state parsing

**Files:**
- Modify: `edge/cellular.py`
- Test: `tests/test_cellular.py`

**Interfaces:**
- Produces: `modem_status(modem_id: str) -> dict` with `state: str` and `connected: bool`.

- [ ] **Step 1: Write the failing tests**

Add tests that feed representative `mmcli --output-json` payloads through the existing subprocess seam and assert that `state == 'connected'` produces `connected is True`, while `registered`, `disconnected`, or missing state produce `False`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_cellular.py`
Expected: FAIL because `modem_status()` does not yet return parsed `state`/`connected` fields.

- [ ] **Step 3: Implement minimal parsing**

Read the flattened ModemManager generic state field from the decoded JSON, normalize it to lower-case text, and return both `state` and `connected = state == 'connected'` alongside the existing technology/raw fields.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=. pytest -q tests/test_cellular.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_cellular.py edge/cellular.py
git commit -m "fix: report cellular connection state"
```

### Task 2: Starlink classification and WAN priority

**Files:**
- Modify: `edge/wan.py`
- Test: `tests/test_wan.py`

**Interfaces:**
- Produces: `configured_starlink_connections() -> set[str]`.
- Produces: `classify_connection(connection: dict, starlink_connections: set[str] | None = None) -> dict | None`.
- Preserves: `select_preferred(candidates: list[dict]) -> dict | None`.

- [ ] **Step 1: Write failing tests**

Add tests asserting:

```python
assert classify_connection(
    {"name": "Starlink", "type": "ethernet", "device": "eth0"},
    {"starlink"},
)["kind"] == "satellite"

assert classify_connection(
    {"name": "Office WAN", "type": "802-3-ethernet", "device": "eth0"},
    {"starlink"},
)["kind"] == "ethernet"

assert select_preferred([
    {"kind": "lte", "online": True},
    {"kind": "satellite", "online": True},
])["kind"] == "satellite"
```

Also test case-insensitive/whitespace-tolerant parsing of `WAVE_STARLINK_CONNECTIONS`.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_wan.py`
Expected: FAIL because Starlink helpers do not exist and satellite currently ranks below LTE.

- [ ] **Step 3: Implement minimal Starlink classification**

Add environment parsing for `WAVE_STARLINK_CONNECTIONS`, classify matching Ethernet profiles as:

```python
{
    "kind": "satellite",
    "provider": "starlink",
    "interface": device,
    "online": True,
    "connection": name,
}
```

Update priorities to `5g=500`, `satellite=450`, `lte=400`, `ethernet=300`, `wifi=100` and return the same order from `status()`.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=. pytest -q tests/test_wan.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_wan.py edge/wan.py
git commit -m "feat: add Starlink WAN classification"
```

### Task 3: Exclude disconnected cellular WANs

**Files:**
- Modify: `edge/wan.py`
- Test: `tests/test_wan.py`

**Interfaces:**
- Consumes: `modem_status(...)["connected"]` from Task 1.

- [ ] **Step 1: Write failing tests**

Monkeypatch `list_modems()` and `modem_status()` so one 5G modem returns `connected=False`; assert `_connection_candidates()` does not include it. Add a second test with `connected=True` and assert it is included.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_wan.py`
Expected: FAIL because current code marks any recognized 5G/LTE modem online.

- [ ] **Step 3: Implement minimal filtering**

Only append cellular candidates when `state.get("connected") is True` and technology is `5g` or `lte`.

- [ ] **Step 4: Run WAN tests**

Run: `PYTHONPATH=. pytest -q tests/test_wan.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_wan.py edge/wan.py
git commit -m "fix: exclude disconnected cellular WANs"
```

### Task 4: Full regression verification

**Files:**
- Modify only if a regression is exposed.

**Interfaces:**
- Verifies the existing FastAPI `/api/v1/wan/status` response remains compatible.

- [ ] **Step 1: Run complete suite**

Run: `PYTHONPATH=. pytest -q`
Expected: PASS.

- [ ] **Step 2: Verify GitHub Actions**

Confirm the workflow for the final head SHA completes successfully.

- [ ] **Step 3: Inspect WAN status behavior**

Verify status priority is exactly `['5g', 'satellite', 'lte', 'ethernet', 'wifi']` and `mode` is `local_only` when no candidates are online.

- [ ] **Step 4: Commit any necessary regression-only corrections**

If no corrections are needed, do not create an empty commit.
