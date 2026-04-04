from __future__ import annotations

import pytest

from decision_platform.ui_dash.app import build_catalog_view_state, filter_catalog_records, rerank_catalog


@pytest.mark.slow
def test_catalog_contains_viable_and_ranked_candidates(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    result = maquete_v2_fallback_runtime["result"]
    assert len(result["catalog"]) >= 8
    assert sum(1 for item in result["catalog"] if item["metrics"]["feasible"]) >= 1
    assert "balanced" in result["ranked_profiles"]
    assert result["ranked_profiles"]["balanced"][0]["score_final"] >= result["ranked_profiles"]["balanced"][-1]["score_final"]
    assert result["default_profile_id"] == "balanced"
    assert result["selected_candidate_id"] == result["selected_candidate"]["candidate_id"]
    assert result["selected_candidate_id"] == result["ranked_profiles"][result["default_profile_id"]][0]["candidate_id"]
    assert "candidates_by_family" in result["summary"]
    assert "viability_rate_by_family" in result["summary"]
    assert "feasible_cost_distribution" in result["summary"]


@pytest.mark.slow
def test_ranking_profiles_change_priorities_and_filtering(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    result = maquete_v2_fallback_runtime["result"]
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
    filtered = filter_catalog_records(reranked, family="bus_with_pump_islands", feasible_only=True, max_cost=600)
    assert min_cost_top
    assert robust_top
    assert reranked
    assert filtered
    assert all(record["topology_family"] == "bus_with_pump_islands" for record in filtered)


@pytest.mark.slow
def test_selected_candidate_changes_with_profile_in_ui_view_state(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    result = maquete_v2_fallback_runtime["result"]
    balanced_state = build_catalog_view_state(result, profile_id=result["default_profile_id"])
    min_cost_state = build_catalog_view_state(result, profile_id="min_cost")
    assert balanced_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert min_cost_state["selected_candidate_id"] == result["ranked_profiles"]["min_cost"][0]["candidate_id"]
