from unittest.mock import patch


def test_expired_subscription_allows_only_resolved_renewal_hosts_before_reject():
    from edge import subscription

    commands = []

    def fake_run(cmd):
        commands.append(cmd)
        return {"ok": True, "code": 0, "stdout": "", "stderr": ""}

    with patch.object(subscription, "load", return_value={"active": False, "reason": "expired"}), \
         patch.object(subscription, "_run", side_effect=fake_run), \
         patch.object(subscription, "renewal_ips", return_value={"203.0.113.10"}):
        result = subscription.enforce("wwan0", "wlan0")

    assert result["internet_access"] is False
    accept = [cmd for cmd in commands if "203.0.113.10" in cmd and "ACCEPT" in cmd]
    reject = [cmd for cmd in commands if "REJECT" in cmd]
    assert accept
    assert reject
    assert commands.index(accept[0]) < commands.index(reject[0])


def test_active_subscription_does_not_need_walled_garden_resolution():
    from edge import subscription

    with patch.object(subscription, "load", return_value={"active": True, "reason": "active"}), \
         patch.object(subscription, "renewal_ips") as resolver, \
         patch.object(subscription, "_run", return_value={"ok": True, "code": 0, "stdout": "", "stderr": ""}):
        result = subscription.enforce("wwan0", "wlan0")

    assert result["internet_access"] is True
    resolver.assert_not_called()
