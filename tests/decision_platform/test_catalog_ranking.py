from __future__ import annotations

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.ui_dash.app import filter_catalog_records, rerank_catalog
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


def test_catalog_contains_viable_and_ranked_candidates() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_catalog_fallback",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        result = run_decision_pipeline(scenario_dir)
        assert len(result["catalog"]) >= 8
        assert sum(1 for item in result["catalog"] if item["metrics"]["feasible"]) >= 1
        assert "balanced" in result["ranked_profiles"]
        assert result["ranked_profiles"]["balanced"][0]["score_final"] >= result["ranked_profiles"]["balanced"][-1]["score_final"]
        assert "candidates_by_family" in result["summary"]
    finally:
        cleanup_scenario_copy(scenario_dir)


def test_ranking_profiles_change_priorities_and_filtering() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ranking_fallback",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        result = run_decision_pipeline(scenario_dir)
        min_cost_top = result["ranked_profiles"]["min_cost"][0]["candidate_id"]
        robust_top = result["ranked_profiles"]["robust_quality"][0]["candidate_id"]
        reranked = rerank_catalog(
            result,
            "balanced",
            {
                "cost_weight": 0.2,
                "quality_weight": 0.3,
                "flow_weight": 0.1,
                "resilience_weight": 0.2,
                "cleaning_weight": 0.1,
                "operability_weight": 0.1,
            },
        )
        filtered = filter_catalog_records(reranked, family="bus_with_pump_islands", feasible_only=True, max_cost=400)
        assert min_cost_top
        assert robust_top
        assert reranked
        assert filtered
        assert all(record["topology_family"] == "bus_with_pump_islands" for record in filtered)
    finally:
        cleanup_scenario_copy(scenario_dir)
