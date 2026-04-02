from __future__ import annotations

from typing import Any


def add_hydraulic_constraints(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload

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

    def hydraulic_slack_rule(model: Any, route_id: str) -> Any:
        pump_capacity = sum(
            payload["pump_options"][option_id]["q_max_lpm"]
            * model.route_uses_pump_option[route_id, slot, option_id]
            for slot in payload["pump_slots"]
            for option_id in payload["pump_option_ids"]
        )
        return model.hydraulic_slack_lpm[route_id] == (
            pump_capacity - model.flow_delivered_lpm[route_id] - model.total_loss_lpm_equiv[route_id]
        )

    model.hydraulic_slack_definition = pyo.Constraint(model.ROUTES, rule=hydraulic_slack_rule)

    def hydraulic_capacity_rule(model: Any, route_id: str) -> Any:
        return (
            model.flow_delivered_lpm[route_id] + model.total_loss_lpm_equiv[route_id]
            <= sum(
                payload["pump_options"][option_id]["q_max_lpm"]
                * model.route_uses_pump_option[route_id, slot, option_id]
                for slot in payload["pump_slots"]
                for option_id in payload["pump_option_ids"]
            )
        )

    model.hydraulic_capacity = pyo.Constraint(model.ROUTES, rule=hydraulic_capacity_rule)
