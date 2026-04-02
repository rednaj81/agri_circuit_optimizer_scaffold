from __future__ import annotations

from typing import Any


def add_structure_constraints(model: Any) -> None:
    import pyomo.environ as pyo

    payload = model._payload

    model.single_system_class = pyo.Constraint(
        expr=sum(model.system_class_selected[system_class] for system_class in model.SYSTEM_CLASSES) == 1
    )
    model.single_suction_trunk = pyo.Constraint(
        expr=sum(model.suction_trunk_selected[option_id] for option_id in model.SUCTION_TRUNK_OPTIONS) == 1
    )
    model.single_discharge_trunk = pyo.Constraint(
        expr=(
            sum(model.discharge_trunk_selected[option_id] for option_id in model.DISCHARGE_TRUNK_OPTIONS)
            == 1
        )
    )

    def mandatory_route_rule(model: Any, route_id: str) -> Any:
        return model.route_active[route_id] == 1

    model.mandatory_routes_enforced = pyo.Constraint(
        model.MANDATORY_ROUTES, rule=mandatory_route_rule
    )

    def source_node_selection_rule(model: Any, node_id: str) -> Any:
        option_ids = payload["source_option_ids_by_node"][node_id]
        return (
            sum(model.source_option_selected[node_id, option_id] for option_id in option_ids)
            == model.source_node_active[node_id]
        )

    model.source_node_selection = pyo.Constraint(model.SOURCE_NODES, rule=source_node_selection_rule)

    def sink_node_selection_rule(model: Any, node_id: str) -> Any:
        option_ids = payload["destination_option_ids_by_node"][node_id]
        return (
            sum(model.destination_option_selected[node_id, option_id] for option_id in option_ids)
            == model.sink_node_active[node_id]
        )

    model.sink_node_selection = pyo.Constraint(model.SINK_NODES, rule=sink_node_selection_rule)

    def source_node_activation_lb_rule(model: Any, route_id: str) -> Any:
        source_node = payload["routes"][route_id]["source"]
        return model.route_active[route_id] <= model.source_node_active[source_node]

    model.source_node_activation_lb = pyo.Constraint(
        model.ROUTES, rule=source_node_activation_lb_rule
    )

    def sink_node_activation_lb_rule(model: Any, route_id: str) -> Any:
        sink_node = payload["routes"][route_id]["sink"]
        return model.route_active[route_id] <= model.sink_node_active[sink_node]

    model.sink_node_activation_lb = pyo.Constraint(model.ROUTES, rule=sink_node_activation_lb_rule)

    def source_node_activation_ub_rule(model: Any, node_id: str) -> Any:
        route_ids = payload["routes_by_source"][node_id]
        return model.source_node_active[node_id] <= sum(model.route_active[route_id] for route_id in route_ids)

    model.source_node_activation_ub = pyo.Constraint(
        model.SOURCE_NODES, rule=source_node_activation_ub_rule
    )

    def sink_node_activation_ub_rule(model: Any, node_id: str) -> Any:
        route_ids = payload["routes_by_sink"][node_id]
        return model.sink_node_active[node_id] <= sum(model.route_active[route_id] for route_id in route_ids)

    model.sink_node_activation_ub = pyo.Constraint(model.SINK_NODES, rule=sink_node_activation_ub_rule)

    def route_class_feasibility_rule(model: Any, route_id: str) -> Any:
        feasible_classes = payload["route_feasible_classes"][route_id]
        return model.route_active[route_id] <= sum(
            model.system_class_selected[system_class] for system_class in feasible_classes
        )

    model.route_class_feasibility = pyo.Constraint(model.ROUTES, rule=route_class_feasibility_rule)

    def pump_slot_single_option_rule(model: Any, slot: int) -> Any:
        return (
            sum(
                model.pump_option_selected[slot, option_id]
                for option_id in payload["pump_option_ids"]
            )
            <= 1
        )

    model.pump_slot_single_option = pyo.Constraint(model.PUMP_SLOTS, rule=pump_slot_single_option_rule)

    def meter_slot_single_option_rule(model: Any, slot: int) -> Any:
        return (
            sum(
                model.meter_option_selected[slot, option_id]
                for option_id in payload["meter_option_ids"]
            )
            <= 1
        )

    model.meter_slot_single_option = pyo.Constraint(
        model.METER_SLOTS, rule=meter_slot_single_option_rule
    )

    def pump_slot_class_rule(model: Any, slot: int, system_class: str) -> Any:
        option_ids = payload["pump_option_ids_by_class"].get(system_class, [])
        if not option_ids:
            return pyo.Constraint.Skip
        return sum(model.pump_option_selected[slot, option_id] for option_id in option_ids) <= (
            model.system_class_selected[system_class]
        )

    model.pump_slot_class_compatibility = pyo.Constraint(
        model.PUMP_SLOTS, model.SYSTEM_CLASSES, rule=pump_slot_class_rule
    )

    def meter_slot_class_rule(model: Any, slot: int, system_class: str) -> Any:
        option_ids = payload["meter_option_ids_by_class"].get(system_class, [])
        if not option_ids:
            return pyo.Constraint.Skip
        return sum(model.meter_option_selected[slot, option_id] for option_id in option_ids) <= (
            model.system_class_selected[system_class]
        )

    model.meter_slot_class_compatibility = pyo.Constraint(
        model.METER_SLOTS, model.SYSTEM_CLASSES, rule=meter_slot_class_rule
    )

    def suction_trunk_class_rule(model: Any, system_class: str) -> Any:
        option_ids = payload["suction_trunk_option_ids_by_class"].get(system_class, [])
        if not option_ids:
            return model.system_class_selected[system_class] == 0
        return sum(model.suction_trunk_selected[option_id] for option_id in option_ids) == (
            model.system_class_selected[system_class]
        )

    model.suction_trunk_class_compatibility = pyo.Constraint(
        model.SYSTEM_CLASSES, rule=suction_trunk_class_rule
    )

    def discharge_trunk_class_rule(model: Any, system_class: str) -> Any:
        option_ids = payload["discharge_trunk_option_ids_by_class"].get(system_class, [])
        if not option_ids:
            return model.system_class_selected[system_class] == 0
        return sum(model.discharge_trunk_selected[option_id] for option_id in option_ids) == (
            model.system_class_selected[system_class]
        )

    model.discharge_trunk_class_compatibility = pyo.Constraint(
        model.SYSTEM_CLASSES, rule=discharge_trunk_class_rule
    )

    def route_pump_assignment_rule(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        required_slots = model.route_active[route_id] if route["need_pump"] else 0
        return (
            sum(model.route_uses_pump_slot[route_id, slot] for slot in model.PUMP_SLOTS)
            == required_slots
        )

    model.route_pump_assignment = pyo.Constraint(
        model.ROUTES, rule=route_pump_assignment_rule
    )

    def route_meter_assignment_rule(model: Any, route_id: str) -> Any:
        return (
            sum(model.route_uses_meter_slot[route_id, slot] for slot in model.METER_SLOTS)
            == model.route_active[route_id]
        )

    model.route_meter_assignment = pyo.Constraint(
        model.ROUTES, rule=route_meter_assignment_rule
    )

    def route_pump_option_count_rule(model: Any, route_id: str) -> Any:
        route = payload["routes"][route_id]
        required_options = model.route_active[route_id] if route["need_pump"] else 0
        return sum(
            model.route_uses_pump_option[route_id, slot, option_id]
            for slot in model.PUMP_SLOTS
            for option_id in payload["pump_option_ids"]
        ) == required_options

    model.route_pump_option_count = pyo.Constraint(model.ROUTES, rule=route_pump_option_count_rule)

    def route_meter_option_count_rule(model: Any, route_id: str) -> Any:
        return sum(
            model.route_uses_meter_option[route_id, slot, option_id]
            for slot in model.METER_SLOTS
            for option_id in payload["meter_option_ids"]
        ) == model.route_active[route_id]

    model.route_meter_option_count = pyo.Constraint(
        model.ROUTES, rule=route_meter_option_count_rule
    )

    def route_pump_slot_definition_rule(model: Any, route_id: str, slot: int) -> Any:
        return model.route_uses_pump_slot[route_id, slot] == sum(
            model.route_uses_pump_option[route_id, slot, option_id]
            for option_id in payload["pump_option_ids"]
        )

    model.route_pump_slot_definition = pyo.Constraint(
        model.ROUTE_PUMP_ASSIGNMENT_KEYS, rule=route_pump_slot_definition_rule
    )

    def route_meter_slot_definition_rule(model: Any, route_id: str, slot: int) -> Any:
        return model.route_uses_meter_slot[route_id, slot] == sum(
            model.route_uses_meter_option[route_id, slot, option_id]
            for option_id in payload["meter_option_ids"]
        )

    model.route_meter_slot_definition = pyo.Constraint(
        model.ROUTE_METER_ASSIGNMENT_KEYS, rule=route_meter_slot_definition_rule
    )

    def route_pump_option_activation_rule(model: Any, route_id: str, slot: int, option_id: str) -> Any:
        return model.route_uses_pump_option[route_id, slot, option_id] <= model.pump_option_selected[
            slot, option_id
        ]

    model.route_pump_option_activation = pyo.Constraint(
        model.ROUTE_PUMP_OPTION_KEYS, rule=route_pump_option_activation_rule
    )

    def route_meter_option_activation_rule(model: Any, route_id: str, slot: int, option_id: str) -> Any:
        return model.route_uses_meter_option[route_id, slot, option_id] <= model.meter_option_selected[
            slot, option_id
        ]

    model.route_meter_option_activation = pyo.Constraint(
        model.ROUTE_METER_OPTION_KEYS, rule=route_meter_option_activation_rule
    )

    def route_pump_slot_activation_rule(model: Any, route_id: str, slot: int) -> Any:
        return model.route_uses_pump_slot[route_id, slot] <= sum(
            model.pump_option_selected[slot, option_id] for option_id in payload["pump_option_ids"]
        )

    model.route_pump_slot_activation = pyo.Constraint(
        model.ROUTE_PUMP_ASSIGNMENT_KEYS, rule=route_pump_slot_activation_rule
    )

    def pump_option_usage_required_rule(model: Any, slot: int, option_id: str) -> Any:
        return model.pump_option_selected[slot, option_id] <= sum(
            model.route_uses_pump_option[route_id, slot, option_id]
            for route_id in payload["route_ids"]
        )

    model.pump_option_usage_required = pyo.Constraint(
        model.PUMP_OPTION_KEYS, rule=pump_option_usage_required_rule
    )

    def route_meter_slot_activation_rule(model: Any, route_id: str, slot: int) -> Any:
        return model.route_uses_meter_slot[route_id, slot] <= sum(
            model.meter_option_selected[slot, option_id] for option_id in payload["meter_option_ids"]
        )

    model.route_meter_slot_activation = pyo.Constraint(
        model.ROUTE_METER_ASSIGNMENT_KEYS, rule=route_meter_slot_activation_rule
    )

    def meter_option_usage_required_rule(model: Any, slot: int, option_id: str) -> Any:
        return model.meter_option_selected[slot, option_id] <= sum(
            model.route_uses_meter_option[route_id, slot, option_id]
            for route_id in payload["route_ids"]
        )

    model.meter_option_usage_required = pyo.Constraint(
        model.METER_OPTION_KEYS, rule=meter_option_usage_required_rule
    )
