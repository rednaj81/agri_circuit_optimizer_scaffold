from __future__ import annotations

from typing import Any


def add_metering_constraints(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload

    def meter_option_route_compatibility_rule(
        model: Any, route_id: str, slot: int, option_id: str
    ) -> Any:
        compatibility = payload["route_meter_compatibility"][route_id][option_id]
        return model.route_uses_meter_option[route_id, slot, option_id] <= int(
            compatibility["compatible"]
        )

    model.route_meter_option_compatibility = pyo.Constraint(
        model.ROUTE_METER_OPTION_KEYS, rule=meter_option_route_compatibility_rule
    )

    def measurement_required_direct_meter_rule(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        if not route["measurement_required"]:
            return pyo.Constraint.Skip
        return sum(
            model.route_uses_meter_option[route_id, slot, option_id]
            for slot in payload["meter_slots"]
            for option_id in payload["route_viable_meter_option_ids"][route_id]
            if not payload["meter_options"][option_id].get("is_bypass", False)
        ) == model.route_active[route_id]

    model.measurement_required_direct_meter = pyo.Constraint(
        model.ROUTES, rule=measurement_required_direct_meter_rule
    )
