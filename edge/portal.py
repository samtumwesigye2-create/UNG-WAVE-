from __future__ import annotations

import html
import json
import urllib.error
import urllib.request

from edge.cloud_client import control_url
from edge.device_identity import identity
from edge.plans import list_plans
from edge.subscription import load as subscription_status


def portal_status() -> dict:
    return {
        "device": identity(),
        "subscription": subscription_status(),
        "plans": list_plans(),
        "checkout_available": bool(control_url()),
    }


def create_checkout(plan_id: str, timeout: int = 10) -> dict:
    plans = {plan["id"]: plan for plan in list_plans()}
    if plan_id not in plans:
        raise ValueError("unknown plan")

    base = control_url()
    if not base:
        raise RuntimeError("WAVE_CONTROL_URL is not configured")

    payload = json.dumps({
        "device_id": identity()["device_id"],
        "plan": plan_id,
        "success_url": f"{base}/renewal/success",
        "cancel_url": f"{base}/renewal/cancel",
    }).encode()
    request = urllib.request.Request(
        f"{base}/api/v1/billing/checkout",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"checkout service returned HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"checkout service unavailable: {exc}") from exc

    checkout_url = result.get("checkout_url")
    if not checkout_url:
        raise RuntimeError("checkout service did not return a checkout URL")
    return result


def render_portal() -> str:
    state = portal_status()
    device = state["device"]
    subscription = state["subscription"]
    active = bool(subscription.get("active"))

    if active:
        headline = "Service active"
        message = "Your UGANET Internet service is active."
    else:
        headline = "Renew service"
        message = "Your Internet access is paused. Renew below to reconnect automatically."

    cards = []
    for plan in state["plans"]:
        plan_id = html.escape(str(plan["id"]))
        name = html.escape(str(plan.get("name", plan_id)))
        devices = html.escape(str(plan.get("max_devices", "—")))
        speed = html.escape(str(plan.get("speed_profile", "standard")))
        button = (
            f'<button onclick="renew(\'{plan_id}\')">Choose {name}</button>'
            if state["checkout_available"]
            else '<button disabled>Payment service unavailable</button>'
        )
        cards.append(
            f'<section class="plan"><h3>{name}</h3><p>Up to {devices} devices</p>'
            f'<p>Profile: {speed}</p>{button}</section>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UNG-WAVE Service Portal</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;margin:0;background:#f4f6f8;color:#17202a}}
main{{max-width:860px;margin:auto;padding:24px}}
.hero{{background:white;border-radius:18px;padding:24px;box-shadow:0 2px 12px #0001}}
.badge{{display:inline-block;padding:6px 10px;border-radius:999px;background:#eef2f7;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:16px;margin-top:18px}}
.plan{{background:white;border-radius:16px;padding:18px;box-shadow:0 2px 12px #0001}}
button{{width:100%;padding:12px;border:0;border-radius:10px;font-weight:700;cursor:pointer}}
button:disabled{{cursor:not-allowed;opacity:.55}}
.small{{font-size:13px;color:#667085}}
#status{{margin-top:14px;font-weight:600}}
</style>
</head>
<body>
<main>
<div class="hero">
<span class="badge">UNG-WAVE · UGANET LINK256</span>
<h1>{html.escape(headline)}</h1>
<p>{html.escape(message)}</p>
<p class="small">Device: {html.escape(str(device.get('device_id', 'unknown')))}</p>
<p class="small">Current plan: {html.escape(str(subscription.get('plan') or 'none'))}</p>
<div id="status"></div>
</div>
<div class="grid">{''.join(cards)}</div>
</main>
<script>
async function renew(plan){{
  const status=document.getElementById('status');
  status.textContent='Opening secure checkout…';
  try{{
    const response=await fetch('/api/v1/portal/checkout',{{
      method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{plan}})
    }});
    const data=await response.json();
    if(!response.ok) throw new Error(data.detail || 'Unable to start checkout');
    window.location.href=data.checkout_url;
  }}catch(err){{status.textContent=String(err.message || err)}}
}}
</script>
</body>
</html>"""
