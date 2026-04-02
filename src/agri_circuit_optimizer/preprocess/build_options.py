from __future__ import annotations

from collections import Counter, defaultdict
from itertools import product
from typing import Any, Dict, Iterable, List

from agri_circuit_optimizer.preprocess.compatibility import (
    component_matches_diameter,
    meter_option_allowed_for_route,
    route_respects_frozen_rules,
    split_encoded_values,
)
from agri_circuit_optimizer.preprocess.pruning import prune_dominated_options


def build_stage_options(data: Dict[str, Any]) -> Dict[str, Any]:
    """Build viable V1/V2/V3 options for each superstructure stage."""

    nodes = data["nodes"].to_dict("records")
    routes = data["routes"].to_dict("records")
    components = data["components"].to_dict("records")
    settings = data["settings"]

    source_options = _build_branch_options(
        nodes=nodes,
        templates=data["source_branch_templates"].to_dict("records"),
        components=components,
        stage_kind="source_branch",
        node_filter_key="is_source",
    )
    destination_options = _build_branch_options(
        nodes=nodes,
        templates=data["destination_branch_templates"].to_dict("records"),
        components=components,
        stage_kind="destination_branch",
        node_filter_key="is_sink",
    )
    pump_slot_options = _build_single_component_options(components, category="pump")
    meter_slot_options = _build_single_component_options(components, category="meter")
    trunk_options = _build_trunk_options(
        templates=data["trunk_templates"].to_dict("records"),
        components=components,
    )

    suction_trunk_options = trunk_options["suction_trunk"]
    discharge_trunk_options = trunk_options["discharge_trunk"]
    allowed_classes = settings.get("allowed_system_diameter_classes") or sorted(
        {
            option["sys_diameter_class"]
            for option in (
                pump_slot_options
                + meter_slot_options
                + suction_trunk_options
                + discharge_trunk_options
            )
            if option.get("sys_diameter_class") not in {"", "none", None}
        }
    )

    route_class_feasibility = _build_route_class_feasibility(
        routes=routes,
        source_options=source_options,
        destination_options=destination_options,
        pump_options=pump_slot_options,
        meter_options=meter_slot_options,
        suction_trunk_options=suction_trunk_options,
        discharge_trunk_options=discharge_trunk_options,
        allowed_classes=allowed_classes,
    )

    mandatory_without_options = [
        route["route_id"]
        for route in routes
        if route["mandatory"] and not route_class_feasibility[route["route_id"]]
    ]
    if mandatory_without_options:
        raise ValueError(
            "Mandatory routes without any viable option chain: "
            f"{mandatory_without_options}."
        )

    return {
        "system_classes": allowed_classes,
        "source_options": source_options,
        "destination_options": destination_options,
        "pump_slot_options": pump_slot_options,
        "meter_slot_options": meter_slot_options,
        "suction_trunk_options": suction_trunk_options,
        "discharge_trunk_options": discharge_trunk_options,
        "route_class_feasibility": route_class_feasibility,
    }


