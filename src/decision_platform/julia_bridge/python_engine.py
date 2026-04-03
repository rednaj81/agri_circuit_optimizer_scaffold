from __future__ import annotations

import networkx as nx

from decision_platform.data_io.loader import ScenarioBundle


def emulate_watermodels_cli(payload: dict, bundle: ScenarioBundle) -> dict:
    graph = nx.DiGraph()
    installed_links = payload["installed_links"]
    for link in installed_links.values():
        graph.add_edge(link["from_node"], link["to_node"], link_id=link["link_id"])
        if bool(link.get("bidirectional", False)):
            graph.add_edge(link["to_node"], link["from_node"], link_id=link["link_id"])

    route_metrics = []
    mandatory_unserved = []
    all_installed_components = []
    total_install_cost = 0.0
    fallback_component_count = 0

    for link in installed_links.values():
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


def _evaluate_route(graph: nx.DiGraph, payload: dict, route: dict) -> dict:
    try:
        paths = _limited_simple_paths(graph, route["source"], route["sink"], max_paths=12, cutoff=10)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return _route_failure(route, "no_path")
    family_rules = payload["family_rules"]

    for nodes in paths[:12]:
        link_ids = [graph[nodes[i]][nodes[i + 1]]["link_id"] for i in range(len(nodes) - 1)]
        links = [payload["installed_links"][link_id] for link_id in link_ids]
        pumps = _components_on_links(links, "pump")
        meters = _components_on_links(links, "meter")
        used_fallback_pump = False
        used_fallback_meter = False
        fallback_pump = payload.get("fallback_components", {}).get("pump")
        fallback_meter = payload.get("fallback_components", {}).get("meter")
        if not pumps:
            if fallback_pump is None:
                continue
            pumps = [fallback_pump]
            used_fallback_pump = True
        active_pumps = min(len(pumps), int(family_rules["max_active_pumps_per_route"]))
        passive_reverse_pump_count = max(0, len(pumps) - active_pumps)
        if passive_reverse_pump_count and not bool(family_rules["allow_idle_pumps_on_path"]):
            continue
        compatible_meters = [
            meter
            for meter in meters
            if float(route["q_min_delivered_lpm"]) >= float(meter["hard_min_lpm"])
            and float(route["q_min_delivered_lpm"]) <= float(meter["hard_max_lpm"])
        ]
        selected_meter = None
        if bool(route["measurement_required"]):
            if not compatible_meters:
                if fallback_meter is None:
                    continue
                selected_meter = fallback_meter
                used_fallback_meter = True
            else:
                selected_meter = min(
                    compatible_meters,
                    key=lambda meter: (
                        abs(float(meter["confidence_min_lpm"]) - float(route["q_min_delivered_lpm"])),
                        -float(meter["quality_base_score"]),
                    ),
                )
        if len(meters) > (1 if route["measurement_required"] else 0) and not bool(family_rules["allow_idle_meters_on_path"]):
            continue
        path_components = [component for link in links for component in link["installed_components"]]
        active_pump = max(pumps, key=lambda pump: float(pump["hard_max_lpm"]))
        delivered_flow = _estimate_delivered_flow(route, path_components, active_pump, selected_meter)
        if delivered_flow < float(route["q_min_delivered_lpm"]):
            continue
        cleaning_volume = sum(float(component["cleaning_hold_up_l"]) for component in path_components)
        within_confidence = bool(
            selected_meter is not None
            and float(selected_meter["confidence_min_lpm"])
            <= float(route["q_min_delivered_lpm"])
            <= float(selected_meter["confidence_max_lpm"])
        )
        route_quality = sum(float(component["quality_base_score"]) for component in path_components)
        switch_count = sum(1 for component in path_components if component["category"] in {"valve", "pump", "meter"})
        operability_score = max(0.0, 100.0 - switch_count * 6 - max(0, len(pumps) - 1) * 8)
        flow_score = min(100.0, delivered_flow / max(float(route["q_min_delivered_lpm"]), 1.0) * 100.0)
        return {
            "route_id": route["route_id"],
            "source": route["source"],
            "sink": route["sink"],
            "mandatory": bool(route["mandatory"]),
            "route_group": route["route_group"],
            "feasible": True,
            "reason": "ok",
            "path_nodes": nodes,
            "path_link_ids": link_ids,
            "active_pump_count": active_pumps,
            "passive_reverse_pump_count": passive_reverse_pump_count,
            "series_pump_count": len(pumps),
            "selected_meter_id": selected_meter["component_id"] if selected_meter else None,
            "flow_within_meter_confidence": within_confidence,
            "cleaning_volume_l": round(cleaning_volume, 3),
            "component_switch_count": switch_count,
            "fallback_component_count": sum(int(component["is_fallback"]) for component in path_components)
            + int(used_fallback_pump)
            + int(used_fallback_meter),
            "used_fallback_pump": used_fallback_pump,
            "used_fallback_meter": used_fallback_meter,
            "delivered_flow_lpm": round(delivered_flow, 3),
            "required_flow_lpm": float(route["q_min_delivered_lpm"]),
            "quality_score_base": round(route_quality, 3),
            "quality_score": round(route_quality, 3),
            "operability_score": round(operability_score, 3),
            "flow_score": round(flow_score, 3),
            "component_ids_on_path": [component["component_id"] for component in path_components],
        }
    return _route_failure(route, "hydraulic_or_meter_infeasible")


