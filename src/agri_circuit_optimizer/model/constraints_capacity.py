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

    def pump_slot_upper_capacity_rule(model: Any, route_id: str, slot: int) -> Any:
        slot_capacity = sum(
            payload["pump_options"][option_id]["q_max_lpm"] * model.pump_option_selected[slot, option_id]
            for option_id in payload["pump_option_ids"]
        )
        return model.flow_delivered_lpm[route_id] <= slot_capacity + max_q * (
            1 - model.route_uses_pump_slot[route_id, slot]
        )

    model.pump_slot_upper_capacity = pyo.Constraint(
        model.ROUTE_PUMP_ASSIGNMENT_KEYS, rule=pump_slot_upper_capacity_rule
    )

    def pump_slot_lower_capacity_rule(model: Any, route_id: str, slot: int) -> Any:
        slot_qmin = sum(
            payload["pump_options"][option_id]["q_min_lpm"] * model.pump_option_selected[slot, option_id]
            for option_id in payload["pump_option_ids"]
        )
        return model.flow_delivered_lpm[route_id] >= slot_qmin - max_q * (
            1 - model.route_uses_pump_slot[route_id, slot]
        )

    model.pump_slot_lower_capacity = pyo.Constraint(
        model.ROUTE_PUMP_ASSIGNMENT_KEYS, rule=pump_slot_lower_capacity_rule
    )

    def meter_slot_upper_capacity_rule(model: Any, route_id: str, slot: int) -> Any:
        slot_capacity = sum(
            payload["meter_options"][option_id]["q_max_lpm"] * model.meter_option_selected[slot, option_id]
            for option_id in payload["meter_option_ids"]
        )
        return model.flow_delivered_lpm[route_id] <= slot_capacity + max_q * (
            1 - model.route_uses_meter_slot[route_id, slot]
        )

    model.meter_slot_upper_capacity = pyo.Constraint(
        model.ROUTE_METER_ASSIGNMENT_KEYS, rule=meter_slot_upper_capacity_rule
    )

    def meter_slot_lower_capacity_rule(model: Any, route_id: str, slot: int) -> Any:
        slot_qmin = sum(
            payload["meter_options"][option_id]["q_min_lpm"] * model.meter_option_selected[slot, option_id]
            for option_id in payload["meter_option_ids"]
        )
        return model.flow_delivered_lpm[route_id] >= slot_qmin - max_q * (
            1 - model.route_uses_meter_slot[route_id, slot]
        )

    model.meter_slot_lower_capacity = pyo.Constraint(
        model.ROUTE_METER_ASSIGNMENT_KEYS, rule=meter_slot_lower_capacity_rule
    )

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
