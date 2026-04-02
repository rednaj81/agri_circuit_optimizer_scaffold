from __future__ import annotations

from typing import Any


def add_hydraulic_constraints(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload
    hydraulic_mode = payload["settings"].get("hydraulic_loss_mode", "additive_lpm")

    def source_capacity_expr(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        source_node = route["source"]
        return sum(
            payload["source_options"][option_id]["q_max_lpm"]
            * model.source_option_selected[source_node, option_id]
            for option_id in payload["source_option_ids_by_node"][source_node]
        )

    def destination_capacity_expr(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        sink_node = route["sink"]
        return sum(
            payload["destination_options"][option_id]["q_max_lpm"]
            * model.destination_option_selected[sink_node, option_id]
            for option_id in payload["destination_option_ids_by_node"][sink_node]
        )

    def suction_capacity_expr(model: Any) -> Any:
        return sum(
            payload["suction_trunk_options"][option_id]["q_max_lpm"]
            * model.suction_trunk_selected[option_id]
            for option_id in payload["suction_trunk_option_ids"]
        )

    def discharge_capacity_expr(model: Any) -> Any:
        return sum(
            payload["discharge_trunk_options"][option_id]["q_max_lpm"]
            * model.discharge_trunk_selected[option_id]
            for option_id in payload["discharge_trunk_option_ids"]
        )

    def pump_capacity_expr(model: Any, route_id: str) -> Any:
        return sum(
            payload["pump_options"][option_id]["q_max_lpm"]
            * model.route_uses_pump_option[route_id, slot, option_id]
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        )

    def meter_capacity_expr(model: Any, route_id: str) -> Any:
        return sum(
            payload["route_meter_compatibility"][route_id][option_id]["meter_q_max_lpm"]
            * model.route_uses_meter_option[route_id, slot, option_id]
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
        )

    def total_loss_rule(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        source_node = route["source"]
        sink_node = route["sink"]
        source_loss = sum(
            payload["source_options"][option_id]["loss_lpm_equiv"]
            * model.source_option_selected[source_node, option_id]
            for option_id in payload["source_option_ids_by_node"][source_node]
        )
        destination_loss = sum(
            payload["destination_options"][option_id]["loss_lpm_equiv"]
            * model.destination_option_selected[sink_node, option_id]
            for option_id in payload["destination_option_ids_by_node"][sink_node]
        )
        suction_loss = sum(
            payload["suction_trunk_options"][option_id]["loss_lpm_equiv"]
            * model.suction_trunk_selected[option_id]
            for option_id in payload["suction_trunk_option_ids"]
        )
        discharge_loss = sum(
            payload["discharge_trunk_options"][option_id]["loss_lpm_equiv"]
            * model.discharge_trunk_selected[option_id]
            for option_id in payload["discharge_trunk_option_ids"]
        )
        pump_loss = sum(
            payload["pump_options"][option_id]["loss_lpm_equiv"]
            * model.route_uses_pump_option[route_id, slot, option_id]
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        )
        meter_loss = sum(
            payload["meter_options"][option_id]["loss_lpm_equiv"]
            * model.route_uses_meter_option[route_id, slot, option_id]
            for slot in payload["meter_slots"]
            for option_id in payload["meter_option_ids"]
        )
        return model.total_loss_lpm_equiv[route_id] == (
            source_loss + destination_loss + suction_loss + discharge_loss + pump_loss + meter_loss
        )

    model.total_loss_definition = pyo.Constraint(model.ROUTES, rule=total_loss_rule)

    def route_effective_definition_rule(model: Any, route_id: str) -> Any:
        return model.route_effective_q_max_lpm[route_id] == (
            model.flow_delivered_lpm[route_id] + model.hydraulic_slack_lpm[route_id]
        )

    model.route_effective_definition = pyo.Constraint(
        model.ROUTES, rule=route_effective_definition_rule
    )

    def hydraulic_slack_rule(model: Any, route_id: str) -> Any:
        if hydraulic_mode == "bottleneck_plus_length":
            return pyo.Constraint.Skip
        return model.hydraulic_slack_lpm[route_id] == (
            pump_capacity_expr(model, route_id)
            - model.flow_delivered_lpm[route_id]
            - model.total_loss_lpm_equiv[route_id]
        )

    model.hydraulic_slack_definition = pyo.Constraint(model.ROUTES, rule=hydraulic_slack_rule)

    def hydraulic_capacity_rule(model: Any, route_id: str) -> Any:
        if hydraulic_mode == "bottleneck_plus_length":
            return pyo.Constraint.Skip
        return (
            model.flow_delivered_lpm[route_id] + model.total_loss_lpm_equiv[route_id]
            <= pump_capacity_expr(model, route_id)
        )

    model.hydraulic_capacity = pyo.Constraint(model.ROUTES, rule=hydraulic_capacity_rule)

    def route_effective_upper_source_rule(model: Any, route_id: str) -> Any:
        return model.route_effective_q_max_lpm[route_id] <= source_capacity_expr(model, route_id)

    model.route_effective_upper_source = pyo.Constraint(
        model.ROUTES, rule=route_effective_upper_source_rule
    )

    def route_effective_upper_destination_rule(model: Any, route_id: str) -> Any:
        return model.route_effective_q_max_lpm[route_id] <= destination_capacity_expr(model, route_id)

    model.route_effective_upper_destination = pyo.Constraint(
        model.ROUTES, rule=route_effective_upper_destination_rule
    )

    def route_effective_upper_suction_rule(model: Any, route_id: str) -> Any:
        return model.route_effective_q_max_lpm[route_id] <= suction_capacity_expr(model)

    model.route_effective_upper_suction = pyo.Constraint(
        model.ROUTES, rule=route_effective_upper_suction_rule
    )

    def route_effective_upper_discharge_rule(model: Any, route_id: str) -> Any:
        return model.route_effective_q_max_lpm[route_id] <= discharge_capacity_expr(model)

    model.route_effective_upper_discharge = pyo.Constraint(
        model.ROUTES, rule=route_effective_upper_discharge_rule
    )

    def route_effective_upper_pump_rule(model: Any, route_id: str) -> Any:
        if hydraulic_mode == "bottleneck_plus_length":
            return model.route_effective_q_max_lpm[route_id] <= pump_capacity_expr(model, route_id)
        return model.route_effective_q_max_lpm[route_id] <= (
            pump_capacity_expr(model, route_id) - model.total_loss_lpm_equiv[route_id]
        )

    model.route_effective_upper_pump = pyo.Constraint(
        model.ROUTES, rule=route_effective_upper_pump_rule
    )

    def route_effective_upper_meter_rule(model: Any, route_id: str) -> Any:
        return model.route_effective_q_max_lpm[route_id] <= meter_capacity_expr(model, route_id)

    model.route_effective_upper_meter = pyo.Constraint(
        model.ROUTES, rule=route_effective_upper_meter_rule
    )
