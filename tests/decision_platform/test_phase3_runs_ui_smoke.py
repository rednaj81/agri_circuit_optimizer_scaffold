from __future__ import annotations

import json

import pytest

from decision_platform.api.run_pipeline import create_run_job, rerun_run_job, run_next_queued_job
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


def _collect_text(component: object) -> str:
    if component is None:
        return ""
    if isinstance(component, str):
        return component
    if isinstance(component, (int, float, bool)):
        return str(component)
    children = getattr(component, "children", None)
    if children is None:
        return ""
    child_items = children if isinstance(children, (list, tuple)) else [children]
    return "".join(_collect_text(child) for child in child_items)


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
            rerun_job = rerun_run_job(created_job["run_id"], queue_root=queue_root)
            rerun_result = run_next_queued_job(queue_root=queue_root)
            app = build_app(
                scenario_dir,
                run_queue_root=queue_root,
                bootstrap_pipeline=False,
            )

        runs_summary = _find_component_by_id(app.layout, "run-jobs-summary")
        run_detail = _find_component_by_id(app.layout, "run-job-detail")
        assert runs_summary is not None
        assert run_detail is not None

        summary_payload = json.loads(runs_summary.children)
        detail_payload = json.loads(run_detail.children)
        assert completed_job is not None
        assert rerun_result is not None
        assert summary_payload["queue_state"] == "idle"
        assert summary_payload["latest_run_id"] == rerun_job["run_id"]
        assert len(summary_payload["runs"]) == 2
        rerun_summary = next(run for run in summary_payload["runs"] if run["run_id"] == rerun_job["run_id"])
        assert rerun_summary["lineage"]["is_rerun"] is True
        assert rerun_summary["lineage"]["source_run_id"] == created_job["run_id"]
        assert rerun_summary["summary_source"] == "persisted_queue_summary"
        assert rerun_summary["evidence_summary"]["has_summary_json"] is True
        assert rerun_summary["evidence_summary"]["final_status_recorded"] is True
        assert detail_payload["selected_run_id"] == rerun_job["run_id"]
        assert detail_payload["rerun_of_run_id"] == created_job["run_id"]
        assert detail_payload["queue_summary"]["source"] == "persisted_queue_summary"
        assert detail_payload["queue_summary"]["refresh_path"] == "canonical_persist_run_job"
        assert detail_payload["queue_summary"]["lineage"] == rerun_summary["lineage"]
        assert detail_payload["queue_summary"]["evidence_summary"] == rerun_summary["evidence_summary"]
        assert detail_payload["engine_requested"] == "watermodels_jl"
        assert detail_payload["engine_used"] == "python_emulated_julia"
        assert detail_payload["execution_mode"] == "diagnostic"
        assert detail_payload["policy_mode"] == "diagnostic_override_probe_disabled"
        assert detail_payload["failure_reason"] is None
        assert detail_payload["source_bundle_reference_path"] == rerun_job["source_bundle_reference_path"]
        assert detail_payload["source_bundle_reference"]["run_id"] == rerun_job["run_id"]
        assert detail_payload["source_bundle_reference"]["rerun_source"]["source_run_id"] == created_job["run_id"]
        assert detail_payload["source_bundle_reference"]["scenario_provenance"]["bundle_manifest"]
        assert detail_payload["evidence"]["run_id"] == rerun_job["run_id"]
        assert detail_payload["evidence"]["artifact_expectation"] == "summary_artifacts_expected"
        assert detail_payload["evidence"]["has_summary_json"] is True
        assert detail_payload["evidence"]["run_dir_isolated"] is True
        assert detail_payload["evidence"]["final_status_logged"] is True
        assert detail_payload["telemetry"]["duration_s"] == detail_payload["duration_s"]
        assert detail_payload["inspection"]["queue_root"] == str(queue_root.resolve())
        assert detail_payload["inspection"]["artifacts_dir"] == rerun_result["artifacts_dir"]
        assert detail_payload["inspection"]["queue_summary_source"] == "persisted_queue_summary"
        assert detail_payload["inspection"]["source_bundle_reference_path"] == rerun_job["source_bundle_reference_path"]

        runs_workspace = _find_component_by_id(app.layout, "runs-workspace-panel")
        runs_overview = _find_component_by_id(app.layout, "run-jobs-overview-panel")
        run_detail_panel = _find_component_by_id(app.layout, "run-job-detail-panel")
        assert runs_workspace is not None
        assert runs_overview is not None
        assert run_detail_panel is not None

        workspace_text = _collect_text(runs_workspace)
        overview_text = _collect_text(runs_overview)
        detail_text = _collect_text(run_detail_panel)
        assert "Próxima ação segura" in workspace_text
        assert "Histórico terminal secundário" in workspace_text
        assert _find_component_by_id(runs_workspace, "runs-workspace-progress-rail") is not None
        assert "Estados da operação" in overview_text
        assert "Reexecução" in overview_text
        assert "Origem desta rodada" in detail_text
        assert "Passagem Runs -> Decisão" in detail_text
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)
