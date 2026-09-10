from edge import wan


def test_select_preferred_prefers_5g_then_lte():
    candidates = [
        {"kind": "wifi", "interface": "wlan0", "online": True},
        {"kind": "ethernet", "interface": "eth0", "online": True},
        {"kind": "lte", "interface": "wwan0", "online": True},
        {"kind": "5g", "interface": "wwan1", "online": True},
    ]
    assert wan.select_preferred(candidates)["interface"] == "wwan1"


def test_select_preferred_prefers_satellite_over_lte():
    candidates = [
        {"kind": "lte", "interface": "wwan0", "online": True},
        {"kind": "satellite", "interface": "eth0", "online": True},
    ]
    assert wan.select_preferred(candidates)["kind"] == "satellite"


def test_select_preferred_falls_back_when_5g_offline():
    candidates = [
        {"kind": "5g", "interface": "wwan0", "online": False},
        {"kind": "lte", "interface": "wwan0", "online": True},
        {"kind": "ethernet", "interface": "eth0", "online": True},
    ]
    assert wan.select_preferred(candidates)["kind"] == "lte"


def test_select_preferred_returns_none_without_online_candidate():
    assert wan.select_preferred([{"kind": "5g", "interface": "wwan0", "online": False}]) is None


def test_configured_starlink_connections_are_casefolded(monkeypatch):
    monkeypatch.setenv("WAVE_STARLINK_CONNECTIONS", " Starlink , Remote SAT ")
    assert wan.configured_starlink_connections() == {"starlink", "remote sat"}


def test_classify_starlink_ethernet_profile_as_satellite():
    result = wan.classify_connection(
        {"name": "Starlink", "type": "ethernet", "device": "eth0"},
        {"starlink"},
    )
    assert result == {
        "kind": "satellite",
        "provider": "starlink",
        "interface": "eth0",
        "online": True,
        "connection": "Starlink",
    }


def test_classify_unknown_ethernet_as_ethernet():
    result = wan.classify_connection(
        {"name": "Office WAN", "type": "802-3-ethernet", "device": "eth0"},
        {"starlink"},
    )
    assert result["kind"] == "ethernet"
    assert result["connection"] == "Office WAN"


def test_connection_candidates_exclude_disconnected_cellular(monkeypatch):
    monkeypatch.setattr(wan, "list_modems", lambda: [{"id": "0", "label": "RM520N"}])
    monkeypatch.setattr(wan, "modem_status", lambda modem_id: {"ok": True, "technology": "5g", "connected": False})
    monkeypatch.setattr(wan, "active_connections", lambda: [])

    assert wan._connection_candidates() == []


def test_connection_candidates_include_connected_cellular(monkeypatch):
    monkeypatch.setattr(wan, "list_modems", lambda: [{"id": "0", "label": "RM520N"}])
    monkeypatch.setattr(wan, "modem_status", lambda modem_id: {"ok": True, "technology": "5g", "connected": True})
    monkeypatch.setattr(wan, "active_connections", lambda: [])

    rows = wan._connection_candidates()

    assert rows[0]["kind"] == "5g"
    assert rows[0]["online"] is True


def test_connection_candidates_classify_configured_starlink(monkeypatch):
    monkeypatch.setenv("WAVE_STARLINK_CONNECTIONS", "Starlink")
    monkeypatch.setattr(wan, "list_modems", lambda: [])
    monkeypatch.setattr(
        wan,
        "active_connections",
        lambda: [{"name": "Starlink", "type": "ethernet", "device": "eth1"}],
    )

    rows = wan._connection_candidates()

    assert rows[0]["kind"] == "satellite"
    assert rows[0]["provider"] == "starlink"
    assert rows[0]["interface"] == "eth1"


def test_status_reports_new_priority_order(monkeypatch):
    monkeypatch.setattr(wan, "_connection_candidates", lambda: [])
    result = wan.status()
    assert result["priority"] == ["5g", "satellite", "lte", "ethernet", "wifi"]
    assert result["mode"] == "local_only"
