from __future__ import annotations

import json

import pytest

from decision_platform.api.run_pipeline import create_run_job, run_next_queued_job
from decision_platform.ui_dash.app import build_app
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_isolated_tmp_dir,
    prepare_scenario_copy,
)


def _find_component_by_id(component: object, target_id: str) -> object | None:
    if getattr(component, "id", None) == target_id:
        return component
    children = getattr(component, "children", None)
    if children is None:
        return None
    child_items = children if isinstance(children, (list, tuple)) else [children]
    for child in child_items:
        found = _find_component_by_id(child, target_id)
        if found is not None:
            return found
    return None


@pytest.mark.fast
def test_runs_tab_reopens_persisted_operational_telemetry() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_runs_telemetry_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    queue_root = prepare_isolated_tmp_dir("maquete_v2_ui_runs_telemetry_queue")
    try:
        with diagnostic_runtime_test_mode():
            created_job = create_run_job(
                scenario_dir,
                queue_root=queue_root,
                allow_diagnostic_python_emulation=True,
            )
            completed_job = run_next_queued_job(queue_root=queue_root)
            app = build_app(scenario_dir, run_queue_root=queue_root)

        runs_summary = _find_component_by_id(app.layout, "run-jobs-summary")
        run_detail = _find_component_by_id(app.layout, "run-job-detail")
        assert runs_summary is not None
        assert run_detail is not None

        summary_payload = json.loads(runs_summary.children)
        detail_payload = json.loads(run_detail.children)
        assert completed_job is not None
        assert summary_payload["queue_state"] == "idle"
        assert summary_payload["latest_run_id"] == created_job["run_id"]
        assert summary_payload["runs"][0]["failure_reason"] is None
        assert detail_payload["selected_run_id"] == created_job["run_id"]
        assert detail_payload["engine_requested"] == "watermodels_jl"
        assert detail_payload["engine_used"] == "python_emulated_julia"
        assert detail_payload["execution_mode"] == "diagnostic"
        assert detail_payload["policy_mode"] == "diagnostic_override_probe_disabled"
        assert detail_payload["failure_reason"] is None
        assert detail_payload["telemetry"]["duration_s"] == detail_payload["duration_s"]
        assert detail_payload["inspection"]["queue_root"] == str(queue_root.resolve())
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)
