import json
from unittest.mock import patch

import pytest


def test_portal_status_exposes_device_plans_and_subscription():
    from edge import portal

    with patch.object(portal, "identity", return_value={"device_id": "WVE-TEST123", "model": "UGANET LINK256"}), \
         patch.object(portal, "list_plans", return_value=[{"id": "wave-basic", "name": "WAVE Basic"}]), \
         patch.object(portal, "subscription_status", return_value={"active": False, "reason": "expired"}), \
         patch.object(portal, "control_url", return_value="https://control.example"):
        state = portal.portal_status()

    assert state["device"]["device_id"] == "WVE-TEST123"
    assert state["subscription"]["active"] is False
    assert state["checkout_available"] is True
    assert state["plans"][0]["id"] == "wave-basic"


def test_create_checkout_rejects_unknown_plan():
    from edge import portal

    with patch.object(portal, "list_plans", return_value=[{"id": "wave-basic"}]):
        with pytest.raises(ValueError, match="unknown plan"):
            portal.create_checkout("not-a-plan")


def test_create_checkout_calls_control_plane():
    from edge import portal

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self):
            return json.dumps({"ok": True, "checkout_url": "https://pay.example/session"}).encode()

    with patch.object(portal, "list_plans", return_value=[{"id": "wave-basic"}]), \
         patch.object(portal, "identity", return_value={"device_id": "WVE-TEST123"}), \
         patch.object(portal, "control_url", return_value="https://control.example"), \
         patch("edge.portal.urllib.request.urlopen", return_value=Response()):
        result = portal.create_checkout("wave-basic")

    assert result["checkout_url"] == "https://pay.example/session"


def test_render_portal_contains_renewal_copy_when_expired():
    from edge import portal

    with patch.object(portal, "portal_status", return_value={
        "device": {"device_id": "WVE-TEST123"},
        "subscription": {"active": False, "reason": "expired", "plan": "wave-basic"},
        "plans": [{"id": "wave-basic", "name": "WAVE Basic", "max_devices": 5, "speed_profile": "standard"}],
        "checkout_available": True,
    }):
        html = portal.render_portal()

    assert "Renew service" in html
    assert "WVE-TEST123" in html
    assert "WAVE Basic" in html
