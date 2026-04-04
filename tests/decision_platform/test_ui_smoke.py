from __future__ import annotations

import pytest

from decision_platform.ui_dash._compat import DASH_AVAILABLE
from decision_platform.ui_dash.app import (
    build_app,
    build_candidate_detail,
    build_comparison_records,
    build_official_candidate_summary,
    build_catalog_view_state,
    filter_catalog_records,
    rerank_catalog,
)

pytestmark = [pytest.mark.requires_dash, pytest.mark.ui]


def test_dash_app_builds_layout_and_callbacks_even_when_fail_closed() -> None:
    app = build_app("data/decision_platform/maquete_v2")

    assert hasattr(app, "layout")
    assert app.layout is not None
    callback_count = len(getattr(app, "callbacks", [])) or len(getattr(app, "callback_map", {}))
    assert callback_count >= 4


def test_real_dash_stack_is_available() -> None:
    assert DASH_AVAILABLE is True


@pytest.mark.slow
def test_dash_app_uses_pipeline_result_when_fallback_is_allowed(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    scenario_dir = maquete_v2_fallback_runtime["scenario_dir"]
    result = maquete_v2_fallback_runtime["result"]
    app = build_app(scenario_dir)
    assert hasattr(app, "layout")
    assert app.layout is not None
    detail = build_candidate_detail(result, result["selected_candidate_id"])
    assert "breakdown" in detail
    assert detail["summary"]["candidate_id"] == result["selected_candidate_id"]
    assert detail["route_rows"]


@pytest.mark.slow
def test_ui_view_state_uses_official_selected_candidate_instead_of_catalog_first(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    manipulated = {**result, "catalog": list(reversed(result["catalog"]))}
    view_state = build_catalog_view_state(
        manipulated,
        profile_id=manipulated["default_profile_id"],
    )
    detail = build_candidate_detail(result, view_state["selected_candidate_id"])
    assert view_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert view_state["selected_candidate_id"] != manipulated["catalog"][0]["candidate_id"]
    assert detail["cytoscape_elements"] == result["selected_candidate"]["render"]["cytoscape_elements"]
    assert detail["summary"]["generation_source"] == result["selected_candidate"]["generation_source"]


@pytest.mark.slow
def test_catalog_filters_include_quality_resilience_flow_and_fallback(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    ranked = rerank_catalog(result, "balanced")
    filtered = filter_catalog_records(
        ranked,
        family="ALL",
        feasible_only=True,
        max_cost=1000,
        min_quality=50,
        min_flow=5,
        min_resilience=10,
        min_cleaning=0,
        min_operability=0,
        top_n_per_family=2,
        fallback_filter="WITH_FALLBACK",
    )
    assert filtered
    assert all(record["feasible"] for record in filtered)
    assert all(float(record["quality_score_raw"]) >= 50 for record in filtered)
    assert all(float(record["flow_out_score"]) >= 5 for record in filtered)
    assert all(float(record["resilience_score"]) >= 10 for record in filtered)
    assert all(int(record["fallback_component_count"]) > 0 for record in filtered)


@pytest.mark.slow
def test_reranking_changes_visible_selected_candidate_when_weights_change(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    default_state = build_catalog_view_state(result, profile_id=result["default_profile_id"])
    reranked_state = build_catalog_view_state(
        result,
        profile_id=result["default_profile_id"],
        weight_overrides={
            "cost_weight": 1.0,
            "quality_weight": 0.0,
            "flow_weight": 0.0,
            "resilience_weight": 0.0,
            "cleaning_weight": 0.0,
            "operability_weight": 0.0,
        },
    )
    assert default_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert reranked_state["selected_candidate_id"] == reranked_state["ranked_records"][0]["candidate_id"]


@pytest.mark.slow
def test_ui_summary_and_comparison_records_expose_decision_fields(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    result = maquete_v2_fallback_runtime["result"]
    official = build_official_candidate_summary(
        result,
        profile_id=result["default_profile_id"],
        candidate_id=result["selected_candidate_id"],
    )
    comparison = build_comparison_records(
        result,
        [record["candidate_id"] for record in result["ranked_profiles"]["balanced"][:2]],
        profile_id=result["default_profile_id"],
    )
    assert official["candidate_id"] == result["selected_candidate_id"]
    assert "critical_routes" in official
    assert comparison
    assert all("score_final" in row for row in comparison)
