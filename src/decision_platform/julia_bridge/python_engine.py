from __future__ import annotations

from typing import Any

import networkx as nx

from decision_platform.data_io.loader import ScenarioBundle


def emulate_watermodels_cli(payload: dict, bundle: ScenarioBundle) -> dict:
    graph = _build_graph(payload)
    route_metrics = []
    mandatory_unserved = []
    all_installed_components = []
    total_install_cost = 0.0
    fallback_component_count = 0

    for link in payload["installed_links"].values():
        for component in link["installed_components"]:
            all_installed_components.append(component)
            total_install_cost += float(component["cost"])
            fallback_component_count += int(bool(component["is_fallback"]))

    for route in bundle.route_requirements.to_dict("records"):
        metric = _evaluate_route(graph, payload, route)
        route_metrics.append(metric)
        if bool(route["mandatory"]) and not bool(metric["feasible"]):
            mandatory_unserved.append(route["route_id"])

    alternate_path_count_critical = 0
    for route in bundle.route_requirements.to_dict("records"):
        if not bool(route["mandatory"]):
            continue
        try:
            count = len(_limited_simple_paths(graph, route["source"], route["sink"], max_paths=3, cutoff=10))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            count = 0
        alternate_path_count_critical += max(0, count - 1)

    feasible = not mandatory_unserved
    served_routes = [metric for metric in route_metrics if metric["feasible"]]
    route_count = max(len(route_metrics), 1)
    cleaning_avg = (
        sum(metric["cleaning_volume_l"] for metric in served_routes) / len(served_routes)
        if served_routes
        else 0.0
    )
    quality_score = sum(metric["quality_score_base"] for metric in route_metrics) / route_count
    flow_out_score = sum(metric["flow_score"] for metric in route_metrics) / route_count
    resilience_score = min(100.0, float(alternate_path_count_critical * 10 + len(served_routes) * 3))
    cleaning_score = max(0.0, 100.0 - cleaning_avg * 10)
    operability_score = sum(metric["operability_score"] for metric in route_metrics) / route_count
    return {
        "engine": "python_emulated_julia",
        "feasible": feasible,
        "mandatory_unserved": mandatory_unserved,
        "install_cost": round(total_install_cost, 3),
        "fallback_cost": round(
            sum(float(component["cost"]) for component in all_installed_components if component["is_fallback"]),
            3,
        ),
        "quality_score_raw": round(quality_score, 3),
        "flow_out_score": round(flow_out_score, 3),
        "resilience_score": round(resilience_score, 3),
        "cleaning_score": round(cleaning_score, 3),
        "operability_score": round(operability_score, 3),
        "maintenance_score": round(max(0.0, 100.0 - len(all_installed_components) * 1.5), 3),
        "alternate_path_count_critical": alternate_path_count_critical,
        "fallback_component_count": fallback_component_count,
        "bom_summary": _build_bom_summary(all_installed_components),
        "route_metrics": route_metrics,
    }


def _build_graph(payload: dict) -> nx.DiGraph:
    graph = nx.DiGraph()
    installed_links = payload["installed_links"]
    for link in installed_links.values():
        graph.add_edge(link["from_node"], link["to_node"], link_id=link["link_id"])
        if bool(link.get("bidirectional", False)):
            graph.add_edge(link["to_node"], link["from_node"], link_id=link["link_id"])
    return graph


def _evaluate_route(graph: nx.DiGraph, payload: dict, route: dict) -> dict:
    try:
        paths = _limited_simple_paths(graph, route["source"], route["sink"], max_paths=12, cutoff=10)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return _route_failure(route, "no_path")

    family_rules = payload["family_rules"]
    successful_paths = []
    failed_paths = []
    for nodes in paths[:12]:
        link_ids = [graph[nodes[i]][nodes[i + 1]]["link_id"] for i in range(len(nodes) - 1)]
        links = [payload["installed_links"][link_id] for link_id in link_ids]
        evaluated = _evaluate_path(route, payload, family_rules, nodes, link_ids, links)
        if evaluated["feasible"]:
            successful_paths.append(evaluated)
        else:
            failed_paths.append(evaluated)

    if successful_paths:
        return max(successful_paths, key=_route_success_rank)
    if failed_paths:
        return max(failed_paths, key=_route_failure_rank)
    return _route_failure(route, "hydraulic_or_meter_infeasible")


