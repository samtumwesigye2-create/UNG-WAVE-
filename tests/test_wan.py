from edge import wan


def test_select_preferred_prefers_5g_then_lte():
    candidates = [
        {"kind": "wifi", "interface": "wlan0", "online": True},
        {"kind": "ethernet", "interface": "eth0", "online": True},
        {"kind": "lte", "interface": "wwan0", "online": True},
        {"kind": "5g", "interface": "wwan1", "online": True},
    ]
    assert wan.select_preferred(candidates)["interface"] == "wwan1"


def test_select_preferred_falls_back_when_5g_offline():
    candidates = [
        {"kind": "5g", "interface": "wwan0", "online": False},
        {"kind": "lte", "interface": "wwan0", "online": True},
        {"kind": "ethernet", "interface": "eth0", "online": True},
    ]
    assert wan.select_preferred(candidates)["kind"] == "lte"


def test_select_preferred_returns_none_without_online_candidate():
    assert wan.select_preferred([{"kind": "5g", "interface": "wwan0", "online": False}]) is None