def _estimate_delivered_flow(route: dict, path_components: list[dict], active_pump: dict, selected_meter: dict | None) -> float:
    required_flow = float(route["q_min_delivered_lpm"])
    meter_hard_max = float(selected_meter["hard_max_lpm"]) if selected_meter else 99999.0
    hard_caps = [float(component["hard_max_lpm"]) for component in path_components if float(component["hard_max_lpm"]) > 0]
    capacity = min(hard_caps + [float(active_pump["hard_max_lpm"]), meter_hard_max])
    cumulative_loss_pct = sum(float(component["forward_loss_pct_when_on"]) for component in path_components)
    delivered_flow = capacity * max(0.05, 1.0 - cumulative_loss_pct / 100.0)
    return max(required_flow if delivered_flow >= required_flow else delivered_flow, 0.0)


def _components_on_links(links: list[dict], category: str) -> list[dict]:
    return [component for link in links for component in link["installed_components"] if component["category"] == category]


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


def _route_failure(route: dict, reason: str) -> dict:
    return {
        "route_id": route["route_id"],
        "source": route["source"],
        "sink": route["sink"],
        "mandatory": bool(route["mandatory"]),
        "route_group": route["route_group"],
        "feasible": False,
        "reason": reason,
        "path_nodes": [],
        "path_link_ids": [],
        "active_pump_count": 0,
        "passive_reverse_pump_count": 0,
        "series_pump_count": 0,
        "selected_meter_id": None,
        "flow_within_meter_confidence": False,
        "cleaning_volume_l": 0.0,
        "component_switch_count": 0,
        "fallback_component_count": 0,
        "used_fallback_pump": False,
        "used_fallback_meter": False,
        "delivered_flow_lpm": 0.0,
        "required_flow_lpm": float(route["q_min_delivered_lpm"]),
        "quality_score_base": 0.0,
        "quality_score": 0.0,
        "operability_score": 0.0,
        "flow_score": 0.0,
        "component_ids_on_path": [],
    }


def _limited_simple_paths(graph: nx.DiGraph, source: str, sink: str, *, max_paths: int, cutoff: int) -> list[list[str]]:
    paths = []
    for path in nx.all_simple_paths(graph, source=source, target=sink, cutoff=cutoff):
        paths.append(path)
        if len(paths) >= max_paths:
            break
    return paths