def _evaluate_path(
    route: dict,
    payload: dict,
    family_rules: dict,
    nodes: list[str],
    link_ids: list[str],
    links: list[dict],
) -> dict:
    component_entries = _component_entries_for_links(links)
    pump_entries = [entry for entry in component_entries if entry["component"]["category"] == "pump"]
    meter_entries = [entry for entry in component_entries if entry["component"]["category"] == "meter"]
    fallback_entries = []
    used_fallback_pump = False
    used_fallback_meter = False
    fallback_pump = payload.get("fallback_components", {}).get("pump")
    fallback_meter = payload.get("fallback_components", {}).get("meter")
    required_flow = float(route["q_min_delivered_lpm"])

    if not pump_entries:
        if fallback_pump is None:
            return _route_failure(
                route,
                "no_pump_available",
                nodes=nodes,
                link_ids=link_ids,
                component_entries=component_entries,
            )
        fallback_entries.append(_make_fallback_entry(fallback_pump, "__fallback_pump__"))
        pump_entries = [fallback_entries[-1]]
        used_fallback_pump = True

    active_pump_limit = max(1, int(family_rules["max_active_pumps_per_route"]))
    active_pump_count = min(len(pump_entries), active_pump_limit)
    passive_reverse_pump_count = max(0, len(pump_entries) - active_pump_count)
    if passive_reverse_pump_count and not bool(family_rules["allow_idle_pumps_on_path"]):
        return _route_failure(
            route,
            "idle_pumps_not_allowed",
            nodes=nodes,
            link_ids=link_ids,
            component_entries=component_entries + fallback_entries,
            active_pump_count=active_pump_count,
            passive_reverse_pump_count=passive_reverse_pump_count,
            series_pump_count=len(pump_entries),
            used_fallback_pump=used_fallback_pump,
            fallback_component_count=_fallback_count(component_entries + fallback_entries),
        )

    selected_meter_entry = None
    compatible_meters = [
        entry
        for entry in meter_entries
        if float(entry["component"]["hard_min_lpm"]) <= required_flow <= float(entry["component"]["hard_max_lpm"])
    ]
    if bool(route["measurement_required"]):
        if compatible_meters:
            selected_meter_entry = min(
                compatible_meters,
                key=lambda entry: (
                    abs(float(entry["component"]["confidence_min_lpm"]) - required_flow),
                    -float(entry["component"]["quality_base_score"]),
                ),
            )
        elif fallback_meter is not None:
            selected_meter_entry = _make_fallback_entry(fallback_meter, "__fallback_meter__")
            fallback_entries.append(selected_meter_entry)
            used_fallback_meter = True
        else:
            return _route_failure(
                route,
                "measurement_required_without_compatible_meter",
                nodes=nodes,
                link_ids=link_ids,
                component_entries=component_entries,
                active_pump_count=active_pump_count,
                passive_reverse_pump_count=passive_reverse_pump_count,
                series_pump_count=len(pump_entries),
                used_fallback_pump=used_fallback_pump,
                fallback_component_count=_fallback_count(component_entries + fallback_entries),
            )

    max_reading_meters = max(0, int(family_rules.get("max_reading_meters_per_route", 1)))
    if len(meter_entries) > max_reading_meters and not bool(family_rules["allow_idle_meters_on_path"]):
        return _route_failure(
            route,
            "idle_meters_not_allowed",
            nodes=nodes,
            link_ids=link_ids,
            component_entries=component_entries + fallback_entries,
            active_pump_count=active_pump_count,
            passive_reverse_pump_count=passive_reverse_pump_count,
            series_pump_count=len(pump_entries),
            selected_meter_id=selected_meter_entry["component"]["component_id"] if selected_meter_entry else None,
            used_fallback_pump=used_fallback_pump,
            used_fallback_meter=used_fallback_meter,
            fallback_component_count=_fallback_count(component_entries + fallback_entries),
        )

    path_entries = component_entries + fallback_entries
    hydraulics = _evaluate_hydraulics(route, path_entries, selected_meter_entry)
    if hydraulics["route_effective_q_max_lpm"] < required_flow:
        return _route_failure(
            route,
            "insufficient_effective_capacity",
            nodes=nodes,
            link_ids=link_ids,
            component_entries=path_entries,
            active_pump_count=active_pump_count,
            passive_reverse_pump_count=passive_reverse_pump_count,
            series_pump_count=len(pump_entries),
            selected_meter_id=selected_meter_entry["component"]["component_id"] if selected_meter_entry else None,
            used_fallback_pump=used_fallback_pump,
            used_fallback_meter=used_fallback_meter,
            fallback_component_count=_fallback_count(path_entries),
            hydraulics=hydraulics,
        )

    route_quality = sum(float(entry["component"]["quality_base_score"]) for entry in path_entries)
    switch_count = sum(1 for entry in path_entries if entry["component"]["category"] in {"valve", "pump", "meter"})
    operability_score = max(
        0.0,
        100.0
        - switch_count * 6
        - passive_reverse_pump_count * 8
        - hydraulics["total_loss_pct"] * 0.6,
    )
    flow_score = min(100.0, hydraulics["delivered_flow_lpm"] / max(required_flow, 1.0) * 100.0)
    return {
        "route_id": route["route_id"],
        "source": route["source"],
        "sink": route["sink"],
        "mandatory": bool(route["mandatory"]),
        "route_group": route["route_group"],
        "feasible": True,
        "reason": "ok",
        "failure_reason": None,
        "path_nodes": nodes,
        "path_link_ids": link_ids,
        "active_path_nodes": nodes,
        "active_path_edge_ids": link_ids,
        "active_path_arc_ids": link_ids,
        "active_pump_count": active_pump_count,
        "passive_reverse_pump_count": passive_reverse_pump_count,
        "series_pump_count": len(pump_entries),
        "selected_meter_id": selected_meter_entry["component"]["component_id"] if selected_meter_entry else None,
        "flow_within_meter_confidence": _flow_within_meter_confidence(selected_meter_entry, required_flow),
        "cleaning_volume_l": round(sum(float(entry["component"]["cleaning_hold_up_l"]) for entry in path_entries), 3),
        "component_switch_count": switch_count,
        "fallback_component_count": _fallback_count(path_entries),
        "used_fallback_pump": used_fallback_pump,
        "used_fallback_meter": used_fallback_meter,
        "delivered_flow_lpm": round(hydraulics["delivered_flow_lpm"], 3),
        "required_flow_lpm": required_flow,
        "quality_score_base": round(route_quality, 3),
        "quality_score": round(route_quality, 3),
        "operability_score": round(operability_score, 3),
        "flow_score": round(flow_score, 3),
        "component_ids_on_path": [entry["component"]["component_id"] for entry in path_entries],
        "total_loss_pct": round(hydraulics["total_loss_pct"], 3),
        "total_loss_lpm_equiv": round(hydraulics["total_loss_lpm_equiv"], 3),
        "route_effective_q_max_lpm": round(hydraulics["route_effective_q_max_lpm"], 3),
        "hydraulic_slack_lpm": round(hydraulics["hydraulic_slack_lpm"], 3),
        "gargalo_principal": hydraulics["gargalo_principal"],
        "bottleneck_component_id": hydraulics["bottleneck_component_id"],
        "bottleneck_component_category": hydraulics["bottleneck_component_category"],
        "critical_component_id": hydraulics["bottleneck_component_id"],
        "critical_consequence": hydraulics["critical_consequence"],
        "hydraulic_trace": hydraulics["hydraulic_trace"],
    }


