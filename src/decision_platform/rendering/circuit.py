from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from decision_platform.data_io.loader import ScenarioBundle


def build_render_payload(candidate: dict[str, Any], bundle: ScenarioBundle, metrics: dict[str, Any]) -> dict[str, Any]:
    nodes = bundle.nodes.set_index("node_id").to_dict("index")
    elements = []
    for node_id, node in nodes.items():
        elements.append(
            {
                "data": {"id": node_id, "label": node["label"], "node_type": node["node_type"]},
                "position": {"x": float(node["x_m"]) * 900, "y": (1.0 - float(node["y_m"])) * 500},
                "classes": f"node {node['node_type']}",
            }
        )
    for link_id in candidate["installed_link_ids"]:
        link = candidate["installed_links"][link_id]
        elements.append(
            {
                "data": {"id": link_id, "source": link["from_node"], "target": link["to_node"], "label": link["archetype"]},
                "classes": f"edge {link['archetype']}",
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
