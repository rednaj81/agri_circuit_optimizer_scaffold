from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict


def build_sets_and_parameters(data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize scenario and option data into a model-friendly payload."""

    routes = data["routes"].to_dict("records")
    components = data["components"].to_dict("records")
    settings = data["settings"]

    route_ids = [route["route_id"] for route in routes]
    source_nodes = sorted(
        {
            route["source"]
            for route in routes
            if route["source"] in options["source_options"]
        }
    )
    sink_nodes = sorted(
        {
            route["sink"]
            for route in routes
            if route["sink"] in options["destination_options"]
        }
    )

    source_option_index = _index_options(options["source_options"])
    destination_option_index = _index_options(options["destination_options"])
    pump_option_index = {option["option_id"]: option for option in options["pump_slot_options"]}
    meter_option_index = {option["option_id"]: option for option in options["meter_slot_options"]}
    suction_option_index = {option["option_id"]: option for option in options["suction_trunk_options"]}
    discharge_option_index = {
        option["option_id"]: option for option in options["discharge_trunk_options"]
    }
    component_index = {component["component_id"]: component for component in components}

    payload = {
        "routes": {route["route_id"]: route for route in routes},
        "route_ids": route_ids,
        "mandatory_routes": [route["route_id"] for route in routes if route["mandatory"]],
        "optional_routes": [route["route_id"] for route in routes if not route["mandatory"]],
        "source_nodes": source_nodes,
        "sink_nodes": sink_nodes,
        "routes_by_source": _group_routes(routes, "source"),
        "routes_by_sink": _group_routes(routes, "sink"),
        "system_classes": list(options["system_classes"]),
        "route_feasible_classes": options["route_class_feasibility"],
        "source_options": source_option_index,
        "source_option_ids_by_node": {
            node_id: [option["option_id"] for option in node_options]
            for node_id, node_options in options["source_options"].items()
        },
        "destination_options": destination_option_index,
        "destination_option_ids_by_node": {
            node_id: [option["option_id"] for option in node_options]
            for node_id, node_options in options["destination_options"].items()
        },
        "pump_options": pump_option_index,
        "pump_option_ids": list(pump_option_index),
        "meter_options": meter_option_index,
        "meter_option_ids": list(meter_option_index),
        "suction_trunk_options": suction_option_index,
        "suction_trunk_option_ids": list(suction_option_index),
        "discharge_trunk_options": discharge_option_index,
        "discharge_trunk_option_ids": list(discharge_option_index),
        "component_ids": list(component_index),
        "components": component_index,
        "settings": settings,
        "pump_slots": list(range(1, int(settings["u_max_slots"]) + 1)),
        "meter_slots": list(range(1, int(settings["v_max_slots"]) + 1)),
    }

    payload["source_option_ids_by_class"] = _group_options_by_class(payload["source_options"])
    payload["destination_option_ids_by_class"] = _group_options_by_class(payload["destination_options"])
    payload["pump_option_ids_by_class"] = _group_options_by_class(payload["pump_options"])
    payload["meter_option_ids_by_class"] = _group_options_by_class(payload["meter_options"])
    payload["suction_trunk_option_ids_by_class"] = _group_options_by_class(
        payload["suction_trunk_options"]
    )
    payload["discharge_trunk_option_ids_by_class"] = _group_options_by_class(
        payload["discharge_trunk_options"]
    )

    return {
        **payload,
    }


def _index_options(options_by_key: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for node_options in options_by_key.values():
        for option in node_options:
            indexed[option["option_id"]] = option
    return indexed


def _group_routes(routes: list[Dict[str, Any]], group_key: str) -> Dict[str, list[str]]:
    grouped: Dict[str, list[str]] = defaultdict(list)
    for route in routes:
        grouped[route[group_key]].append(route["route_id"])
    return {key: sorted(value) for key, value in grouped.items()}


def _group_options_by_class(option_index: Dict[str, Dict[str, Any]]) -> Dict[str, list[str]]:
    grouped: Dict[str, list[str]] = defaultdict(list)
    for option_id, option in option_index.items():
        grouped[option["sys_diameter_class"]].append(option_id)
    return {key: sorted(value) for key, value in grouped.items()}
