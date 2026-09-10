from __future__ import annotations

PLANS = {
    "wave-basic": {
        "name": "WAVE Basic",
        "billing_period_days": 30,
        "max_devices": 5,
        "speed_profile": "standard",
    },
    "wave-plus": {
        "name": "WAVE Plus",
        "billing_period_days": 30,
        "max_devices": 10,
        "speed_profile": "priority",
    },
    "wave-pro": {
        "name": "WAVE Pro",
        "billing_period_days": 30,
        "max_devices": 25,
        "speed_profile": "business",
    },
}


def list_plans() -> list[dict]:
    return [{"id": key, **value} for key, value in PLANS.items()]


def get_plan(plan_id: str) -> dict | None:
    value = PLANS.get(plan_id)
    return {"id": plan_id, **value} if value else None