def _evaluate_hydraulics(
    route: dict,
    component_entries: list[dict[str, Any]],
    selected_meter_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    required_flow = float(route["q_min_delivered_lpm"])
    total_loss_pct = 0.0
    capacity_terms = []
    hydraulic_trace = []

    for entry in component_entries:
        component = entry["component"]
        loss_pct = float(component["forward_loss_pct_when_on"])
        hard_max = float(component["hard_max_lpm"])
        effective_capacity = max(0.0, hard_max * max(0.05, 1.0 - loss_pct / 100.0))
        total_loss_pct += loss_pct
        hydraulic_trace.append(
            {
                "link_id": entry["link_id"],
                "component_id": component["component_id"],
                "category": component["category"],
                "loss_pct": round(loss_pct, 3),
                "hard_max_lpm": round(hard_max, 3),
                "effective_capacity_lpm": round(effective_capacity, 3),
                "is_fallback": bool(component["is_fallback"]),
                "consequence": "path_hydraulic_limit",
            }
        )
        if hard_max > 0:
            capacity_terms.append((effective_capacity, component, entry["link_id"]))

    if not capacity_terms:
        return {
            "total_loss_pct": total_loss_pct,
            "total_loss_lpm_equiv": required_flow,
            "route_effective_q_max_lpm": 0.0,
            "hydraulic_slack_lpm": -required_flow,
            "delivered_flow_lpm": 0.0,
            "gargalo_principal": "no_capacity_terms",
            "bottleneck_component_id": None,
            "bottleneck_component_category": None,
            "critical_consequence": "no_capacity_terms",
            "hydraulic_trace": hydraulic_trace,
        }

    bottleneck_capacity, bottleneck_component, bottleneck_link_id = min(capacity_terms, key=lambda item: item[0])
    total_loss_lpm_equiv = required_flow * total_loss_pct / 100.0
    route_effective_q_max_lpm = max(0.0, bottleneck_capacity)
    delivered_flow_lpm = route_effective_q_max_lpm
    hydraulic_slack_lpm = delivered_flow_lpm - required_flow

    for item in hydraulic_trace:
        if item["component_id"] == bottleneck_component["component_id"] and item["link_id"] == bottleneck_link_id:
            item["is_bottleneck"] = True
            item["consequence"] = "limits_effective_capacity"
        else:
            item["is_bottleneck"] = False

    if selected_meter_entry is not None and not _flow_within_meter_confidence(selected_meter_entry, required_flow):
        critical_consequence = "meter_outside_confidence_band"
    elif hydraulic_slack_lpm < 0:
        critical_consequence = "route_below_required_flow"
    else:
        critical_consequence = "limits_effective_capacity"

    return {
        "total_loss_pct": total_loss_pct,
        "total_loss_lpm_equiv": total_loss_lpm_equiv,
        "route_effective_q_max_lpm": route_effective_q_max_lpm,
        "hydraulic_slack_lpm": hydraulic_slack_lpm,
        "delivered_flow_lpm": delivered_flow_lpm,
        "gargalo_principal": f"{bottleneck_component['category']}:{bottleneck_component['component_id']}",
        "bottleneck_component_id": bottleneck_component["component_id"],
        "bottleneck_component_category": bottleneck_component["category"],
        "critical_consequence": critical_consequence,
        "hydraulic_trace": hydraulic_trace,
    }


def _route_success_rank(metric: dict[str, Any]) -> tuple[float, ...]:
    return (
        float(metric["hydraulic_slack_lpm"]),
        -float(metric["fallback_component_count"]),
        -float(metric["total_loss_lpm_equiv"]),
        float(metric["quality_score"]),
    )


def _route_failure_rank(metric: dict[str, Any]) -> tuple[float, ...]:
    failure_priority = {
        "insufficient_effective_capacity": 5.0,
        "measurement_required_without_compatible_meter": 4.0,
        "idle_pumps_not_allowed": 3.0,
        "idle_meters_not_allowed": 2.0,
        "no_pump_available": 1.0,
        "no_path": 0.0,
        "hydraulic_or_meter_infeasible": -1.0,
    }
    return (
        failure_priority.get(metric["reason"], -5.0),
        float(metric.get("delivered_flow_lpm", 0.0)),
        -float(metric.get("fallback_component_count", 0)),
    )


def _component_entries_for_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"link_id": link["link_id"], "component": component}
        for link in links
        for component in link["installed_components"]
    ]


