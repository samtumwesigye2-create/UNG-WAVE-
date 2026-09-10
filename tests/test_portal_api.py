from unittest.mock import patch

from fastapi.testclient import TestClient


def test_portal_page_and_status_routes():
    from edge.main import app

    client = TestClient(app)
    with patch("edge.main.render_portal", return_value="<html>portal</html>"), \
         patch("edge.main.portal_status", return_value={"checkout_available": True}):
        page = client.get("/portal")
        status = client.get("/api/v1/portal/status")

    assert page.status_code == 200
    assert "portal" in page.text
    assert status.status_code == 200
    assert status.json()["checkout_available"] is True


def test_portal_checkout_returns_checkout_url():
    from edge.main import app

    client = TestClient(app)
    with patch("edge.main.portal_checkout", return_value={"checkout_url": "https://pay.example/session"}):
        response = client.post("/api/v1/portal/checkout", json={"plan": "wave-basic"})

    assert response.status_code == 200
    assert response.json()["checkout_url"] == "https://pay.example/session"


def test_portal_checkout_rejects_unknown_plan():
    from edge.main import app

    client = TestClient(app)
    with patch("edge.main.portal_checkout", side_effect=ValueError("unknown plan")):
        response = client.post("/api/v1/portal/checkout", json={"plan": "bad"})

    assert response.status_code == 400
