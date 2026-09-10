from edge import cellular


def test_normalize_access_technology_prefers_5g():
    assert cellular.normalize_access_technology("5gnr, lte") == "5g"
    assert cellular.normalize_access_technology("lte") == "lte"


def test_parse_modem_list():
    text = "/org/freedesktop/ModemManager1/Modem/0 [Quectel] RM520N-GL\n"
    rows = cellular.parse_modem_list(text)
    assert rows == [{"id": "0", "path": "/org/freedesktop/ModemManager1/Modem/0", "label": "[Quectel] RM520N-GL"}]


def test_connect_command_uses_simple_connect(monkeypatch):
    calls = []
    monkeypatch.setattr(cellular, "_run", lambda cmd, timeout=30: calls.append(cmd) or {"ok": True, "stdout": "success", "stderr": ""})
    result = cellular.connect("0", apn="internet")
    assert result["ok"] is True
    assert calls[-1] == ["mmcli", "-m", "0", "--simple-connect=apn=internet"]


def test_modem_status_reports_connected_state(monkeypatch):
    payload = '{"modem.generic.state":"connected","modem.generic.access-technologies":"5gnr, lte"}'
    monkeypatch.setattr(cellular, "_run", lambda cmd, timeout=30: {"ok": True, "stdout": payload, "stderr": "", "code": 0})

    result = cellular.modem_status("0")

    assert result["state"] == "connected"
    assert result["connected"] is True
    assert result["technology"] == "5g"


def test_modem_status_registered_is_not_connected(monkeypatch):
    payload = '{"modem.generic.state":"registered","modem.generic.access-technologies":"lte"}'
    monkeypatch.setattr(cellular, "_run", lambda cmd, timeout=30: {"ok": True, "stdout": payload, "stderr": "", "code": 0})

    result = cellular.modem_status("0")

    assert result["state"] == "registered"
    assert result["connected"] is False


def test_modem_status_missing_state_is_not_connected(monkeypatch):
    payload = '{"modem.generic.access-technologies":"lte"}'
    monkeypatch.setattr(cellular, "_run", lambda cmd, timeout=30: {"ok": True, "stdout": payload, "stderr": "", "code": 0})

    result = cellular.modem_status("0")

    assert result["state"] == "unknown"
    assert result["connected"] is False
