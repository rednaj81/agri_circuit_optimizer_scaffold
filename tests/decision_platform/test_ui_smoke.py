from __future__ import annotations

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.ui_dash.app import build_app, build_candidate_detail
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


def test_dash_app_builds_layout_and_callbacks_even_when_fail_closed() -> None:
    app = build_app("data/decision_platform/maquete_v2")

    assert hasattr(app, "layout")
    assert app.layout is not None
    assert len(getattr(app, "callbacks", [])) >= 4


def test_dash_app_uses_pipeline_result_when_fallback_is_allowed() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_fallback",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        app = build_app(scenario_dir)
        assert hasattr(app, "layout")
        assert app.layout is not None
        detail = build_candidate_detail(run_decision_pipeline(scenario_dir), None)
        assert "breakdown" in detail
    finally:
        cleanup_scenario_copy(scenario_dir)
