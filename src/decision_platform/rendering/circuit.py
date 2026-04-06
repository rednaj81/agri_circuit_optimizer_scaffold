from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from decision_platform.data_io.loader import ScenarioBundle


NODE_TYPE_LABELS = {
    "water_tank": "Tanque de agua",
    "product_tank": "Tanque de produto",
    "mixer_tank": "Misturador",
    "incorporator_tank": "Incorporador",
    "external_outlet": "Saida externa",
    "service_return": "Retorno de servico",
    "junction": "Juncao operacional",
}

EDGE_ARCHETYPE_LABELS = {
    "tank_tap": "Tomada de tanque",
    "service_tap": "Tomada de servico",
    "supply_tap": "Entrada de agua",
    "outlet_tap": "Saida do circuito",
    "bus_segment": "Trecho do barramento",
    "pump_island_segment": "Trecho com ilha de bomba",
    "upper_bypass_segment": "Trecho do bypass superior",
    "vertical_link": "Conexao vertical",
    "star_tap": "Ligacao estrela",
    "star_trunk": "Tronco estrela",
    "loop_upper_chord": "Corda superior",
}


def _is_internal_business_node(node: dict[str, Any]) -> bool:
    zone = str(node.get("zone", "")).strip().lower()
    if zone in {"internal", "hub"}:
        return True
    if bool(node.get("is_candidate_hub")):
        return True
    labels = " ".join(str(node.get(field, "")).strip().lower() for field in ("node_id", "label", "notes"))
    return "hub" in labels and str(node.get("node_type", "")).strip() == "junction"


def _node_label(node: dict[str, Any]) -> str:
    label = str(node.get("label", "")).strip()
    node_id = str(node.get("node_id", "")).strip()
    return label or node_id or "Entidade sem rotulo"


def _edge_label(archetype: Any) -> str:
    normalized = str(archetype or "").strip()
    return EDGE_ARCHETYPE_LABELS.get(normalized, normalized or "Conexao do circuito")


def _route_projection_rows(
    bundle: ScenarioBundle,
    metrics: dict[str, Any],
    visible_node_ids: set[str],
) -> list[dict[str, Any]]:
    route_lookup = {
        str(row.get("route_id", "")).strip(): row
        for row in bundle.route_requirements.to_dict("records")
        if str(row.get("route_id", "")).strip()
    }
    projected_rows: list[dict[str, Any]] = []
    for route in metrics.get("route_metrics", []):
        if not bool(route.get("feasible")):
            continue
        route_id = str(route.get("route_id", "")).strip()
        route_row = route_lookup.get(route_id, {})
        source = str(route_row.get("source", "")).strip()
        target = str(route_row.get("sink", "")).strip()
        if not route_id or source not in visible_node_ids or target not in visible_node_ids or source == target:
            continue
        projected_rows.append(
            {
                "projection_id": f"route:{route_id}",
                "route_id": route_id,
                "source": source,
                "target": target,
                "label": str(route_row.get("notes", "")).strip() or f"{source} -> {target}",
                "mandatory": bool(route_row.get("mandatory")),
                "measurement_required": bool(route_row.get("measurement_required")),
            }
        )
    return projected_rows


def build_render_payload(candidate: dict[str, Any], bundle: ScenarioBundle, metrics: dict[str, Any]) -> dict[str, Any]:
    nodes = {
        node_id: {"node_id": node_id, **node}
        for node_id, node in bundle.nodes.set_index("node_id").to_dict("index").items()
    }
    installed_node_ids: set[str] = set()
    direct_business_edges: list[dict[str, Any]] = []
    for link_id in candidate["installed_link_ids"]:
        link = candidate["installed_links"][link_id]
        source = str(link["from_node"])
        target = str(link["to_node"])
        installed_node_ids.add(source)
        installed_node_ids.add(target)
    visible_node_ids = {
        node_id
        for node_id in installed_node_ids
        if node_id in nodes and not _is_internal_business_node(nodes[node_id])
    }
    route_projections = _route_projection_rows(bundle, metrics, visible_node_ids)
    for route in route_projections:
        visible_node_ids.add(str(route["source"]))
        visible_node_ids.add(str(route["target"]))
    elements = []
    for node_id in sorted(visible_node_ids):
        node = nodes[node_id]
        elements.append(
            {
                "data": {
                    "id": node_id,
                    "label": _node_label(node),
                    "node_type": node["node_type"],
                    "business_role": NODE_TYPE_LABELS.get(str(node["node_type"]).strip(), "Entidade do circuito"),
                },
                "position": {"x": float(node["x_m"]) * 900, "y": (1.0 - float(node["y_m"])) * 500},
                "classes": f"node {node['node_type']}",
            }
        )
    for link_id in candidate["installed_link_ids"]:
        link = candidate["installed_links"][link_id]
        source = str(link["from_node"])
        target = str(link["to_node"])
        if source in visible_node_ids and target in visible_node_ids:
            direct_business_edges.append(
                {
                    "data": {
                        "id": link_id,
                        "source": source,
                        "target": target,
                        "label": _edge_label(link["archetype"]),
                    },
                    "classes": f"edge {link['archetype']}",
                }
            )
    if direct_business_edges:
        elements.extend(direct_business_edges)
    else:
        for route in route_projections:
            elements.append(
                {
                    "data": {
                        "id": str(route["projection_id"]),
                        "route_id": str(route["route_id"]),
                        "source": str(route["source"]),
                        "target": str(route["target"]),
                        "label": str(route["label"]),
                    },
                    "classes": " ".join(
                        item
                        for item in [
                            "edge",
                            "route-projection",
                            "mandatory" if bool(route["mandatory"]) else "optional",
                            "measurement-required" if bool(route["measurement_required"]) else "",
                        ]
                        if item
                    ),
                }
            )
    return {
        "cytoscape_elements": elements,
        "route_highlights": {
            route["route_id"]: route["path_link_ids"]
            for route in metrics["route_metrics"]
            if route["feasible"]
        },
    }


def build_solution_comparison_figure(candidates: list[dict[str, Any]]) -> go.Figure:
    labels = ["quality", "flow", "resilience", "cleaning", "operability", "maintenance"]
    figure = go.Figure()
    for item in candidates:
        metrics = item["metrics"]
        figure.add_trace(
            go.Scatterpolar(
                r=[
                    metrics["quality_score_raw"],
                    metrics["flow_out_score"],
                    metrics["resilience_score"],
                    metrics["cleaning_score"],
                    metrics["operability_score"],
                    metrics["maintenance_score"],
                ],
                theta=labels,
                fill="toself",
                name=item["candidate_id"],
            )
        )
    figure.update_layout(polar={"radialaxis": {"visible": True}}, showlegend=True)
    return figure
