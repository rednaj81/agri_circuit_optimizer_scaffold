from __future__ import annotations

from math import ceil, hypot, isnan
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
        settings=settings,
        stage_kind="source_branch",
        node_filter_key="is_source",
    )
    destination_options = _build_branch_options(
        nodes=nodes,
        templates=data["destination_branch_templates"].to_dict("records"),
        components=components,
        settings=settings,
        stage_kind="destination_branch",
        node_filter_key="is_sink",
    )
    pump_slot_options = _build_single_component_options(components, settings=settings, category="pump")
    meter_slot_options = _build_single_component_options(components, settings=settings, category="meter")
    trunk_options = _build_trunk_options(
        templates=data["trunk_templates"].to_dict("records"),
        components=components,
        settings=settings,
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
    settings: Dict[str, Any],
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
        branch_role = str(
            "suction" if stage_kind == "source_branch" else "discharge"
        )
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
                raw_components = [item for item in [connector, valve, check] if item is not None]
                modular_components, hose_length_m, hose_modules_used = _expand_hose_components(
                    hose_component=hose,
                    node=node,
                    settings=settings,
                    stage_kind=stage_kind,
                )
                raw_components = modular_components + raw_components
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
                            "branch_role": str(template.get("branch_role") or branch_role),
                            "node_operational_role": str(node.get("operational_role") or ""),
                            "required_flags": {
                                "require_valve": bool(template["require_valve"]),
                                "require_check": bool(template["require_check"]),
                            },
                            "allowed_adaptor_pairs": sorted(allowed_adaptor_pairs),
                            "uses_adaptor": any(
                                component["category"] == "adaptor" for component in adapted_components
                            ),
                            "contains_valve": any(
                                component["category"] == "valve" for component in adapted_components
                            ),
                            "selectively_closable": any(
                                component["category"] == "valve" for component in adapted_components
                            ),
                            "hose_length_m": hose_length_m,
                            "hose_modules_used": hose_modules_used,
                        },
                        dominance_key=(
                            stage_kind,
                            node_id,
                            template["template_id"],
                            hose["sys_diameter_class"],
                            tuple(
                                sorted(
                                    component["component_id"]
                                    for component in adapted_components
                                    if bool(component.get("is_extra", False))
                                )
                            ),
                            tuple(
                                sorted(
                                    Counter(component["category"] for component in adapted_components).items()
                                )
                            ),
                        ),
                        settings=settings,
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
    settings: Dict[str, Any],
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
                "hose_length_m": _float_or_default(component.get("hose_length_m")),
                "hose_modules_used": int(round(_float_or_default(component.get("hose_length_m")))),
            },
            dominance_key=(
                category,
                component["sys_diameter_class"],
                bool(component["is_bypass"]),
                tuple(
                    [component["component_id"]] if bool(component.get("is_extra", False)) else []
                ),
                tuple(sorted(Counter([component["category"]]).items())),
            ),
            settings=settings,
        )
        option["is_bypass"] = bool(component["is_bypass"])
        option["component_id"] = component["component_id"]
        if category == "meter":
            option["meter_error_pct"] = _float_or_default(component.get("meter_error_pct"))
            option["meter_batch_min_l"] = _float_or_default(component.get("meter_batch_min_l"))
            option["meter_dose_q_max_lpm"] = _float_or_default(
                component.get("meter_dose_q_max_lpm"),
                default=_float_or_default(component.get("q_max_lpm")),
            )
        options.append(option)

    return sorted(prune_dominated_options(options), key=lambda option: option["option_id"])


