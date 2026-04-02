from __future__ import annotations

from typing import Any


def add_capacity_constraints(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload
    max_q = max(
        [
            option["q_max_lpm"]
            for option in payload["pump_options"].values()
        ]
        + [option["q_max_lpm"] for option in payload["meter_options"].values()]
        + [option["q_max_lpm"] for option in payload["source_options"].values()]
        + [option["q_max_lpm"] for option in payload["destination_options"].values()]
        + [option["q_max_lpm"] for option in payload["suction_trunk_options"].values()]
        + [option["q_max_lpm"] for option in payload["discharge_trunk_options"].values()]
    )

    def min_required_flow_rule(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        return model.flow_delivered_lpm[route_id] >= (
            float(route["q_min_delivered_lpm"]) * model.route_active[route_id]
        )

    model.minimum_required_flow = pyo.Constraint(model.ROUTES, rule=min_required_flow_rule)

    def route_flow_activation_rule(model: Any, route_id: str) -> Any:
        return model.flow_delivered_lpm[route_id] <= max_q * model.route_active[route_id]

    model.route_flow_activation = pyo.Constraint(model.ROUTES, rule=route_flow_activation_rule)

    def source_branch_capacity_rule(model: Any, route_id: str) -> Any:
        source_node = payload["routes"][route_id]["source"]
        option_ids = payload["source_option_ids_by_node"][source_node]
        return model.flow_delivered_lpm[route_id] <= sum(
            payload["source_options"][option_id]["q_max_lpm"]
            * model.source_option_selected[source_node, option_id]
            for option_id in option_ids
        )

    model.source_branch_capacity = pyo.Constraint(model.ROUTES, rule=source_branch_capacity_rule)

    def destination_branch_capacity_rule(model: Any, route_id: str) -> Any:
        sink_node = payload["routes"][route_id]["sink"]
        option_ids = payload["destination_option_ids_by_node"][sink_node]
        return model.flow_delivered_lpm[route_id] <= sum(
            payload["destination_options"][option_id]["q_max_lpm"]
            * model.destination_option_selected[sink_node, option_id]
            for option_id in option_ids
        )

    model.destination_branch_capacity = pyo.Constraint(
        model.ROUTES, rule=destination_branch_capacity_rule
    )

    def suction_trunk_capacity_rule(model: Any, route_id: str) -> Any:
        return model.flow_delivered_lpm[route_id] <= sum(
            payload["suction_trunk_options"][option_id]["q_max_lpm"]
            * model.suction_trunk_selected[option_id]
            for option_id in payload["suction_trunk_option_ids"]
        )

    model.suction_trunk_capacity = pyo.Constraint(
        model.ROUTES, rule=suction_trunk_capacity_rule
    )

    def discharge_trunk_capacity_rule(model: Any, route_id: str) -> Any:
        return model.flow_delivered_lpm[route_id] <= sum(
            payload["discharge_trunk_options"][option_id]["q_max_lpm"]
            * model.discharge_trunk_selected[option_id]
            for option_id in payload["discharge_trunk_option_ids"]
        )

    model.discharge_trunk_capacity = pyo.Constraint(
        model.ROUTES, rule=discharge_trunk_capacity_rule
    )

    def pump_capacity_upper_rule(model: Any, route_id: str) -> Any:
        return model.flow_delivered_lpm[route_id] <= sum(
            payload["pump_options"][option_id]["q_max_lpm"]
            * model.route_uses_pump_option[route_id, slot, option_id]
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        ) + max_q * (1 - model.route_active[route_id])

    model.pump_capacity_upper = pyo.Constraint(model.ROUTES, rule=pump_capacity_upper_rule)

    def pump_capacity_lower_rule(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        if not route["need_pump"]:
            return pyo.Constraint.Skip
        return model.flow_delivered_lpm[route_id] >= sum(
            payload["pump_options"][option_id]["q_min_lpm"]
            * model.route_uses_pump_option[route_id, slot, option_id]
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        )

    model.pump_capacity_lower = pyo.Constraint(model.ROUTES, rule=pump_capacity_lower_rule)

    def meter_capacity_upper_rule(model: Any, route_id: str) -> Any:
        return model.flow_delivered_lpm[route_id] <= sum(
            payload["route_meter_compatibility"][route_id][option_id]["meter_q_max_lpm"]
            * model.route_uses_meter_option[route_id, slot, option_id]
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
        ) + max_q * (1 - model.route_active[route_id])

    model.meter_capacity_upper = pyo.Constraint(model.ROUTES, rule=meter_capacity_upper_rule)

    def meter_capacity_lower_rule(model: Any, route_id: str) -> Any:
        return model.flow_delivered_lpm[route_id] >= sum(
            payload["meter_options"][option_id]["q_min_lpm"]
            * model.route_uses_meter_option[route_id, slot, option_id]
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
        )

    model.meter_capacity_lower = pyo.Constraint(model.ROUTES, rule=meter_capacity_lower_rule)

    def component_availability_rule(model: Any, component_id: str) -> Any:
        total_usage = 0

        for node_id, option_ids in payload["source_option_ids_by_node"].items():
            for option_id in option_ids:
                total_usage += payload["source_options"][option_id]["component_counts"].get(component_id, 0) * (
                    model.source_option_selected[node_id, option_id]
                )

        for node_id, option_ids in payload["destination_option_ids_by_node"].items():
            for option_id in option_ids:
                total_usage += payload["destination_options"][option_id]["component_counts"].get(
                    component_id, 0
                ) * model.destination_option_selected[node_id, option_id]

        for slot in payload["pump_slots"]:
            for option_id in payload["pump_option_ids"]:
                total_usage += payload["pump_options"][option_id]["component_counts"].get(component_id, 0) * (
                    model.pump_option_selected[slot, option_id]
                )

        for slot in payload["meter_slots"]:
            for option_id in payload["meter_option_ids"]:
                total_usage += payload["meter_options"][option_id]["component_counts"].get(component_id, 0) * (
                    model.meter_option_selected[slot, option_id]
                )

        for option_id in payload["suction_trunk_option_ids"]:
            total_usage += payload["suction_trunk_options"][option_id]["component_counts"].get(
                component_id, 0
            ) * model.suction_trunk_selected[option_id]

        for option_id in payload["discharge_trunk_option_ids"]:
            total_usage += payload["discharge_trunk_options"][option_id]["component_counts"].get(
                component_id, 0
            ) * model.discharge_trunk_selected[option_id]

        return total_usage <= int(payload["components"][component_id]["available_qty"])

    model.component_availability = pyo.Constraint(
        model.COMPONENTS, rule=component_availability_rule
    )