def _build_branch_options(
    *,
    nodes: List[Dict[str, Any]],
    templates: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    stage_kind: str,
    node_filter_key: str,
) -> Dict[str, List[Dict[str, Any]]]:
    options_by_node: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    hoses = [component for component in components if component["category"] == "hose"]
    connectors = [component for component in components if component["category"] == "connector"]
    valves = [component for component in components if component["category"] == "valve"]
    checks = [component for component in components if component["category"] == "check_valve"]
    adaptors = [component for component in components if component["category"] == "adaptor"]

    for node in nodes:
        if not bool(node[node_filter_key]):
            continue

        node_id = node["node_id"]
        node_options: List[Dict[str, Any]] = []

        for template in templates:
            allowed_nodes = set(split_encoded_values(template["allowed_node_ids"]))
            if allowed_nodes and node_id not in allowed_nodes:
                continue

            allowed_hose_diameters = split_encoded_values(template["allowed_hose_diameters"])
            allowed_adaptor_pairs = set(split_encoded_values(template["allowed_adaptor_pairs"]))
            hose_candidates = [
                component
                for component in hoses
                if component_matches_diameter(component, allowed_hose_diameters)
            ]
            valve_candidates: Iterable[Dict[str, Any] | None] = valves if template["require_valve"] else [None]
            check_candidates: Iterable[Dict[str, Any] | None] = checks if template["require_check"] else [None]

            for hose, connector, valve, check in product(
                hose_candidates,
                connectors,
                valve_candidates,
                check_candidates,
            ):
                raw_components = [item for item in [hose, connector, valve, check] if item is not None]
                adapted_components = _attach_branch_adaptors(
                    system_class=hose["sys_diameter_class"],
                    raw_components=raw_components,
                    adaptors=adaptors,
                    allowed_adaptor_pairs=allowed_adaptor_pairs,
                )
                if adapted_components is None:
                    continue

                node_options.append(
                    _compose_option(
                        stage_kind=stage_kind,
                        option_suffix=(
                            f"{node_id}_{template['template_id']}_"
                            f"{'_'.join(component['component_id'] for component in adapted_components)}"
                        ),
                        sys_diameter_class=hose["sys_diameter_class"],
                        components=adapted_components,
                        applies_to=node_id,
                        metadata={
                            "template_id": template["template_id"],
                            "node_id": node_id,
                            "required_flags": {
                                "require_valve": bool(template["require_valve"]),
                                "require_check": bool(template["require_check"]),
                            },
                            "allowed_adaptor_pairs": sorted(allowed_adaptor_pairs),
                            "uses_adaptor": any(
                                component["category"] == "adaptor" for component in adapted_components
                            ),
                        },
                        dominance_key=(
                            stage_kind,
                            node_id,
                            template["template_id"],
                            hose["sys_diameter_class"],
                            tuple(
                                sorted(
                                    Counter(component["category"] for component in adapted_components).items()
                                )
                            ),
                        ),
                    )
                )

        options_by_node[node_id] = sorted(
            prune_dominated_options(node_options),
            key=lambda option: option["option_id"],
        )

    return dict(options_by_node)


def _attach_branch_adaptors(
    *,
    system_class: str,
    raw_components: List[Dict[str, Any]],
    adaptors: List[Dict[str, Any]],
    allowed_adaptor_pairs: set[str],
) -> List[Dict[str, Any]] | None:
    functional_components = [component for component in raw_components if component["category"] != "hose"]
    foreign_classes = sorted(
        {
            component["sys_diameter_class"]
            for component in functional_components
            if component["sys_diameter_class"] != system_class
        }
    )
    adaptor_components: List[Dict[str, Any]] = []

    for foreign_class in foreign_classes:
        adaptor_pair = f"{foreign_class}_to_{system_class}"
        if adaptor_pair not in allowed_adaptor_pairs:
            return None
        adaptor = next(
            (
                component
                for component in adaptors
                if component["component_id"] == f"adaptor_{adaptor_pair}"
            ),
            None,
        )
        if adaptor is None:
            return None
        adaptor_components.append(adaptor)

    return raw_components + adaptor_components


def _build_single_component_options(
    components: List[Dict[str, Any]],
    *,
    category: str,
) -> List[Dict[str, Any]]:
    options: List[Dict[str, Any]] = []
    for component in components:
        if component["category"] != category:
            continue
        option = _compose_option(
            stage_kind=category,
            option_suffix=component["component_id"],
            sys_diameter_class=component["sys_diameter_class"],
            components=[component],
            applies_to=None,
            metadata={
                "component_id": component["component_id"],
                "is_bypass": bool(component["is_bypass"]),
            },
            dominance_key=(
                category,
                component["sys_diameter_class"],
                bool(component["is_bypass"]),
                tuple(sorted(Counter([component["category"]]).items())),
            ),
        )
        option["is_bypass"] = bool(component["is_bypass"])
        option["component_id"] = component["component_id"]
        if category == "meter":
            option["meter_error_pct"] = float(component.get("meter_error_pct") or 0.0)
            option["meter_batch_min_l"] = float(component.get("meter_batch_min_l") or 0.0)
            option["meter_dose_q_max_lpm"] = float(
                component.get("meter_dose_q_max_lpm") or component.get("q_max_lpm") or 0.0
            )
        options.append(option)

    return sorted(prune_dominated_options(options), key=lambda option: option["option_id"])


