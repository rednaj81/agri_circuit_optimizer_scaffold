from __future__ import annotations

from typing import Any


def declare_variables(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload

    model.ROUTES = pyo.Set(initialize=payload["route_ids"], ordered=True)
    model.MANDATORY_ROUTES = pyo.Set(initialize=payload["mandatory_routes"], ordered=True)
    model.OPTIONAL_ROUTES = pyo.Set(initialize=payload["optional_routes"], ordered=True)
    model.SOURCE_NODES = pyo.Set(initialize=payload["source_nodes"], ordered=True)
    model.SINK_NODES = pyo.Set(initialize=payload["sink_nodes"], ordered=True)
    model.SYSTEM_CLASSES = pyo.Set(initialize=payload["system_classes"], ordered=True)
    model.PUMP_SLOTS = pyo.Set(initialize=payload["pump_slots"], ordered=True)
    model.METER_SLOTS = pyo.Set(initialize=payload["meter_slots"], ordered=True)
    model.COMPONENTS = pyo.Set(initialize=payload["component_ids"], ordered=True)

    model.SOURCE_OPTION_KEYS = pyo.Set(
        dimen=2,
        initialize=[
            (node_id, option_id)
            for node_id, option_ids in payload["source_option_ids_by_node"].items()
            for option_id in option_ids
        ],
        ordered=True,
    )
    model.DESTINATION_OPTION_KEYS = pyo.Set(
        dimen=2,
        initialize=[
            (node_id, option_id)
            for node_id, option_ids in payload["destination_option_ids_by_node"].items()
            for option_id in option_ids
        ],
        ordered=True,
    )
    model.PUMP_OPTION_KEYS = pyo.Set(
        dimen=2,
        initialize=[
            (slot, option_id)
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        ],
        ordered=True,
    )
    model.METER_OPTION_KEYS = pyo.Set(
        dimen=2,
        initialize=[
            (slot, option_id)
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
        ],
        ordered=True,
    )
    model.ROUTE_PUMP_ASSIGNMENT_KEYS = pyo.Set(
        dimen=2,
        initialize=[
            (route_id, slot)
            for route_id in payload["route_ids"]
            for slot in payload["pump_slots"]
        ],
        ordered=True,
    )
    model.ROUTE_METER_ASSIGNMENT_KEYS = pyo.Set(
        dimen=2,
        initialize=[
            (route_id, slot)
            for route_id in payload["route_ids"]
            for slot in payload["meter_slots"]
        ],
        ordered=True,
    )
    model.ROUTE_PUMP_OPTION_KEYS = pyo.Set(
        dimen=3,
        initialize=[
            (route_id, slot, option_id)
            for route_id in payload["route_ids"]
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        ],
        ordered=True,
    )
    model.ROUTE_METER_OPTION_KEYS = pyo.Set(
        dimen=3,
        initialize=[
            (route_id, slot, option_id)
            for route_id in payload["route_ids"]
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
        ],
        ordered=True,
    )
    model.SUCTION_TRUNK_OPTIONS = pyo.Set(
        initialize=payload["suction_trunk_option_ids"], ordered=True
    )
    model.DISCHARGE_TRUNK_OPTIONS = pyo.Set(
        initialize=payload["discharge_trunk_option_ids"], ordered=True
    )

    model.route_active = pyo.Var(model.ROUTES, domain=pyo.Binary)
    model.source_node_active = pyo.Var(model.SOURCE_NODES, domain=pyo.Binary)
    model.sink_node_active = pyo.Var(model.SINK_NODES, domain=pyo.Binary)
    model.system_class_selected = pyo.Var(model.SYSTEM_CLASSES, domain=pyo.Binary)

    model.source_option_selected = pyo.Var(model.SOURCE_OPTION_KEYS, domain=pyo.Binary)
    model.destination_option_selected = pyo.Var(model.DESTINATION_OPTION_KEYS, domain=pyo.Binary)
    model.pump_option_selected = pyo.Var(model.PUMP_OPTION_KEYS, domain=pyo.Binary)
    model.meter_option_selected = pyo.Var(model.METER_OPTION_KEYS, domain=pyo.Binary)
    model.route_uses_pump_slot = pyo.Var(model.ROUTE_PUMP_ASSIGNMENT_KEYS, domain=pyo.Binary)
    model.route_uses_meter_slot = pyo.Var(model.ROUTE_METER_ASSIGNMENT_KEYS, domain=pyo.Binary)
    model.route_uses_pump_option = pyo.Var(model.ROUTE_PUMP_OPTION_KEYS, domain=pyo.Binary)
    model.route_uses_meter_option = pyo.Var(model.ROUTE_METER_OPTION_KEYS, domain=pyo.Binary)
    model.suction_trunk_selected = pyo.Var(model.SUCTION_TRUNK_OPTIONS, domain=pyo.Binary)
    model.discharge_trunk_selected = pyo.Var(model.DISCHARGE_TRUNK_OPTIONS, domain=pyo.Binary)
    model.flow_delivered_lpm = pyo.Var(model.ROUTES, domain=pyo.NonNegativeReals)
    model.total_loss_lpm_equiv = pyo.Var(model.ROUTES, domain=pyo.NonNegativeReals)
    model.hydraulic_slack_lpm = pyo.Var(model.ROUTES, domain=pyo.NonNegativeReals)
