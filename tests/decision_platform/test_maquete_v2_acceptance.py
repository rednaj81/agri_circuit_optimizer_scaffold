from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.julia_bridge.bridge import watermodels_available
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


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
        feasible = [item for item in result["catalog"] if item["metrics"]["feasible"]]
        infeasible = [item for item in result["catalog"] if not item["metrics"]["feasible"]]

        assert feasible
        assert infeasible
        assert any(route["cleaning_volume_l"] >= 0 for item in feasible for route in item["metrics"]["route_metrics"])
        assert any(route["selected_meter_id"] for item in feasible for route in item["metrics"]["route_metrics"] if route["feasible"])
        assert any(item["metrics"]["quality_score_breakdown"] for item in feasible)
        assert any(item["payload"]["selection_log"] for item in feasible)

        assert (output_dir / "catalog.csv").exists()
        assert (output_dir / "catalog_detailed.json").exists()
        assert (output_dir / "ranking_profiles.json").exists()
        assert (output_dir / "catalog_summary.json").exists()
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.requires_julia
def test_maquete_v2_pipeline_runs_with_real_julia_and_exports_final_artifacts() -> None:
    if not watermodels_available():
        pytest.skip("Real Julia/WaterModels runtime is not available.")
    output_dir = Path("tests/_tmp/decision_platform_maquete_v2_real_out")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        result = run_decision_pipeline("data/decision_platform/maquete_v2", output_dir)
        assert result["scenario_id"] == "maquete_v2"
        selected = result["ranked_profiles"]["min_cost"][0]["candidate_id"]
        selected_item = next(item for item in result["catalog"] if item["candidate_id"] == selected)
        assert selected_item["metrics"]["engine_requested"] == "watermodels_jl"
        assert selected_item["metrics"]["engine_used"] == "watermodels_jl"
        assert selected_item["metrics"]["engine_mode"] == "real_julia"
        assert selected_item["metrics"]["julia_available"] is True
        assert selected_item["metrics"]["watermodels_available"] is True
        assert (output_dir / "summary.json").exists()
        assert (output_dir / "catalog.csv").exists()
        assert (output_dir / "catalog.json").exists()
        assert (output_dir / "ranked_profiles.json").exists()
        assert (output_dir / "selected_candidate.json").exists()
        assert (output_dir / "selected_candidate_routes.json").exists()
        assert (output_dir / "selected_candidate_bom.csv").exists()
        assert (output_dir / "selected_candidate_score_breakdown.json").exists()
        assert (output_dir / "selected_candidate_render.json").exists()
        assert (output_dir / "selected_candidate.svg").exists()
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
