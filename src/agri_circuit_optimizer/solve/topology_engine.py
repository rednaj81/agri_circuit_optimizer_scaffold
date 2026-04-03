from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from math import isnan
from typing import Any, Dict

from agri_circuit_optimizer.preprocess.compatibility import split_encoded_values
from agri_circuit_optimizer.preprocess.feasibility import meter_compatibility


def is_fixed_topology_mode(data: Dict[str, Any]) -> bool:
    return data.get("edges") is not None and (
        data["settings"].get("topology_family", "star_manifolds") != "star_manifolds"
    )


def dry_run_fixed_topology(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = build_fixed_topology_payload(data)
    route_checks = {
        route["route_id"]: validate_route_on_fixed_topology(route, payload)
        for route in payload["routes"]
    }
    core_group = payload["rules"]["core_routes_group"]
    return {
        "topology_family": payload["topology_family"],
        "installed_edges": len(payload["installed_edges"]),
        "mandatory_core_routes_with_active_path": sum(
            1
            for route in payload["routes"]
            if bool(route["mandatory"])
            and route["route_group"] == core_group
            and bool(route_checks[route["route_id"]]["served"])
        ),
        "mandatory_routes_with_active_path": sum(
            1
            for route in payload["routes"]
            if bool(route["mandatory"]) and bool(route_checks[route["route_id"]]["served"])
        ),
    }


def solve_fixed_topology_case(data: Dict[str, Any], *, solver_name: str) -> Dict[str, Any]:
    payload = build_fixed_topology_payload(data)
    route_results = [
        validate_route_on_fixed_topology(route, payload)
        for route in payload["routes"]
    ]
    bom = build_fixed_topology_bom(payload)
    comparison = compare_family_solutions({payload["topology_family"]: {"summary": {}, "bom": bom, "routes": route_results}})
    summary = build_fixed_topology_summary(payload, route_results, bom, solver_name)
    return {
        "summary": summary,
        "bom": bom,
        "routes": route_results,
        "hydraulics": [item["hydraulics"] for item in route_results if item["served"]],
        "topology": {
            "topology_family": payload["topology_family"],
            "installed_edge_ids": sorted(payload["installed_edges"]),
            "topology_rules": payload["rules"],
        },
        "comparison": comparison,
    }


def compare_family_solutions(solutions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    family_rows: Dict[str, Dict[str, Any]] = {}
    for family, solution in solutions.items():
        summary = solution.get("summary", {})
        bom = solution.get("bom", [])
        family_rows[family] = {
            "topology_family": family,
            "total_material_cost": float(summary.get("total_material_cost", _sum_total_cost(bom))),
            "hose_total_used_m": float(summary.get("hose_total_used_m", _sum_hose_length(bom))),
            "tee_total_used": int(summary.get("tee_total_used", _sum_category_qty(bom, "connector"))),
            "solenoid_total": int(summary.get("solenoid_total", _sum_category_qty(bom, "valve"))),
            "pump_total": int(_sum_category_qty(bom, "pump")),
            "meter_total": int(_sum_category_qty(bom, "meter")),
            "routes_served": int(summary.get("routes_served", _sum_served_routes(solution.get("routes", [])))),
            "mandatory_routes_served": int(
                summary.get("mandatory_routes_served", _sum_mandatory_served(solution.get("routes", [])))
            ),
        }
    return {
        "families": family_rows,
    }


def build_fixed_topology_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    component_index = {
        component["component_id"]: component
        for component in data["components"].to_dict("records")
    }
    node_index = {node["node_id"]: node for node in data["nodes"].to_dict("records")}
    routes = data["routes"].to_dict("records")
    edges_frame = data["edges"]
    edges: Dict[str, Dict[str, Any]] = {}
    adjacency: Dict[str, list[Dict[str, Any]]] = defaultdict(list)
    incident_edges: Dict[str, list[str]] = defaultdict(list)

    for edge in edges_frame.to_dict("records"):
        component_ids = split_encoded_values(edge["component_ids"])
        components = [component_index[component_id] for component_id in component_ids]
        hose_length_m = float(edge.get("length_m") or 0.0)
        if hose_length_m <= 0:
            hose_length_m = sum(_float_or_default(component.get("hose_length_m")) for component in components)
        edge_summary = summarize_edge_hydraulics(
            edge=edge,
            components=components,
            hose_length_m=hose_length_m,
            settings=data["settings"],
        )
        edge_record = {
            **edge,
            "component_ids_list": component_ids,
            "components": components,
            "hose_length_m": hose_length_m,
            **edge_summary,
        }
        edges[edge["edge_id"]] = edge_record
        incident_edges[edge["from_node"]].append(edge["edge_id"])
        incident_edges[edge["to_node"]].append(edge["edge_id"])
        if not bool(edge["default_installed"]):
            continue
        for arc in _edge_to_arcs(edge_record):
            adjacency[arc["from_node"]].append(arc)

    return {
        "topology_family": data["settings"]["topology_family"],
        "settings": data["settings"],
        "rules": data.get("topology_rules") or {
            "core_routes_group": "core",
            "service_routes_group": "service",
            "max_active_pumps_per_route": 1,
            "max_reading_meters_per_route": 1,
            "allow_idle_pumps_on_path": False,
            "allow_idle_meters_on_path": False,
            "allow_passive_bypass_on_path": True,
            "enforce_simple_path": True,
            "allow_cycle_if_inactive": True,
            "treat_extra_open_branch_as_invalid": True,
        },
        "routes": routes,
        "nodes": node_index,
        "edges": edges,
        "installed_edges": {
            edge_id for edge_id, edge in edges.items() if bool(edge.get("default_installed", False))
        },
        "adjacency": dict(adjacency),
        "incident_edges": {node_id: sorted(edge_ids) for node_id, edge_ids in incident_edges.items()},
    }


def validate_route_on_fixed_topology(route: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    rules = payload["rules"]
    path_candidates = _enumerate_route_paths(route, payload)
    best_result: Dict[str, Any] | None = None
    failure_reasons: list[str] = []

    for path in path_candidates:
        selectivity = _evaluate_path_selectivity(path, payload)
        if not bool(selectivity["selective_route_realizable"]):
            failure_reasons.append("path_selectivity")
            continue

        pump_candidates = _collect_component_candidates(path, payload, "pump")
        pump_choices = _build_pump_choices(route, rules, pump_candidates)
        if not pump_choices:
            failure_reasons.append("pump_selection")
            continue

        meter_candidates = _collect_component_candidates(path, payload, "meter")
        meter_choices = _build_meter_choices(route, rules, meter_candidates)
        if not meter_choices:
            failure_reasons.append("meter_selection")
            continue

        for active_pumps in pump_choices:
            for reading_meter in meter_choices:
                evaluation = _evaluate_path_operation(
                    route=route,
                    path=path,
                    payload=payload,
                    active_pumps=active_pumps,
                    reading_meter=reading_meter,
                    selectivity=selectivity,
                )
                if not evaluation["served"]:
                    failure_reasons.append(evaluation["failure_reason"])
                    continue
                if best_result is None or _route_result_rank(evaluation) > _route_result_rank(best_result):
                    best_result = evaluation

    if best_result is not None:
        return best_result

    return {
        "route_id": route["route_id"],
        "source": route["source"],
        "sink": route["sink"],
        "mandatory": bool(route["mandatory"]),
        "route_group": route.get("route_group", "core"),
        "measurement_required": bool(route["measurement_required"]),
        "served": False,
        "failure_reason": failure_reasons[0] if failure_reasons else "no_active_path",
        "topology_family": payload["topology_family"],
        "active_path_edge_ids": [],
        "active_path_arc_ids": [],
        "active_path_nodes": [],
        "source_branch_selected": None,
        "discharge_branch_selected": None,
        "selective_route_realizable": False,
        "extra_open_branch_conflict": True,
        "open_suction_branch_count": 0,
        "open_discharge_branch_count": 0,
        "selected_meter_id": None,
        "meter_component_id": None,
        "meter_is_bypass": False,
        "meter_q_range_ok": False,
        "meter_dose_ok": False,
        "meter_error_ok": False,
        "hydraulics": {
            "route_id": route["route_id"],
            "system_class": _infer_route_system_class([], payload),
            "flow_delivered_lpm": 0.0,
            "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
            "total_loss_lpm_equiv": 0.0,
            "route_effective_q_max_lpm": 0.0,
            "hydraulic_slack_lpm": -float(route["q_min_delivered_lpm"]),
            "gargalo_principal": "no_path",
            "bottleneck_component_id": None,
            "route_hose_total_m": 0.0,
            "hydraulic_mode": payload["settings"].get("hydraulic_loss_mode", "additive_lpm"),
            "active_path_edge_ids": [],
        },
    }


def build_fixed_topology_summary(
    payload: Dict[str, Any],
    route_results: list[Dict[str, Any]],
    bom: list[Dict[str, Any]],
    solver_name: str,
) -> Dict[str, Any]:
    core_group = payload["rules"]["core_routes_group"]
    service_group = payload["rules"]["service_routes_group"]
    core_mandatory_failed = [
        route["route_id"]
        for route in route_results
        if bool(route["mandatory"]) and route["route_group"] == core_group and not bool(route["served"])
    ]
    return {
        "solver": solver_name,
        "solver_status": "ok" if not core_mandatory_failed else "infeasible",
        "termination_condition": "fixed_topology_validated"
        if not core_mandatory_failed
        else "mandatory_core_routes_unserved",
        "topology_family": payload["topology_family"],
        "system_class": _infer_route_system_class(payload["installed_edges"], payload),
        "routes_served": sum(1 for route in route_results if bool(route["served"])),
        "mandatory_routes_served": sum(
            1 for route in route_results if bool(route["mandatory"]) and bool(route["served"])
        ),
        "core_routes_served": sum(
            1 for route in route_results if route["route_group"] == core_group and bool(route["served"])
        ),
        "service_routes_served": sum(
            1 for route in route_results if route["route_group"] == service_group and bool(route["served"])
        ),
        "core_mandatory_routes_served": sum(
            1
            for route in route_results
            if bool(route["mandatory"]) and route["route_group"] == core_group and bool(route["served"])
        ),
        "service_mandatory_routes_served": sum(
            1
            for route in route_results
            if bool(route["mandatory"]) and route["route_group"] == service_group and bool(route["served"])
        ),
        "mandatory_core_routes_unserved": core_mandatory_failed,
        "total_material_cost": round(_sum_total_cost(bom), 3),
        "objective_value": round(
            _sum_total_cost(bom)
            - payload["settings"].get("optional_route_reward", 0.0)
            * sum(
                float(route.get("weight", 0.0))
                for route in route_results
                if bool(route["served"]) and not bool(route["mandatory"])
            ),
            3,
        ),
        **_inventory_summary_for_bom(bom),
    }


def build_fixed_topology_bom(payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    component_qty: Counter[str] = Counter()
    role_qty: Dict[str, Dict[str, int]] = defaultdict(lambda: {"suction": 0, "discharge": 0, "other": 0})
    component_index: Dict[str, Dict[str, Any]] = {}

    for edge_id in sorted(payload["installed_edges"]):
        edge = payload["edges"][edge_id]
        role = _edge_role_for_bom(edge)
        for component in edge["components"]:
            component_id = component["component_id"]
            component_qty[component_id] += 1
            role_qty[component_id][role] += 1
            component_index[component_id] = component

    bom = []
    for component_id, qty in sorted(component_qty.items()):
        component = component_index[component_id]
        bom.append(
            {
                "component_id": component_id,
                "category": component["category"],
                "qty": int(qty),
                "unit_cost": float(component["cost"]),
                "total_cost": round(float(component["cost"]) * int(qty), 3),
                "is_extra": bool(component.get("is_extra", False)),
                "extra_penalty_group": component.get("extra_penalty_group", ""),
                "hose_length_m": _float_or_default(component.get("hose_length_m")),
                "qty_suction": int(role_qty[component_id]["suction"]),
                "qty_discharge": int(role_qty[component_id]["discharge"]),
                "qty_other": int(role_qty[component_id]["other"]),
            }
        )
    return bom


def summarize_edge_hydraulics(
    *,
    edge: Dict[str, Any],
    components: list[Dict[str, Any]],
    hose_length_m: float,
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    if not components:
        return {
            "q_max_lpm": 9999.0,
            "q_min_lpm": 0.0,
            "loss_lpm_equiv": 0.0,
            "bottleneck_component_id": None,
        }
    q_local_base_lpm = min(float(component["q_max_lpm"]) for component in components)
    bottleneck_component = min(components, key=lambda component: float(component["q_max_lpm"]))
    hydraulic_mode = str(settings.get("hydraulic_loss_mode", "additive_lpm")).strip() or "additive_lpm"
    if hydraulic_mode == "bottleneck_plus_length":
        hose_loss_pct_per_m = max(
            [_float_or_default(component.get("hose_loss_pct_per_m")) for component in components]
            or [0.0]
        )
        effective_factor = max(
            _float_or_default(settings.get("min_length_factor"), default=0.1),
            1.0 - hose_loss_pct_per_m * max(hose_length_m, 0.0),
        )
        effective_qmax = q_local_base_lpm * effective_factor
        loss_lpm_equiv = q_local_base_lpm - effective_qmax
    else:
        effective_qmax = q_local_base_lpm
        loss_lpm_equiv = sum(float(component["loss_lpm_equiv"]) for component in components)
    return {
        "q_max_lpm": float(effective_qmax),
        "q_min_lpm": max(float(component["q_min_lpm"]) for component in components),
        "loss_lpm_equiv": float(loss_lpm_equiv),
        "bottleneck_component_id": bottleneck_component["component_id"],
    }


def _enumerate_route_paths(route: Dict[str, Any], payload: Dict[str, Any]) -> list[Dict[str, Any]]:
    rules = payload["rules"]
    source = route["source"]
    sink = route["sink"]
    max_depth = max(1, len(payload["installed_edges"]) + 1)
    paths: list[Dict[str, Any]] = []

    def search(
        node_id: str,
        path_arcs: list[Dict[str, Any]],
        visited_nodes: list[str],
        used_groups: set[str],
    ) -> None:
        if node_id == sink:
            paths.append(
                {
                    "arc_ids": [arc["arc_id"] for arc in path_arcs],
                    "edge_ids": [arc["edge_id"] for arc in path_arcs],
                    "nodes": list(visited_nodes),
                }
            )
            return
        if len(path_arcs) >= max_depth:
            return
        for arc in payload["adjacency"].get(node_id, []):
            edge = payload["edges"][arc["edge_id"]]
            group_id = str(edge.get("group_id", "")).strip()
            if group_id and group_id in used_groups:
                continue
            next_node = arc["to_node"]
            if bool(rules["enforce_simple_path"]) and next_node in visited_nodes:
                continue
            search(
                next_node,
                path_arcs + [arc],
                visited_nodes + [next_node],
                used_groups | ({group_id} if group_id else set()),
            )

    search(source, [], [source], set())
    return paths


def _edge_to_arcs(edge: Dict[str, Any]) -> list[Dict[str, Any]]:
    direction_mode = str(edge.get("direction_mode", "forward_only")).strip() or "forward_only"
    arcs = []
    if direction_mode in {"forward_only", "bidirectional", "conditional"}:
        arcs.append(
            {
                "arc_id": edge["edge_id"],
                "edge_id": edge["edge_id"],
                "from_node": edge["from_node"],
                "to_node": edge["to_node"],
                "direction": "forward",
            }
        )
    if direction_mode in {"reverse_only", "bidirectional"}:
        arcs.append(
            {
                "arc_id": f"{edge['edge_id']}:rev",
                "edge_id": edge["edge_id"],
                "from_node": edge["to_node"],
                "to_node": edge["from_node"],
                "direction": "reverse",
            }
        )
    return arcs


def _evaluate_path_selectivity(path: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    path_edge_ids = set(path["edge_ids"])
    conflicting_edges = []
    if bool(payload["rules"].get("treat_extra_open_branch_as_invalid", True)):
        for node_id in path["nodes"]:
            for edge_id in payload["incident_edges"].get(node_id, []):
                if edge_id in path_edge_ids:
                    continue
                edge = payload["edges"][edge_id]
                edge_kind = str(edge.get("edge_kind", "")).strip()
                branch_like_edge = "tap" in edge_kind or bool(str(edge.get("branch_role", "")).strip())
                if (
                    branch_like_edge
                    and bool(edge.get("can_be_active", False))
                    and not bool(edge.get("must_be_closed_if_unused", False))
                ):
                    conflicting_edges.append(edge_id)
    source_edge = path["edge_ids"][0] if path["edge_ids"] else None
    sink_edge = path["edge_ids"][-1] if path["edge_ids"] else None
    selectable = bool(path["edge_ids"]) and not conflicting_edges
    return {
        "source_branch_selected": source_edge,
        "discharge_branch_selected": sink_edge,
        "open_suction_branch_count": 1 if source_edge else 0,
        "open_discharge_branch_count": 1 if sink_edge else 0,
        "extra_open_branch_conflict": bool(conflicting_edges),
        "selective_route_realizable": selectable,
        "conflicting_source_nodes": conflicting_edges,
        "conflicting_sink_nodes": conflicting_edges,
    }


def _collect_component_candidates(
    path: Dict[str, Any],
    payload: Dict[str, Any],
    category: str,
) -> list[Dict[str, Any]]:
    candidates: list[Dict[str, Any]] = []
    for edge_id in path["edge_ids"]:
        edge = payload["edges"][edge_id]
        for component in edge["components"]:
            if component["category"] == category:
                candidates.append({"edge_id": edge_id, "component": component})
    return candidates


def _build_pump_choices(
    route: Dict[str, Any],
    rules: Dict[str, Any],
    pump_candidates: list[Dict[str, Any]],
) -> list[list[Dict[str, Any]]]:
    max_active = int(route.get("max_active_pumps") or rules["max_active_pumps_per_route"])
    min_active = 1 if bool(route.get("need_pump", False)) else 0
    if min_active == 0:
        if pump_candidates and not bool(rules.get("allow_idle_pumps_on_path", False)):
            return []
        return [[]]
    if not pump_candidates:
        return []
    if not bool(rules.get("allow_idle_pumps_on_path", False)) and len(pump_candidates) > max_active:
        return []
    upper = min(max_active, len(pump_candidates))
    choices = []
    for active_count in range(min_active, upper + 1):
        choices.extend([list(combo) for combo in combinations(pump_candidates, active_count)])
    return choices


def _build_meter_choices(
    route: Dict[str, Any],
    rules: Dict[str, Any],
    meter_candidates: list[Dict[str, Any]],
) -> list[Dict[str, Any] | None]:
    measurement_required = bool(route.get("measurement_required", False))
    if not meter_candidates:
        return [] if measurement_required else [None]

    compatible_candidates = [
        candidate
        for candidate in meter_candidates
        if bool(meter_compatibility(route, candidate["component"])["compatible"])
    ]
    if measurement_required:
        if not compatible_candidates:
            return []
        if not bool(rules.get("allow_idle_meters_on_path", False)) and len(meter_candidates) > 1:
            return []
        return compatible_candidates[: int(rules["max_reading_meters_per_route"])]

    passive_bypass_present = any(bool(candidate["component"].get("is_bypass", False)) for candidate in meter_candidates)
    if passive_bypass_present and not bool(rules.get("allow_passive_bypass_on_path", True)):
        return []
    if meter_candidates and not bool(rules.get("allow_idle_meters_on_path", False)):
        return []
    return [None]


def _evaluate_path_operation(
    *,
    route: Dict[str, Any],
    path: Dict[str, Any],
    payload: Dict[str, Any],
    active_pumps: list[Dict[str, Any]],
    reading_meter: Dict[str, Any] | None,
    selectivity: Dict[str, Any],
) -> Dict[str, Any]:
    meter_flags = (
        meter_compatibility(route, reading_meter["component"]) if reading_meter is not None else _default_meter_flags(route)
    )
    hydraulics = _summarize_path_hydraulics(
        route=route,
        path=path,
        payload=payload,
        active_pumps=active_pumps,
        reading_meter=reading_meter,
    )
    if not bool(hydraulics["hydraulic_ok"]):
        return {
            "served": False,
            "failure_reason": "hydraulic_capacity",
        }
    selected_meter_component = reading_meter["component"]["component_id"] if reading_meter is not None else None
    selected_pump_component = (
        active_pumps[0]["component"]["component_id"] if active_pumps else None
    )
    return {
        "route_id": route["route_id"],
        "source": route["source"],
        "sink": route["sink"],
        "mandatory": bool(route["mandatory"]),
        "route_group": route.get("route_group", "core"),
        "measurement_required": bool(route["measurement_required"]),
        "served": True,
        "failure_reason": None,
        "topology_family": payload["topology_family"],
        "active_path_edge_ids": list(path["edge_ids"]),
        "active_path_arc_ids": list(path["arc_ids"]),
        "active_path_nodes": list(path["nodes"]),
        "pump_component_id": selected_pump_component,
        "selected_meter_id": selected_meter_component,
        "meter_component_id": selected_meter_component,
        "meter_is_bypass": bool(meter_flags["meter_is_bypass"]),
        "meter_q_range_ok": bool(meter_flags["q_range_ok"]),
        "meter_dose_ok": bool(meter_flags["dose_ok"]),
        "meter_error_ok": bool(meter_flags["error_ok"]),
        "source_branch_selected": selectivity["source_branch_selected"],
        "discharge_branch_selected": selectivity["discharge_branch_selected"],
        "selective_route_realizable": bool(selectivity["selective_route_realizable"]),
        "extra_open_branch_conflict": bool(selectivity["extra_open_branch_conflict"]),
        "open_suction_branch_count": int(selectivity["open_suction_branch_count"]),
        "open_discharge_branch_count": int(selectivity["open_discharge_branch_count"]),
        "conflicting_source_nodes": list(selectivity["conflicting_source_nodes"]),
        "conflicting_sink_nodes": list(selectivity["conflicting_sink_nodes"]),
        "flow_delivered_lpm": float(
            max(route["q_min_delivered_lpm"], hydraulics["q_min_required_lpm"])
        ),
        "q_min_required_lpm": float(route["q_min_delivered_lpm"]),
        "hydraulic_mode": hydraulics["hydraulic_mode"],
        "hydraulics": {
            **hydraulics,
            "route_id": route["route_id"],
        },
    }


def _summarize_path_hydraulics(
    *,
    route: Dict[str, Any],
    path: Dict[str, Any],
    payload: Dict[str, Any],
    active_pumps: list[Dict[str, Any]],
    reading_meter: Dict[str, Any] | None,
) -> Dict[str, Any]:
    edges = [payload["edges"][edge_id] for edge_id in path["edge_ids"]]
    hydraulic_mode = payload["settings"].get("hydraulic_loss_mode", "additive_lpm")
    required_flow = float(route.get("q_min_delivered_lpm", 0.0))
    total_loss = sum(float(edge["loss_lpm_equiv"]) for edge in edges)
    edge_capacities = {edge["edge_id"]: float(edge["q_max_lpm"]) for edge in edges}
    active_pump_capacity = min(
        [float(candidate["component"]["q_max_lpm"]) for candidate in active_pumps] or [9999.0]
    )
    if hydraulic_mode == "bottleneck_plus_length":
        route_capacity = min(list(edge_capacities.values()) + [active_pump_capacity])
    else:
        route_capacity = min(
            list(edge_capacities.values())
            + [max(0.0, active_pump_capacity - total_loss)]
        )
    bottleneck_edge_id = min(edge_capacities, key=lambda edge_id: edge_capacities[edge_id]) if edge_capacities else None
    bottleneck_component_id = (
        payload["edges"][bottleneck_edge_id]["bottleneck_component_id"] if bottleneck_edge_id else None
    )
    return {
        "system_class": _infer_route_system_class(path["edge_ids"], payload),
        "flow_delivered_lpm": required_flow,
        "q_min_required_lpm": required_flow,
        "total_loss_lpm_equiv": float(total_loss),
        "route_effective_q_max_lpm": float(route_capacity),
        "hydraulic_slack_lpm": float(route_capacity - required_flow),
        "hydraulic_ok": route_capacity >= required_flow - 1e-9,
        "gargalo_principal": bottleneck_edge_id or "none",
        "bottleneck_component_id": bottleneck_component_id,
        "route_hose_total_m": float(sum(edge["hose_length_m"] for edge in edges)),
        "hydraulic_mode": hydraulic_mode,
        "active_path_edge_ids": list(path["edge_ids"]),
        "reading_meter_component_id": reading_meter["component"]["component_id"] if reading_meter else None,
    }


def _edge_role_for_bom(edge: Dict[str, Any]) -> str:
    branch_role = str(edge.get("branch_role", "")).strip()
    if branch_role in {"suction", "discharge"}:
        return branch_role
    edge_kind = str(edge.get("edge_kind", "")).strip()
    if "suction" in edge_kind:
        return "suction"
    if "discharge" in edge_kind:
        return "discharge"
    return "other"


def _infer_route_system_class(edge_ids: Any, payload: Dict[str, Any]) -> str:
    classes = set()
    iterable = edge_ids if isinstance(edge_ids, (list, set, tuple)) else payload["installed_edges"]
    for edge_id in iterable:
        edge = payload["edges"][edge_id]
        for component in edge["components"]:
            system_class = str(component.get("sys_diameter_class", "")).strip()
            if system_class and system_class != "none":
                classes.add(system_class)
    if len(classes) == 1:
        return next(iter(classes))
    if not classes:
        return "none"
    return "mixed"


def _default_meter_flags(route: Dict[str, Any]) -> Dict[str, Any]:
    measurement_required = bool(route.get("measurement_required", False))
    return {
        "compatible": not measurement_required,
        "meter_is_bypass": False,
        "bypass_ok": not measurement_required,
        "q_range_ok": not measurement_required,
        "dose_ok": not measurement_required,
        "error_ok": not measurement_required,
        "meter_q_min_lpm": 0.0,
        "meter_q_max_lpm": 0.0,
    }


def _route_result_rank(item: Dict[str, Any]) -> tuple[float, float, float]:
    hydraulics = item["hydraulics"]
    return (
        float(hydraulics["hydraulic_slack_lpm"]),
        -float(hydraulics["total_loss_lpm_equiv"]),
        -float(len(item["active_path_edge_ids"])),
    )


def _sum_total_cost(bom: list[Dict[str, Any]]) -> float:
    return sum(float(item.get("total_cost", 0.0)) for item in bom)


def _sum_category_qty(bom: list[Dict[str, Any]], category: str) -> int:
    return sum(int(item.get("qty", 0)) for item in bom if item.get("category") == category)


def _sum_hose_length(bom: list[Dict[str, Any]]) -> float:
    return sum(
        float(item.get("hose_length_m", 0.0)) * int(item.get("qty", 0))
        for item in bom
        if item.get("category") == "hose"
    )


def _sum_served_routes(routes: list[Dict[str, Any]]) -> int:
    return sum(1 for route in routes if bool(route.get("served", False)))


def _sum_mandatory_served(routes: list[Dict[str, Any]]) -> int:
    return sum(
        1 for route in routes if bool(route.get("mandatory", False)) and bool(route.get("served", False))
    )


def _inventory_summary_for_bom(bom: list[Dict[str, Any]]) -> Dict[str, Any]:
    hose_total_used_m = _sum_hose_length(bom)
    tee_total_used = _sum_category_qty(bom, "connector")
    solenoid_suction_total = sum(
        int(item.get("qty_suction", 0)) for item in bom if item.get("category") == "valve"
    )
    solenoid_discharge_total = sum(
        int(item.get("qty_discharge", 0)) for item in bom if item.get("category") == "valve"
    )
    solenoid_total = _sum_category_qty(bom, "valve")
    base_usage: Dict[str, int] = {}
    extra_usage: Dict[str, int] = {}
    for item in bom:
        target = extra_usage if bool(item.get("is_extra", False)) else base_usage
        target[item["component_id"]] = int(item["qty"])
    return {
        "hose_total_used_m": round(hose_total_used_m, 3),
        "tee_total_used": tee_total_used,
        "solenoid_suction_total": solenoid_suction_total,
        "solenoid_discharge_total": solenoid_discharge_total,
        "solenoid_total": solenoid_total,
        "base_vs_extra_usage": {
            "base": base_usage,
            "extra": extra_usage,
        },
    }


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
