from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from decision_platform.catalog.quality_rules import apply_quality_rules
from decision_platform.catalog.viability import (
    serialize_constraint_failures,
    summarize_constraint_failures,
    viable_cost_distribution,
)
from decision_platform.data_io.loader import ScenarioBundle
from decision_platform.graph_generation.generator import generate_candidate_topology_bundle
from decision_platform.graph_repair.repair import normalize_candidate
from decision_platform.julia_bridge.bridge import evaluate_candidates_via_bridge
from decision_platform.ranking.scoring import apply_weight_profile
from decision_platform.rendering.circuit import build_render_payload
from decision_platform.scenario_engine.installer import build_candidate_payload


def build_solution_catalog(bundle: ScenarioBundle) -> dict[str, Any]:
    generation_bundle = generate_candidate_topology_bundle(bundle)
    generation_report = generation_bundle["report"]
    candidates = [normalize_candidate(candidate, bundle) for candidate in generation_bundle["candidates"]]
    payloads = [build_candidate_payload(candidate, bundle) for candidate in candidates]
    metrics_list = [
        _enrich_viability_metrics(apply_quality_rules(metrics, bundle))
        for metrics in evaluate_candidates_via_bridge(payloads, bundle)
    ]
    evaluated = []
    for candidate, payload, metrics in zip(candidates, payloads, metrics_list):
        render = build_render_payload(candidate, bundle, metrics)
        evaluated.append(
            {
                "candidate_id": candidate["candidate_id"],
                "topology_family": candidate["topology_family"],
                "generation_source": candidate["generation_source"],
                "generation_metadata": candidate.get("metadata", {}),
                "installed_link_ids": candidate["installed_link_ids"],
                "payload": payload,
                "metrics": metrics,
                "render": render,
            }
        )
    catalog_frame = pd.DataFrame(
        [
            {
                "candidate_id": item["candidate_id"],
                "topology_family": item["topology_family"],
                "generation_source": item["generation_source"],
                "lineage_label": str(item["generation_metadata"].get("lineage_label", item["generation_source"])),
                "origin_family": str(item["generation_metadata"].get("origin_family", item["topology_family"])),
                "generation_index": int(item["generation_metadata"].get("generation", 0)),
                "was_repaired": bool(item["generation_metadata"].get("repaired", False)),
                "feasible": bool(item["metrics"]["feasible"]),
                "install_cost": float(item["metrics"]["install_cost"]),
                "fallback_cost": float(item["metrics"]["fallback_cost"]),
                "quality_score_raw": float(item["metrics"]["quality_score_raw"]),
                "flow_out_score": float(item["metrics"]["flow_out_score"]),
                "resilience_score": float(item["metrics"]["resilience_score"]),
                "cleaning_score": float(item["metrics"]["cleaning_score"]),
                "operability_score": float(item["metrics"]["operability_score"]),
                "maintenance_score": float(item["metrics"]["maintenance_score"]),
                "fallback_component_count": int(item["metrics"]["fallback_component_count"]),
                "engine_used": item["metrics"]["engine_used"],
                "engine_mode": item["metrics"]["engine_mode"],
                "infeasibility_reason": item["metrics"].get("infeasibility_reason"),
                "constraint_failure_count": int(item["metrics"].get("constraint_failure_count", 0)),
                "constraint_failure_categories": json.dumps(
                    item["metrics"].get("constraint_failure_categories", {}),
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "constraint_failures": serialize_constraint_failures(
                    item["metrics"].get("constraint_failures", [])
                ),
            }
            for item in evaluated
        ]
    )
    ranked_profiles = {
        profile_id: apply_weight_profile(catalog_frame, bundle.weight_profiles, profile_id)
        for profile_id in bundle.weight_profiles["profile_id"].tolist()
    }
    default_profile_id = _get_default_profile_id(bundle)
    selected_candidate_id, selected_candidate = _resolve_selected_candidate(
        evaluated,
        ranked_profiles.get(default_profile_id, []),
    )
    summary = _build_catalog_summary(candidates, evaluated, generation_report)
    return {
        "scenario_id": bundle.scenario_settings.get("scenario_id", bundle.base_dir.name),
        "catalog": evaluated,
        "catalog_frame": catalog_frame,
        "ranked_profiles": ranked_profiles,
        "default_profile_id": default_profile_id,
        "selected_candidate_id": selected_candidate_id,
        "selected_candidate": selected_candidate,
        "summary": summary,
        "generation_report": generation_report,
    }


def export_catalog(result: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[str, Path] = {}
    catalog_frame = result["catalog_frame"].copy()
    selected_profile_id = result.get("default_profile_id")
    selected_candidate = result.get("selected_candidate")

    catalog_csv = out_dir / "catalog.csv"
    catalog_frame.to_csv(catalog_csv, index=False)
    exported["catalog_csv"] = catalog_csv

    try:
        catalog_parquet = out_dir / "catalog.parquet"
        catalog_frame.to_parquet(catalog_parquet, index=False)
        exported["catalog_parquet"] = catalog_parquet
    except Exception:
        pass

    ranked_profiles_json = out_dir / "ranked_profiles.json"
    ranked_profiles_json.write_text(json.dumps(result["ranked_profiles"], indent=2, ensure_ascii=False), encoding="utf-8")
    exported["ranked_profiles"] = ranked_profiles_json

    ranking_json = out_dir / "ranking_profiles.json"
    ranking_json.write_text(json.dumps(result["ranked_profiles"], indent=2, ensure_ascii=False), encoding="utf-8")
    exported["ranking_profiles_legacy"] = ranking_json

    detailed_json = out_dir / "catalog_detailed.json"
    detailed_json.write_text(json.dumps(_json_ready_catalog(result["catalog"]), indent=2, ensure_ascii=False), encoding="utf-8")
    exported["catalog_detailed"] = detailed_json

    catalog_json = out_dir / "catalog.json"
    catalog_json.write_text(json.dumps(_json_ready_catalog(result["catalog"]), indent=2, ensure_ascii=False), encoding="utf-8")
    exported["catalog_json"] = catalog_json

    summary_json = out_dir / "catalog_summary.json"
    summary_json.write_text(json.dumps(result.get("summary", {}), indent=2, ensure_ascii=False), encoding="utf-8")
    exported["catalog_summary"] = summary_json

    engine_comparison = result.get("engine_comparison")
    if engine_comparison is not None:
        engine_comparison_json = out_dir / "engine_comparison.json"
        engine_comparison_json.write_text(json.dumps(engine_comparison, indent=2, ensure_ascii=False), encoding="utf-8")
        exported["engine_comparison_json"] = engine_comparison_json

    decision_summary = _build_decision_summary(result, selected_profile_id, selected_candidate)
    final_summary_json = out_dir / "summary.json"
    final_summary_json.write_text(json.dumps(decision_summary, indent=2, ensure_ascii=False), encoding="utf-8")
    exported["summary_json"] = final_summary_json

    for item in result["catalog"]:
        candidate_dir = out_dir / item["candidate_id"]
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "solution.json").write_text(
            json.dumps(_json_ready_catalog([item])[0], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        pd.DataFrame(item["metrics"]["bom_summary"]["components"]).to_csv(candidate_dir / "bom.csv", index=False)

    if selected_candidate is not None:
        selected_candidate_json = out_dir / "selected_candidate.json"
        selected_candidate_json.write_text(
            json.dumps(_json_ready_catalog([selected_candidate])[0], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        exported["selected_candidate_json"] = selected_candidate_json

        selected_candidate_routes_json = out_dir / "selected_candidate_routes.json"
        selected_candidate_routes_json.write_text(
            json.dumps(
                {
                    "candidate_id": selected_candidate["candidate_id"],
                    "topology_family": selected_candidate["topology_family"],
                    "generation_source": selected_candidate.get("generation_source"),
                    "generation_metadata": selected_candidate.get("generation_metadata", {}),
                    "routes": selected_candidate["metrics"]["route_metrics"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        exported["selected_candidate_routes_json"] = selected_candidate_routes_json

        selected_candidate_score_json = out_dir / "selected_candidate_score_breakdown.json"
        selected_candidate_score_json.write_text(
            json.dumps(
                {
                    "profile_id": selected_profile_id,
                    "candidate_id": selected_candidate["candidate_id"],
                    "quality_score_breakdown": selected_candidate["metrics"].get("quality_score_breakdown", []),
                    "quality_flags": selected_candidate["metrics"].get("quality_flags", []),
                    "rules_triggered": selected_candidate["metrics"].get("rules_triggered", []),
                    "selection_log": selected_candidate["payload"].get("selection_log", []),
                    "route_hydraulic_summary": [
                        {
                            "route_id": route.get("route_id"),
                            "feasible": route.get("feasible"),
                            "reason": route.get("reason"),
                            "route_effective_q_max_lpm": route.get("route_effective_q_max_lpm"),
                            "hydraulic_slack_lpm": route.get("hydraulic_slack_lpm"),
                            "total_loss_lpm_equiv": route.get("total_loss_lpm_equiv"),
                            "bottleneck_component_id": route.get("bottleneck_component_id"),
                            "critical_consequence": route.get("critical_consequence"),
                        }
                        for route in selected_candidate["metrics"].get("route_metrics", [])
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        exported["selected_candidate_score_breakdown_json"] = selected_candidate_score_json

        selected_candidate_render_json = out_dir / "selected_candidate_render.json"
        selected_candidate_render_json.write_text(
            json.dumps(
                {
                    "candidate_id": selected_candidate["candidate_id"],
                    "topology_family": selected_candidate["topology_family"],
                    "render": selected_candidate["render"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        exported["selected_candidate_render_json"] = selected_candidate_render_json

        selected_candidate_bom_csv = out_dir / "selected_candidate_bom.csv"
        bom_frame = pd.DataFrame(selected_candidate["metrics"]["bom_summary"]["components"]).copy()
        if not bom_frame.empty:
            bom_frame.insert(0, "candidate_id", selected_candidate["candidate_id"])
        else:
            bom_frame = pd.DataFrame([{"candidate_id": selected_candidate["candidate_id"]}])
        bom_frame.to_csv(selected_candidate_bom_csv, index=False)
        exported["selected_candidate_bom_csv"] = selected_candidate_bom_csv

        selected_candidate_svg = out_dir / "selected_candidate.svg"
        selected_candidate_svg.write_text(_build_svg(selected_candidate["render"]), encoding="utf-8")
        exported["selected_candidate_svg"] = selected_candidate_svg

        try:
            selected_candidate_png = out_dir / "selected_candidate.png"
            _build_png(selected_candidate["render"], selected_candidate_png)
            exported["selected_candidate_png"] = selected_candidate_png
        except Exception:
            pass
    return exported


def _json_ready_catalog(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": item["candidate_id"],
            "topology_family": item["topology_family"],
            "generation_source": item["generation_source"],
            "generation_metadata": item.get("generation_metadata", {}),
            "installed_link_ids": item["installed_link_ids"],
            "metrics": item["metrics"],
            "render": item["render"],
        }
        for item in items
    ]


def _build_catalog_summary(
    candidates: list[dict[str, Any]],
    evaluated: list[dict[str, Any]],
    generation_report: dict[str, Any],
) -> dict[str, Any]:
    family_counts: dict[str, int] = {}
    feasible_by_family: dict[str, int] = {}
    infeasible_candidates_by_family: dict[str, int] = {}
    repaired_count = 0
    infeasible_by_reason: dict[str, int] = {}
    infeasible_routes_by_family: dict[str, int] = {}
    feasible_costs: list[float] = []
    feasible_costs_by_family: dict[str, list[float]] = {}
    for candidate in candidates:
        family = candidate["topology_family"]
        family_counts[family] = family_counts.get(family, 0) + 1
        repaired_count += int(bool(candidate.get("metadata", {}).get("repaired", False)))
    for item in evaluated:
        family = item["topology_family"]
        if bool(item["metrics"]["feasible"]):
            feasible_by_family[family] = feasible_by_family.get(family, 0) + 1
            total_cost = float(item["metrics"].get("install_cost", 0.0)) + float(item["metrics"].get("fallback_cost", 0.0))
            feasible_costs.append(total_cost)
            feasible_costs_by_family.setdefault(family, []).append(total_cost)
        else:
            infeasible_candidates_by_family[family] = infeasible_candidates_by_family.get(family, 0) + 1
            reason = str(item["metrics"].get("infeasibility_reason") or "unknown")
            infeasible_by_reason[reason] = infeasible_by_reason.get(reason, 0) + 1
        for route in item["metrics"]["route_metrics"]:
            if route.get("feasible", True):
                continue
            reason = str(route.get("reason", "unknown"))
            infeasible_routes_by_family[family] = infeasible_routes_by_family.get(family, 0) + 1
    viability_rate_by_family = {
        family: round(feasible_by_family.get(family, 0) / max(count, 1), 4)
        for family, count in family_counts.items()
    }
    infeasible_candidate_rate_by_reason = {
        reason: round(count / max(len(evaluated), 1), 4)
        for reason, count in sorted(infeasible_by_reason.items())
    }
    return {
        "candidate_count": len(candidates),
        "candidates_by_family": family_counts,
        "feasible_by_family": feasible_by_family,
        "infeasible_candidates_by_family": infeasible_candidates_by_family,
        "viability_rate_by_family": viability_rate_by_family,
        "infeasible_candidate_rate_by_reason": infeasible_candidate_rate_by_reason,
        "feasible_cost_distribution": viable_cost_distribution(feasible_costs),
        "feasible_cost_distribution_by_family": {
            family: viable_cost_distribution(values)
            for family, values in sorted(feasible_costs_by_family.items())
        },
        "infeasible_routes_by_family": infeasible_routes_by_family,
        "repair_rate": round(repaired_count / max(len(candidates), 1), 4),
        "infeasible_rate_by_reason": infeasible_by_reason,
        "generation_report": generation_report,
    }


def _build_decision_summary(
    result: dict[str, Any],
    selected_profile_id: str | None,
    selected_candidate: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = dict(result.get("summary", {}))
    summary["scenario_id"] = result.get("scenario_id")
    summary["default_profile_id"] = selected_profile_id
    summary["best_profile"] = selected_profile_id
    if selected_candidate is None:
        summary["selected_candidate_id"] = None
        return summary
    metrics = selected_candidate["metrics"]
    route_hydraulic_summary = [
        {
            "route_id": route.get("route_id"),
            "feasible": route.get("feasible"),
            "reason": route.get("reason"),
            "route_effective_q_max_lpm": route.get("route_effective_q_max_lpm"),
            "hydraulic_slack_lpm": route.get("hydraulic_slack_lpm"),
            "total_loss_lpm_equiv": route.get("total_loss_lpm_equiv"),
            "bottleneck_component_id": route.get("bottleneck_component_id"),
            "critical_consequence": route.get("critical_consequence"),
        }
        for route in metrics.get("route_metrics", [])
    ]
    summary.update(
        {
            "selected_candidate_id": selected_candidate["candidate_id"],
            "selected_topology_family": selected_candidate["topology_family"],
            "selected_generation_source": selected_candidate.get("generation_source"),
            "selected_lineage_label": selected_candidate.get("generation_metadata", {}).get("lineage_label"),
            "engine_requested": metrics.get("engine_requested"),
            "engine_used": metrics.get("engine_used"),
            "engine_mode": metrics.get("engine_mode"),
            "julia_available": metrics.get("julia_available"),
            "watermodels_available": metrics.get("watermodels_available"),
            "feasible": bool(metrics.get("feasible")),
            "total_cost": float(metrics.get("install_cost", 0.0)) + float(metrics.get("fallback_cost", 0.0)),
            "install_cost": float(metrics.get("install_cost", 0.0)),
            "fallback_cost": float(metrics.get("fallback_cost", 0.0)),
            "quality_total": float(metrics.get("quality_score_raw", 0.0)),
            "flow_total": float(metrics.get("flow_out_score", 0.0)),
            "resilience_total": float(metrics.get("resilience_score", 0.0)),
            "operability_total": float(metrics.get("operability_score", 0.0)),
            "cleaning_total": float(metrics.get("cleaning_score", 0.0)),
            "maintenance_total": float(metrics.get("maintenance_score", 0.0)),
            "fallback_component_count": int(metrics.get("fallback_component_count", 0)),
            "infeasibility_reason": metrics.get("infeasibility_reason"),
            "constraint_failure_count": int(metrics.get("constraint_failure_count", 0)),
            "constraint_failure_categories": metrics.get("constraint_failure_categories", {}),
            "constraint_failures": metrics.get("constraint_failures", []),
            "mandatory_failed_route_ids": metrics.get("mandatory_failed_route_ids", []),
            "route_count": len(metrics.get("route_metrics", [])),
            "bom_component_count": int(metrics.get("bom_summary", {}).get("total_components", 0)),
            "route_hydraulic_summary": route_hydraulic_summary,
        }
    )
    return summary


def _get_default_profile_id(bundle: ScenarioBundle) -> str:
    configured = str(bundle.scenario_settings.get("ranking", {}).get("default_profile", "")).strip()
    if configured:
        return configured
    return str(bundle.weight_profiles["profile_id"].iloc[0])


def resolve_selected_candidate(
    result: dict[str, Any],
    profile_id: str | None = None,
    ranked_records: list[dict[str, Any]] | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    resolved_profile_id = profile_id or result.get("default_profile_id")
    if ranked_records is None:
        ranked_records = result.get("ranked_profiles", {}).get(resolved_profile_id or "", [])
    return _resolve_selected_candidate(result.get("catalog", []), ranked_records)


def _resolve_selected_candidate(
    catalog: list[dict[str, Any]],
    ranked_records: list[dict[str, Any]],
) -> tuple[str | None, dict[str, Any] | None]:
    if not ranked_records:
        return None, None
    selected_candidate_id = str(ranked_records[0]["candidate_id"])
    selected_candidate = next(
        (candidate for candidate in catalog if candidate["candidate_id"] == selected_candidate_id),
        None,
    )
    return selected_candidate_id, selected_candidate


def _build_svg(render_payload: dict[str, Any]) -> str:
    node_elements = []
    edge_elements = []
    for element in render_payload.get("cytoscape_elements", []):
        data = element.get("data", {})
        position = element.get("position")
        if position:
            node_id = str(data.get("id", ""))
            x = float(position.get("x", 0.0))
            y = float(position.get("y", 0.0))
            node_elements.append(
                f'<g class="node"><circle cx="{x:.1f}" cy="{y:.1f}" r="18" fill="#1f77b4" opacity="0.9" />'
                f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" font-size="12" fill="#ffffff">{node_id}</text></g>'
            )
        elif "source" in data and "target" in data:
            edge_elements.append((str(data["source"]), str(data["target"]), str(data.get("label", ""))))
    node_positions = {
        str(element.get("data", {}).get("id", "")): element.get("position", {})
        for element in render_payload.get("cytoscape_elements", [])
        if element.get("position")
    }
    svg_edges = []
    for source, target, label in edge_elements:
        src = node_positions.get(source, {})
        dst = node_positions.get(target, {})
        if not src or not dst:
            continue
        x1 = float(src.get("x", 0.0))
        y1 = float(src.get("y", 0.0))
        x2 = float(dst.get("x", 0.0))
        y2 = float(dst.get("y", 0.0))
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        svg_edges.append(
            f'<g class="edge"><line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#555555" stroke-width="3" />'
            f'<text x="{mx:.1f}" y="{my - 6:.1f}" text-anchor="middle" font-size="10" fill="#333333">{label}</text></g>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="560" viewBox="0 0 960 560">'
        '<rect width="100%" height="100%" fill="#f9fbfd" />'
        + "".join(svg_edges)
        + "".join(node_elements)
        + "</svg>"
    )


def _build_png(render_payload: dict[str, Any], output_path: Path) -> None:
    node_positions = {
        str(element.get("data", {}).get("id", "")): element.get("position", {})
        for element in render_payload.get("cytoscape_elements", [])
        if element.get("position")
    }
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor("#f9fbfd")
    fig.patch.set_facecolor("#f9fbfd")
    for element in render_payload.get("cytoscape_elements", []):
        data = element.get("data", {})
        if "source" not in data or "target" not in data:
            continue
        src = node_positions.get(str(data["source"]), {})
        dst = node_positions.get(str(data["target"]), {})
        if not src or not dst:
            continue
        x1, y1 = float(src.get("x", 0.0)), float(src.get("y", 0.0))
        x2, y2 = float(dst.get("x", 0.0)), float(dst.get("y", 0.0))
        ax.plot([x1, x2], [y1, y2], color="#555555", linewidth=2.5, zorder=1)
        ax.text((x1 + x2) / 2.0, (y1 + y2) / 2.0 - 8, str(data.get("label", "")), fontsize=8, ha="center", color="#333333")
    for node_id, position in node_positions.items():
        x, y = float(position.get("x", 0.0)), float(position.get("y", 0.0))
        ax.scatter([x], [y], s=500, color="#1f77b4", zorder=2)
        ax.text(x, y, node_id, fontsize=9, ha="center", va="center", color="white", zorder=3)
    ax.set_xlim(0, 960)
    ax.set_ylim(560, 0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def _enrich_viability_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(metrics)
    enriched.update(summarize_constraint_failures(enriched))
    return enriched
