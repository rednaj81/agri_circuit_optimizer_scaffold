from __future__ import annotations

from pathlib import Path
import shutil

import json
import pandas as pd
import pytest

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.julia_bridge.bridge import watermodels_available
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


@pytest.mark.slow
def test_maquete_v2_pipeline_exports_and_route_metrics() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_acceptance_fallback",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = Path("tests/_tmp/decision_platform_maquete_v2_out")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        result = run_decision_pipeline(scenario_dir, output_dir)

        assert result["scenario_id"] == "maquete_v2"
        assert result["default_profile_id"] == "balanced"
        assert result["selected_candidate_id"] == result["selected_candidate"]["candidate_id"]
        feasible = [item for item in result["catalog"] if item["metrics"]["feasible"]]
        infeasible = [item for item in result["catalog"] if not item["metrics"]["feasible"]]

        assert feasible
        assert infeasible
        assert any(route["cleaning_volume_l"] >= 0 for item in feasible for route in item["metrics"]["route_metrics"])
        assert any(route["selected_meter_id"] for item in feasible for route in item["metrics"]["route_metrics"] if route["feasible"])
        assert any("total_loss_lpm_equiv" in route for item in feasible for route in item["metrics"]["route_metrics"])
        assert any("bottleneck_component_id" in route for item in feasible for route in item["metrics"]["route_metrics"])
        assert any(item["metrics"]["quality_score_breakdown"] for item in feasible)
        assert any(item["payload"]["selection_log"] for item in feasible)

        summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
        engine_comparison = json.loads((output_dir / "engine_comparison.json").read_text(encoding="utf-8"))
        selected_candidate = json.loads((output_dir / "selected_candidate.json").read_text(encoding="utf-8"))
        selected_routes = json.loads((output_dir / "selected_candidate_routes.json").read_text(encoding="utf-8"))
        selected_render = json.loads((output_dir / "selected_candidate_render.json").read_text(encoding="utf-8"))
        selected_breakdown = json.loads((output_dir / "selected_candidate_score_breakdown.json").read_text(encoding="utf-8"))
        selected_bom = pd.read_csv(output_dir / "selected_candidate_bom.csv")

        assert (output_dir / "catalog.csv").exists()
        assert (output_dir / "catalog.json").exists()
        assert (output_dir / "catalog_detailed.json").exists()
        assert (output_dir / "ranked_profiles.json").exists()
        assert (output_dir / "ranking_profiles.json").exists()
        assert (output_dir / "catalog_summary.json").exists()
        assert (output_dir / "engine_comparison.json").exists()
        assert (output_dir / "selected_candidate.svg").exists()

        assert summary["default_profile_id"] == result["default_profile_id"]
        assert summary["selected_candidate_id"] == result["selected_candidate_id"]
        assert summary["selected_generation_source"] == result["selected_candidate"]["generation_source"]
        assert "viability_rate_by_family" in summary
        assert "infeasible_candidate_rate_by_reason" in summary
        assert "feasible_cost_distribution" in summary
        assert selected_candidate["candidate_id"] == result["selected_candidate_id"]
        assert "generation_metadata" in selected_candidate
        assert selected_routes["candidate_id"] == result["selected_candidate_id"]
        assert selected_render["candidate_id"] == result["selected_candidate_id"]
        assert selected_breakdown["candidate_id"] == result["selected_candidate_id"]
        assert selected_breakdown["profile_id"] == result["default_profile_id"]
        assert all(selected_bom["candidate_id"] == result["selected_candidate_id"])
        assert selected_routes["topology_family"] == selected_candidate["topology_family"]
        assert selected_render["topology_family"] == selected_candidate["topology_family"]
        assert selected_render["render"] == selected_candidate["render"]
        assert selected_routes["routes"] == selected_candidate["metrics"]["route_metrics"]
        assert all("route_effective_q_max_lpm" in route for route in selected_routes["routes"])
        assert all("critical_consequence" in route for route in selected_routes["routes"])
        assert summary["constraint_failure_categories"] == result["selected_candidate"]["metrics"]["constraint_failure_categories"]
        assert engine_comparison["scenario_comparisons"]["maquete_v2"]["decision_difference_observed"] is True
        assert engine_comparison["scenario_comparisons"]["maquete_v2"]["selected_candidate"]["same"] is False
        assert engine_comparison["scenario_comparisons"]["hybrid_free_focus_variant"]["selected_candidate"]["same"] is False
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.requires_julia
@pytest.mark.slow
def test_maquete_v2_pipeline_runs_with_real_julia_and_exports_final_artifacts() -> None:
    if not watermodels_available():
        pytest.skip("Real Julia/WaterModels runtime is not available.")
    output_dir = Path("tests/_tmp/decision_platform_maquete_v2_real_out")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        result = run_decision_pipeline("data/decision_platform/maquete_v2", output_dir)
        assert result["scenario_id"] == "maquete_v2"
        selected_item = result["selected_candidate"]
        assert selected_item["metrics"]["engine_requested"] == "watermodels_jl"
        assert selected_item["metrics"]["engine_used"] == "watermodels_jl"
        assert selected_item["metrics"]["engine_mode"] == "real_julia"
        assert selected_item["metrics"]["julia_available"] is True
        assert selected_item["metrics"]["watermodels_available"] is True
        assert (output_dir / "summary.json").exists()
        assert (output_dir / "catalog.csv").exists()
        assert (output_dir / "catalog.json").exists()
        assert (output_dir / "ranked_profiles.json").exists()
        assert (output_dir / "engine_comparison.json").exists()
        assert (output_dir / "selected_candidate.json").exists()
        assert (output_dir / "selected_candidate_routes.json").exists()
        assert (output_dir / "selected_candidate_bom.csv").exists()
        assert (output_dir / "selected_candidate_score_breakdown.json").exists()
        assert (output_dir / "selected_candidate_render.json").exists()
        assert (output_dir / "selected_candidate.svg").exists()
        summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
        assert summary["selected_candidate_id"] == result["selected_candidate_id"]
        assert summary["default_profile_id"] == result["default_profile_id"]
        assert summary["engine_used"] == "watermodels_jl"
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
