from __future__ import annotations

from typing import Any


def add_objective(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload
    settings = payload["settings"]

    material_cost = 0
    for node_id, option_ids in payload["source_option_ids_by_node"].items():
        for option_id in option_ids:
            material_cost += payload["source_options"][option_id]["cost"] * model.source_option_selected[
                node_id, option_id
            ]

    for node_id, option_ids in payload["destination_option_ids_by_node"].items():
        for option_id in option_ids:
            material_cost += payload["destination_options"][option_id]["cost"] * model.destination_option_selected[
                node_id, option_id
            ]

    for slot in payload["pump_slots"]:
        for option_id in payload["pump_option_ids"]:
            material_cost += payload["pump_options"][option_id]["cost"] * model.pump_option_selected[
                slot, option_id
            ]

    for slot in payload["meter_slots"]:
        for option_id in payload["meter_option_ids"]:
            material_cost += payload["meter_options"][option_id]["cost"] * model.meter_option_selected[
                slot, option_id
            ]

    for option_id in payload["suction_trunk_option_ids"]:
        material_cost += payload["suction_trunk_options"][option_id]["cost"] * model.suction_trunk_selected[
            option_id
        ]

    for option_id in payload["discharge_trunk_option_ids"]:
        material_cost += payload["discharge_trunk_options"][option_id]["cost"] * model.discharge_trunk_selected[
            option_id
        ]

    optional_route_reward = float(settings["optional_route_reward"])
    cleaning_penalty = float(settings["cleaning_cost_liters_per_operation"])
    robustness_weight = float(settings["robustness_weight"])
    reward_term = sum(
        optional_route_reward
        * float(payload["routes"][route_id]["weight"])
        * model.route_active[route_id]
        for route_id in payload["optional_routes"]
    )
    cleaning_term = cleaning_penalty * sum(model.route_active[route_id] for route_id in payload["route_ids"])

    model.total_cost_expression = pyo.Expression(expr=material_cost + cleaning_term)
    model.optional_reward_expression = pyo.Expression(expr=reward_term)
    model.robustness_expression = pyo.Expression(
        expr=robustness_weight * sum(model.hydraulic_slack_lpm[route_id] for route_id in payload["route_ids"])
    )
    model.total_objective = pyo.Objective(
        expr=model.total_cost_expression - model.optional_reward_expression - model.robustness_expression,
        sense=pyo.minimize,
    )