def _build_trunk_options(
    *,
    templates: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    settings: Dict[str, Any],
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
            consume_connector = _trunk_template_consumes_connector(template, settings)
            connector_candidates = [None]
            if consume_connector:
                connector_candidates = [
                    component
                    for component in connectors
                    if component["sys_diameter_class"] == hose["sys_diameter_class"]
                ]
            for connector in connector_candidates:
                modular_components, hose_length_m, hose_modules_used = _expand_trunk_hose_components(
                    hose_component=hose,
                    settings=settings,
                    stage_kind=template["stage_kind"],
                )
                option_components = list(modular_components)
                if connector is not None:
                    option_components.append(connector)
                options_by_stage[template["stage_kind"]].append(
                    _compose_option(
                        stage_kind=template["stage_kind"],
                        option_suffix=(
                            f"{template['template_id']}_{hose['component_id']}"
                            + (f"_{connector['component_id']}" if connector is not None else "")
                        ),
                        sys_diameter_class=hose["sys_diameter_class"],
                        components=option_components,
                        applies_to=None,
                        metadata={
                            "template_id": template["template_id"],
                            "hose_length_m": hose_length_m,
                            "hose_modules_used": hose_modules_used,
                            "consume_connector": consume_connector,
                        },
                        dominance_key=(
                            template["stage_kind"],
                            template["template_id"],
                            hose["sys_diameter_class"],
                            tuple(
                                sorted(
                                    component["component_id"]
                                    for component in option_components
                                    if bool(component.get("is_extra", False))
                                )
                            ),
                            tuple(
                                sorted(
                                    Counter(component["category"] for component in option_components).items()
                                )
                            ),
                        ),
                        settings=settings,
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
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    component_ids = [component["component_id"] for component in components]
    category_profile = Counter(component["category"] for component in components)
    hose_length_m = float(
        _float_or_default(metadata.get("hose_length_m"))
        or sum(_float_or_default(component.get("hose_length_m")) for component in components)
    )
    hose_modules_used = int(
        metadata.get("hose_modules_used")
        or round(sum(_float_or_default(component.get("hose_length_m")) for component in components))
    )
    q_local_base_lpm = float(min(float(component["q_max_lpm"]) for component in components))
    bottleneck_component = min(
        components,
        key=lambda component: float(component["q_max_lpm"]),
    )
    q_max_effective, local_loss_lpm_equiv = _compute_effective_qmax(
        components=components,
        q_local_base_lpm=q_local_base_lpm,
        hose_length_m=hose_length_m,
        settings=settings,
    )
    base_component_counts = Counter(
        component["component_id"] for component in components if not bool(component.get("is_extra", False))
    )
    extra_component_counts = Counter(
        component["component_id"] for component in components if bool(component.get("is_extra", False))
    )

    return {
        "option_id": f"{stage_kind}__{option_suffix}",
        "stage_kind": stage_kind,
        "applies_to": applies_to,
        "sys_diameter_class": sys_diameter_class,
        "component_ids": component_ids,
        "component_counts": dict(Counter(component_ids)),
        "cost": float(sum(float(component["cost"]) for component in components)),
        "q_min_lpm": float(max(float(component["q_min_lpm"]) for component in components)),
        "q_max_lpm": q_max_effective,
        "loss_lpm_equiv": local_loss_lpm_equiv,
        "internal_volume_l": float(
            sum(float(component["internal_volume_l"]) for component in components)
        ),
        "hose_length_m": hose_length_m,
        "hose_modules_used": hose_modules_used,
        "q_local_base_lpm": q_local_base_lpm,
        "q_local_effective_lpm": q_max_effective,
        "bottleneck_component_id": bottleneck_component["component_id"],
        "base_component_counts": dict(base_component_counts),
        "extra_component_counts": dict(extra_component_counts),
        "category_profile": dict(category_profile),
        "branch_role": metadata.get("branch_role"),
        "contains_valve": bool(metadata.get("contains_valve", False)),
        "selectively_closable": bool(metadata.get("selectively_closable", False)),
        "metadata": {
            **metadata,
            "hydraulic_mode": settings.get("hydraulic_loss_mode", "additive_lpm"),
            "q_local_base_lpm": q_local_base_lpm,
            "q_local_effective_lpm": q_max_effective,
            "bottleneck_component_id": bottleneck_component["component_id"],
            "base_component_counts": dict(base_component_counts),
            "extra_component_counts": dict(extra_component_counts),
        },
        "dominance_key": dominance_key,
    }


def _expand_hose_components(
    *,
    hose_component: Dict[str, Any],
    node: Dict[str, Any],
    settings: Dict[str, Any],
    stage_kind: str,
) -> tuple[List[Dict[str, Any]], float, int]:
    if settings.get("hydraulic_loss_mode", "additive_lpm") != "bottleneck_plus_length":
        return [hose_component], _float_or_default(hose_component.get("hose_length_m")), 1

    required_hose_m = _compute_branch_hose_length(node=node, settings=settings, stage_kind=stage_kind)
    module_m = _float_or_default(
        hose_component.get("hose_length_m"),
        default=_float_or_default(settings.get("hose_module_m"), default=1.0),
    )
    hose_modules_used = max(1, int(ceil(required_hose_m / module_m)))
    hose_length_m = hose_modules_used * module_m
    return [hose_component] * hose_modules_used, hose_length_m, hose_modules_used


def _expand_trunk_hose_components(
    *,
    hose_component: Dict[str, Any],
    settings: Dict[str, Any],
    stage_kind: str,
) -> tuple[List[Dict[str, Any]], float, int]:
    if settings.get("hydraulic_loss_mode", "additive_lpm") != "bottleneck_plus_length":
        return [hose_component], _float_or_default(hose_component.get("hose_length_m")), 1

    required_hose_m = _float_or_default(
        settings.get(f"trunk_length_{stage_kind.replace('_trunk', '')}_m")
    )
    module_m = _float_or_default(
        hose_component.get("hose_length_m"),
        default=_float_or_default(settings.get("hose_module_m"), default=1.0),
    )
    hose_modules_used = max(1, int(ceil(required_hose_m / module_m)))
    hose_length_m = hose_modules_used * module_m
    return [hose_component] * hose_modules_used, hose_length_m, hose_modules_used


def _compute_branch_hose_length(
    *,
    node: Dict[str, Any],
    settings: Dict[str, Any],
    stage_kind: str,
) -> float:
    manifold_prefix = "suction" if stage_kind == "source_branch" else "discharge"
    manifold_x = _float_or_default(settings.get(f"{manifold_prefix}_manifold_x_m"))
    manifold_y = _float_or_default(settings.get(f"{manifold_prefix}_manifold_y_m"))
    distance = hypot(
        _float_or_default(node.get("x_m")) - manifold_x,
        _float_or_default(node.get("y_m")) - manifold_y,
    )
    return max(
        _float_or_default(settings.get("minimum_branch_hose_m")),
        distance * _float_or_default(settings.get("bend_factor"), default=1.0)
        + _float_or_default(settings.get("connection_margin_m")),
    )


def _compute_effective_qmax(
    *,
    components: List[Dict[str, Any]],
    q_local_base_lpm: float,
    hose_length_m: float,
    settings: Dict[str, Any],
) -> tuple[float, float]:
    if settings.get("hydraulic_loss_mode", "additive_lpm") != "bottleneck_plus_length":
        return q_local_base_lpm, float(sum(float(component["loss_lpm_equiv"]) for component in components))

    hose_loss_pct_per_m = max(
        [
            _float_or_default(component.get("hose_loss_pct_per_m"))
            for component in components
            if component["category"] == "hose"
        ]
        or [0.0]
    )
    length_factor = max(
        _float_or_default(settings.get("min_length_factor"), default=0.1),
        1.0 - hose_loss_pct_per_m * hose_length_m,
    )
    q_local_effective = q_local_base_lpm * length_factor
    return q_local_effective, q_local_base_lpm - q_local_effective


def _trunk_template_consumes_connector(template: Dict[str, Any], settings: Dict[str, Any]) -> bool:
    if "consume_connector" in template:
        return _bool_or_default(template["consume_connector"])
    if settings.get("hydraulic_loss_mode", "additive_lpm") == "bottleneck_plus_length":
        return _bool_or_default(settings.get("maquette_trunks_consume_connectors"), default=True)
    return True


def _float_or_default(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float(default)
    if isnan(numeric):
        return float(default)
    return numeric


def _bool_or_default(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and isnan(value):
            return default
        return bool(int(value))
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n", ""}:
            return False
    return default


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
