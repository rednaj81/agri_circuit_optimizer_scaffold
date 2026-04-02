from __future__ import annotations

from typing import Any, Dict


def meter_can_serve_route(route: Dict[str, Any], meter: Dict[str, Any]) -> bool:
    if bool(route.get("measurement_required", 0)) and bool(meter.get("is_bypass", False)):
        return False
    q_req = float(route.get("q_min_delivered_lpm", 0))
    dose_min = float(route.get("dose_min_l", 0))
    err_max = float(route.get("dose_error_max_pct", 100))
    q_ok = float(meter.get("q_max_lpm", 1e12)) >= q_req
    dose_ok = float(meter.get("meter_batch_min_l") or 0) <= dose_min
    err_ok = float(meter.get("meter_error_pct") or 0) <= err_max
    return q_ok and dose_ok and err_ok


def pump_can_serve_route(route: Dict[str, Any], pump: Dict[str, Any]) -> bool:
    q_req = float(route.get("q_min_delivered_lpm", 0))
    return float(pump.get("q_max_lpm", 0)) >= q_req