def _build_trunk_options(
    *,
    templates: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    hoses = [component for component in components if component["category"] == "hose"]
    connectors = [component for component in components if component["category"] == "connector"]
    options_by_stage: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for template in templates:
        allowed_diameters = split_encoded_values(template["allowed_diameters"])
        hose_candidates = [
            component
            for component in hoses
            if component_matches_diameter(component, allowed_diameters)
        ]
        for hose in hose_candidates:
            connector_candidates = [
                component
                for component in connectors
                if component["sys_diameter_class"] == hose["sys_diameter_class"]
            ]
            for connector in connector_candidates:
                options_by_stage[template["stage_kind"]].append(
                    _compose_option(
                        stage_kind=template["stage_kind"],
                        option_suffix=(
                            f"{template['template_id']}_{hose['component_id']}_{connector['component_id']}"
                        ),
                        sys_diameter_class=hose["sys_diameter_class"],
                        components=[hose, connector],
                        applies_to=None,
                        metadata={"template_id": template["template_id"]},
                        dominance_key=(
                            template["stage_kind"],
                            template["template_id"],
                            hose["sys_diameter_class"],
                            tuple(sorted(Counter(["hose", "connector"]).items())),
                        ),
                    )
                )

    return {
        stage_kind: sorted(
            prune_dominated_options(stage_options),
            key=lambda option: option["option_id"],
        )
        for stage_kind, stage_options in options_by_stage.items()
    }


def _compose_option(
    *,
    stage_kind: str,
    option_suffix: str,
    sys_diameter_class: str,
    components: List[Dict[str, Any]],
    applies_to: str | None,
    metadata: Dict[str, Any],
    dominance_key: Any,
) -> Dict[str, Any]:
    component_ids = [component["component_id"] for component in components]
    category_profile = Counter(component["category"] for component in components)

    return {
        "option_id": f"{stage_kind}__{option_suffix}",
        "stage_kind": stage_kind,
        "applies_to": applies_to,
        "sys_diameter_class": sys_diameter_class,
        "component_ids": component_ids,
        "component_counts": dict(Counter(component_ids)),
        "cost": float(sum(float(component["cost"]) for component in components)),
        "q_min_lpm": float(max(float(component["q_min_lpm"]) for component in components)),
        "q_max_lpm": float(min(float(component["q_max_lpm"]) for component in components)),
        "loss_lpm_equiv": float(sum(float(component["loss_lpm_equiv"]) for component in components)),
        "internal_volume_l": float(
            sum(float(component["internal_volume_l"]) for component in components)
        ),
        "category_profile": dict(category_profile),
        "metadata": metadata,
        "dominance_key": dominance_key,
    }


def _build_route_class_feasibility(
    *,
    routes: List[Dict[str, Any]],
    source_options: Dict[str, List[Dict[str, Any]]],
    destination_options: Dict[str, List[Dict[str, Any]]],
    pump_options: List[Dict[str, Any]],
    meter_options: List[Dict[str, Any]],
    suction_trunk_options: List[Dict[str, Any]],
    discharge_trunk_options: List[Dict[str, Any]],
    allowed_classes: List[str],
) -> Dict[str, List[str]]:
    feasible_classes: Dict[str, List[str]] = {}
    pump_classes = _index_classes({"pump": pump_options})
    meter_classes = _index_classes({"meter": meter_options})
    suction_classes = _index_classes({"suction_trunk": suction_trunk_options})
    discharge_classes = _index_classes({"discharge_trunk": discharge_trunk_options})

    for route in routes:
        route_id = route["route_id"]
        if not route_respects_frozen_rules(route["source"], route["sink"]):
            feasible_classes[route_id] = []
            continue

        required_flow = float(route["q_min_delivered_lpm"])
        route_feasible: List[str] = []
        for system_class in allowed_classes:
            has_source = bool(source_options.get(route["source"]))
            has_destination = bool(destination_options.get(route["sink"]))
            has_suction = system_class in suction_classes.get("suction_trunk", set())
            has_discharge = system_class in discharge_classes.get("discharge_trunk", set())
            has_pump = any(
                option["sys_diameter_class"] == system_class and option["q_max_lpm"] >= required_flow
                for option in pump_options
            )
            has_meter = any(
                option["sys_diameter_class"] == system_class
                and meter_option_allowed_for_route(route, option)
                for option in meter_options
            )
            if has_source and has_destination and has_suction and has_discharge and has_pump and has_meter:
                route_feasible.append(system_class)

        feasible_classes[route_id] = route_feasible

    return feasible_classes


def _index_classes(options_by_key: Dict[str, List[Dict[str, Any]]]) -> Dict[str, set[str]]:
    class_index: Dict[str, set[str]] = defaultdict(set)
    for key, options in options_by_key.items():
        for option in options:
            class_index[key].add(option["sys_diameter_class"])
    return dict(class_index)
