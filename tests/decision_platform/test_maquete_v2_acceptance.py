from __future__ import annotations

from pathlib import Path
import shutil

from decision_platform.api.run_pipeline import run_decision_pipeline
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