def _make_fallback_entry(component: dict[str, Any], link_id: str) -> dict[str, Any]:
    return {"link_id": link_id, "component": component}


def _fallback_count(component_entries: list[dict[str, Any]]) -> int:
    return sum(int(bool(entry["component"]["is_fallback"])) for entry in component_entries)


def _flow_within_meter_confidence(selected_meter_entry: dict[str, Any] | None, required_flow: float) -> bool:
    if selected_meter_entry is None:
        return False
    component = selected_meter_entry["component"]
    return float(component["confidence_min_lpm"]) <= required_flow <= float(component["confidence_max_lpm"])


def _build_bom_summary(components: list[dict]) -> dict:
    summary: dict[str, dict] = {}
    for component in components:
        entry = summary.setdefault(
            component["component_id"],
            {"component_id": component["component_id"], "category": component["category"], "qty": 0, "total_cost": 0.0},
        )
        entry["qty"] += 1
        entry["total_cost"] = round(entry["total_cost"] + float(component["cost"]), 3)
    return {"components": sorted(summary.values(), key=lambda item: item["component_id"]), "total_components": len(components)}


def _route_failure(
    route: dict,
    reason: str,
    *,
    nodes: list[str] | None = None,
    link_ids: list[str] | None = None,
    component_entries: list[dict[str, Any]] | None = None,
    active_pump_count: int = 0,
    passive_reverse_pump_count: int = 0,
    series_pump_count: int = 0,
    selected_meter_id: str | None = None,
    used_fallback_pump: bool = False,
    used_fallback_meter: bool = False,
    fallback_component_count: int = 0,
    hydraulics: dict[str, Any] | None = None,
) -> dict:
    component_entries = component_entries or []
    hydraulics = hydraulics or {
        "total_loss_pct": 0.0,
        "total_loss_lpm_equiv": 0.0,
        "route_effective_q_max_lpm": 0.0,
        "hydraulic_slack_lpm": -float(route["q_min_delivered_lpm"]),
        "delivered_flow_lpm": 0.0,
        "gargalo_principal": None,
        "bottleneck_component_id": None,
        "bottleneck_component_category": None,
        "critical_consequence": reason,
        "hydraulic_trace": [],
    }
    return {
        "route_id": route["route_id"],
        "source": route["source"],
        "sink": route["sink"],
        "mandatory": bool(route["mandatory"]),
        "route_group": route["route_group"],
        "feasible": False,
        "reason": reason,
        "failure_reason": reason,
        "path_nodes": nodes or [],
        "path_link_ids": link_ids or [],
        "active_path_nodes": nodes or [],
        "active_path_edge_ids": link_ids or [],
        "active_path_arc_ids": link_ids or [],
        "active_pump_count": active_pump_count,
        "passive_reverse_pump_count": passive_reverse_pump_count,
        "series_pump_count": series_pump_count,
        "selected_meter_id": selected_meter_id,
        "flow_within_meter_confidence": False,
        "cleaning_volume_l": round(sum(float(entry["component"]["cleaning_hold_up_l"]) for entry in component_entries), 3),
        "component_switch_count": sum(1 for entry in component_entries if entry["component"]["category"] in {"valve", "pump", "meter"}),
        "fallback_component_count": fallback_component_count,
        "used_fallback_pump": used_fallback_pump,
        "used_fallback_meter": used_fallback_meter,
        "delivered_flow_lpm": round(float(hydraulics["delivered_flow_lpm"]), 3),
        "required_flow_lpm": float(route["q_min_delivered_lpm"]),
        "quality_score_base": round(sum(float(entry["component"]["quality_base_score"]) for entry in component_entries), 3),
        "quality_score": round(sum(float(entry["component"]["quality_base_score"]) for entry in component_entries), 3),
        "operability_score": 0.0,
        "flow_score": 0.0,
        "component_ids_on_path": [entry["component"]["component_id"] for entry in component_entries],
        "total_loss_pct": round(float(hydraulics["total_loss_pct"]), 3),
        "total_loss_lpm_equiv": round(float(hydraulics["total_loss_lpm_equiv"]), 3),
        "route_effective_q_max_lpm": round(float(hydraulics["route_effective_q_max_lpm"]), 3),
        "hydraulic_slack_lpm": round(float(hydraulics["hydraulic_slack_lpm"]), 3),
        "gargalo_principal": hydraulics["gargalo_principal"],
        "bottleneck_component_id": hydraulics["bottleneck_component_id"],
        "bottleneck_component_category": hydraulics["bottleneck_component_category"],
        "critical_component_id": hydraulics["bottleneck_component_id"],
        "critical_consequence": hydraulics["critical_consequence"],
        "hydraulic_trace": hydraulics["hydraulic_trace"],
    }


def _limited_simple_paths(graph: nx.DiGraph, source: str, sink: str, *, max_paths: int, cutoff: int) -> list[list[str]]:
    paths = []
    for path in nx.all_simple_paths(graph, source=source, target=sink, cutoff=cutoff):
        paths.append(path)
        if len(paths) >= max_paths:
            break
    return paths
