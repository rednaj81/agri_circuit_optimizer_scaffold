from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from decision_platform.catalog.quality_rules import apply_quality_rules
from decision_platform.data_io.loader import ScenarioBundle
from decision_platform.graph_generation.generator import generate_candidate_topologies
from decision_platform.graph_repair.repair import normalize_candidate
from decision_platform.julia_bridge.bridge import evaluate_candidate_via_bridge
from decision_platform.ranking.scoring import apply_weight_profile
from decision_platform.rendering.circuit import build_render_payload
from decision_platform.scenario_engine.installer import build_candidate_payload


def build_solution_catalog(bundle: ScenarioBundle) -> dict[str, Any]:
    candidates = [normalize_candidate(candidate, bundle) for candidate in generate_candidate_topologies(bundle)]
    evaluated = []
    for candidate in candidates:
        payload = build_candidate_payload(candidate, bundle)
        metrics = apply_quality_rules(evaluate_candidate_via_bridge(payload, bundle), bundle)
        render = build_render_payload(candidate, bundle, metrics)
        evaluated.append(
            {
                "candidate_id": candidate["candidate_id"],
                "topology_family": candidate["topology_family"],
                "generation_source": candidate["generation_source"],
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
            }
            for item in evaluated
        ]
    )
    ranked_profiles = {
        profile_id: apply_weight_profile(catalog_frame, bundle.weight_profiles, profile_id)
        for profile_id in bundle.weight_profiles["profile_id"].tolist()
    }
    summary = _build_catalog_summary(candidates, evaluated)
    return {
        "scenario_id": bundle.scenario_settings.get("scenario_id", bundle.base_dir.name),
        "catalog": evaluated,
        "catalog_frame": catalog_frame,
        "ranked_profiles": ranked_profiles,
        "summary": summary,
    }


def export_catalog(result: dict[str, Any], output_dir: str | Path) -> dict[str, Path]:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    exported: dict[str, Path] = {}
    catalog_frame = result["catalog_frame"].copy()

    catalog_csv = out_dir / "catalog.csv"
    catalog_frame.to_csv(catalog_csv, index=False)
    exported["catalog_csv"] = catalog_csv

    try:
        catalog_parquet = out_dir / "catalog.parquet"
        catalog_frame.to_parquet(catalog_parquet, index=False)
        exported["catalog_parquet"] = catalog_parquet
    except Exception:
        pass

    ranking_json = out_dir / "ranking_profiles.json"
    ranking_json.write_text(json.dumps(result["ranked_profiles"], indent=2, ensure_ascii=False), encoding="utf-8")
    exported["ranking_profiles"] = ranking_json

    detailed_json = out_dir / "catalog_detailed.json"
    detailed_json.write_text(json.dumps(_json_ready_catalog(result["catalog"]), indent=2, ensure_ascii=False), encoding="utf-8")
    exported["catalog_detailed"] = detailed_json

    summary_json = out_dir / "catalog_summary.json"
    summary_json.write_text(json.dumps(result.get("summary", {}), indent=2, ensure_ascii=False), encoding="utf-8")
    exported["catalog_summary"] = summary_json

    for item in result["catalog"]:
        candidate_dir = out_dir / item["candidate_id"]
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "solution.json").write_text(
            json.dumps(_json_ready_catalog([item])[0], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        pd.DataFrame(item["metrics"]["bom_summary"]["components"]).to_csv(candidate_dir / "bom.csv", index=False)
    return exported


def _json_ready_catalog(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": item["candidate_id"],
            "topology_family": item["topology_family"],
            "generation_source": item["generation_source"],
            "installed_link_ids": item["installed_link_ids"],
            "metrics": item["metrics"],
            "render": item["render"],
        }
        for item in items
    ]


def _build_catalog_summary(candidates: list[dict[str, Any]], evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    family_counts: dict[str, int] = {}
    feasible_by_family: dict[str, int] = {}
    repaired_count = 0
    infeasible_by_reason: dict[str, int] = {}
    for candidate in candidates:
        family = candidate["topology_family"]
        family_counts[family] = family_counts.get(family, 0) + 1
        repaired_count += int(bool(candidate.get("metadata", {}).get("repaired", False)))
    for item in evaluated:
        family = item["topology_family"]
        if bool(item["metrics"]["feasible"]):
            feasible_by_family[family] = feasible_by_family.get(family, 0) + 1
        for route in item["metrics"]["route_metrics"]:
            if route.get("feasible", True):
                continue
            reason = str(route.get("reason", "unknown"))
            infeasible_by_reason[reason] = infeasible_by_reason.get(reason, 0) + 1
    return {
        "candidate_count": len(candidates),
        "candidates_by_family": family_counts,
        "feasible_by_family": feasible_by_family,
        "repair_rate": round(repaired_count / max(len(candidates), 1), 4),
        "infeasible_rate_by_reason": infeasible_by_reason,
    }
