from fastapi.testclient import TestClient

from edge import main


client = TestClient(main.app)


def test_cellular_modems_endpoint(monkeypatch):
    monkeypatch.setattr(main, "list_cellular_modems", lambda: [{"id": "0", "label": "5G modem"}])
    response = client.get("/api/v1/cellular/modems")
    assert response.status_code == 200
    assert response.json()["modems"][0]["id"] == "0"


def test_cellular_status_endpoint(monkeypatch):
    monkeypatch.setattr(main, "cellular_modem_status", lambda modem_id: {"ok": True, "modem_id": modem_id, "technology": "5g"})
    response = client.get("/api/v1/cellular/0/status")
    assert response.status_code == 200
    assert response.json()["technology"] == "5g"


def test_cellular_connect_endpoint(monkeypatch):
    monkeypatch.setattr(main, "cellular_connect", lambda modem_id, apn=None: {"ok": True, "modem_id": modem_id, "apn_used": bool(apn)})
    response = client.post("/api/v1/cellular/0/connect", json={"apn": "internet"})
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_wan_status_endpoint(monkeypatch):
    monkeypatch.setattr(main, "wan_status", lambda: {"preferred": {"kind": "5g", "interface": "modem:0"}, "mode": "online"})
    response = client.get("/api/v1/wan/status")
    assert response.status_code == 200
    assert response.json()["preferred"]["kind"] == "5g"
