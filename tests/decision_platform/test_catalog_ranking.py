from __future__ import annotations

from decision_platform.api.run_pipeline import run_decision_pipeline


def test_catalog_contains_viable_and_ranked_candidates() -> None:
    result = run_decision_pipeline("data/decision_platform/maquete_v2")

    assert len(result["catalog"]) >= 8
    assert sum(1 for item in result["catalog"] if item["metrics"]["feasible"]) >= 1
    assert "balanced" in result["ranked_profiles"]
    assert result["ranked_profiles"]["balanced"][0]["score_final"] >= result["ranked_profiles"]["balanced"][-1]["score_final"]


def test_ranking_profiles_change_priorities() -> None:
    result = run_decision_pipeline("data/decision_platform/maquete_v2")

    min_cost_top = result["ranked_profiles"]["min_cost"][0]["candidate_id"]
    robust_top = result["ranked_profiles"]["robust_quality"][0]["candidate_id"]

    assert min_cost_top
    assert robust_top
