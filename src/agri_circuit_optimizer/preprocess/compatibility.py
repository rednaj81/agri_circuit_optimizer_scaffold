from __future__ import annotations

from typing import Any, Dict, Iterable, List


def check_system_diameter_compatibility(option: Dict[str, Any], system_class: str) -> bool:
    """Return True when an option is compatible with the chosen system diameter class."""
    return option.get("sys_diameter_class") in {system_class, None, "none"}


def split_encoded_values(raw_value: Any) -> List[str]:
    if raw_value is None:
        return []
    text = str(raw_value).strip()
    if not text:
        return []
    return [chunk.strip() for chunk in text.split("|") if chunk.strip()]


def component_matches_diameter(component: Dict[str, Any], allowed_classes: Iterable[str]) -> bool:
    return str(component.get("sys_diameter_class", "")).strip() in set(allowed_classes)


def option_supports_flow(option: Dict[str, Any], required_flow_lpm: float) -> bool:
    return float(option.get("q_max_lpm", 0.0)) >= float(required_flow_lpm)


def meter_option_allowed_for_route(route: Dict[str, Any], meter_option: Dict[str, Any]) -> bool:
    if bool(route.get("measurement_required", False)) and bool(meter_option.get("is_bypass", False)):
        return False
    return option_supports_flow(meter_option, float(route.get("q_min_delivered_lpm", 0.0)))


def route_respects_frozen_rules(source: str, sink: str) -> bool:
    if sink == "W":
        return False
    if source == "S":
        return False
    return True
