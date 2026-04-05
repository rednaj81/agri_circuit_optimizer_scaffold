from __future__ import annotations

import json
from pathlib import Path

import pytest

from decision_platform.api.run_pipeline import (
    cancel_run_job,
    create_run_job,
    inspect_run_job,
    list_run_jobs,
    rerun_run_job,
    run_next_queued_job,
    summarize_run_jobs,
)
from decision_platform.julia_bridge import bridge
from decision_platform.ui_dash.app import build_app
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_maquete_v2_acceptance_scenario,
    prepare_isolated_tmp_dir,
)


@pytest.mark.slow
def test_phase3_queue_acceptance_serial_jobs_are_isolated_and_auditable() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_queue_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    queue_root = prepare_isolated_tmp_dir("phase3_queue_root")
    try:
        with diagnostic_runtime_test_mode():
            first_job = create_run_job(
                scenario_dir,
                queue_root=queue_root,
                allow_diagnostic_python_emulation=True,
            )
            second_job = create_run_job(
                scenario_dir,
                queue_root=queue_root,
                allow_diagnostic_python_emulation=True,
            )
            first_result = run_next_queued_job(queue_root=queue_root)
            after_first = list_run_jobs(queue_root)
            second_result = run_next_queued_job(queue_root=queue_root)
            final_summary = summarize_run_jobs(queue_root)

        assert first_job["status"] == "queued"
        assert second_job["status"] == "queued"
        assert first_result is not None
        assert second_result is not None
        assert first_result["run_id"] != second_result["run_id"]
        assert first_result["status"] == "completed"
        assert second_result["status"] == "completed"
        assert [job["status"] for job in after_first].count("completed") == 1
        assert [job["status"] for job in after_first].count("queued") == 1
        assert final_summary["worker_mode"] == "serial"
        assert final_summary["status_counts"]["completed"] == 2
        assert final_summary["status_counts"]["queued"] == 0

        for completed_job in (first_result, second_result):
            run_dir = Path(completed_job["run_dir"])
            artifacts_dir = Path(completed_job["artifacts"]["artifacts_dir"])
            summary_path = artifacts_dir / "summary.json"
            events_path = Path(completed_job["events_path"])
            log_path = Path(completed_job["log_path"])
            bundle_reference_path = Path(completed_job["source_bundle_reference_path"])

            assert run_dir.parent == queue_root.resolve()
            assert run_dir.exists()
            assert artifacts_dir.exists()
            assert summary_path.exists()
            assert events_path.exists()
            assert log_path.exists()
            assert bundle_reference_path.exists()
            assert completed_job["source_bundle_manifest"].endswith("scenario_bundle.yaml")
            assert completed_job["source_bundle_files"]["components.csv"] == "component_catalog.csv"
            assert completed_job["execution_mode"] == "diagnostic"
            assert completed_job["official_gate_valid"] is False
            assert completed_job["result_summary_path"].endswith("summary.json")

            event_statuses = [
                json.loads(line)["status"]
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert event_statuses == ["queued", "preparing", "running", "exporting", "completed"]
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            assert summary_payload["scenario_bundle_manifest"]
            assert summary_payload["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
            assert summary_payload["execution_mode"] == "diagnostic"
            assert summary_payload["official_gate_valid"] is False
            assert bridge.DISABLE_REAL_JULIA_PROBE_ENV in log_path.read_text(encoding="utf-8")
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_keeps_official_mode_julia_only(monkeypatch) -> None:
    monkeypatch.setenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, "1")
    official_queue_root = prepare_isolated_tmp_dir("phase3_queue_official_root")
    diagnostic_scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_queue_diagnostic_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    diagnostic_queue_root = prepare_isolated_tmp_dir("phase3_queue_diagnostic_root")
    try:
        official_job = create_run_job(
            "data/decision_platform/maquete_v2",
            queue_root=official_queue_root,
        )
        failed_job = run_next_queued_job(queue_root=official_queue_root)
        diagnostic_job = create_run_job(
            diagnostic_scenario_dir,
            queue_root=diagnostic_queue_root,
            allow_diagnostic_python_emulation=True,
        )
        with diagnostic_runtime_test_mode():
            completed_job = run_next_queued_job(queue_root=diagnostic_queue_root)

        assert official_job["requested_execution_mode"] == "official"
        assert failed_job is not None
        assert failed_job["status"] == "failed"
        assert "invalid for the official Julia-only gate" in str(failed_job["error"])
        assert failed_job["artifacts"]["summary_json"] is None

        assert diagnostic_job["requested_execution_mode"] == "diagnostic"
        assert completed_job is not None
        assert completed_job["status"] == "completed"
        assert completed_job["execution_mode"] == "diagnostic"
        assert completed_job["official_gate_valid"] is False
        assert completed_job["result_summary_path"].endswith("summary.json")
    finally:
        cleanup_scenario_copy(diagnostic_queue_root)
        cleanup_scenario_copy(official_queue_root)
        cleanup_scenario_copy(diagnostic_scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_can_cancel_queued_jobs_without_execution_artifacts() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_cancel_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    queue_root = prepare_isolated_tmp_dir("phase3_queue_cancel_root")
    try:
        with diagnostic_runtime_test_mode():
            canceled_candidate = create_run_job(
                scenario_dir,
                queue_root=queue_root,
                allow_diagnostic_python_emulation=True,
            )
            runnable_candidate = create_run_job(
                scenario_dir,
                queue_root=queue_root,
                allow_diagnostic_python_emulation=True,
            )
            canceled_job = cancel_run_job(canceled_candidate["run_id"], queue_root=queue_root)
            inspection = inspect_run_job(canceled_candidate["run_id"], queue_root=queue_root)
            completed_job = run_next_queued_job(queue_root=queue_root)
            final_summary = summarize_run_jobs(queue_root)

        assert canceled_job["status"] == "canceled"
        assert inspection["status"] == "canceled"
        assert inspection["run_id"] == canceled_candidate["run_id"]
        assert inspection["artifacts"]["summary_json"] is None
        assert inspection["artifacts"]["selected_candidate_json"] is None
        assert inspection["events"][-1]["status"] == "canceled"
        assert "canceled before execution" in inspection["events"][-1]["message"]
        assert Path(inspection["artifacts_dir"]).exists() is False
        assert completed_job is not None
        assert completed_job["run_id"] == runnable_candidate["run_id"]
        assert completed_job["status"] == "completed"
        assert final_summary["status_counts"]["canceled"] == 1
        assert final_summary["status_counts"]["completed"] == 1
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_can_rerun_terminal_runs_with_new_run_id(monkeypatch) -> None:
    monkeypatch.setenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, "1")
    official_queue_root = prepare_isolated_tmp_dir("phase3_queue_rerun_official_root")
    diagnostic_scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_rerun_diagnostic_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    diagnostic_queue_root = prepare_isolated_tmp_dir("phase3_queue_rerun_diagnostic_root")
    try:
        official_job = create_run_job(
            "data/decision_platform/maquete_v2",
            queue_root=official_queue_root,
        )
        failed_job = run_next_queued_job(queue_root=official_queue_root)
        failed_rerun_job = rerun_run_job(official_job["run_id"], queue_root=official_queue_root)
        failed_rerun_result = run_next_queued_job(queue_root=official_queue_root)

        diagnostic_job = create_run_job(
            diagnostic_scenario_dir,
            queue_root=diagnostic_queue_root,
            allow_diagnostic_python_emulation=True,
        )
        with diagnostic_runtime_test_mode():
            completed_job = run_next_queued_job(queue_root=diagnostic_queue_root)
            completed_rerun_job = rerun_run_job(diagnostic_job["run_id"], queue_root=diagnostic_queue_root)
            completed_rerun_result = run_next_queued_job(queue_root=diagnostic_queue_root)

        failed_rerun_inspection = inspect_run_job(failed_rerun_job["run_id"], queue_root=official_queue_root)
        completed_rerun_inspection = inspect_run_job(completed_rerun_job["run_id"], queue_root=diagnostic_queue_root)

        assert failed_job is not None
        assert failed_job["status"] == "failed"
        assert failed_rerun_job["run_id"] != official_job["run_id"]
        assert failed_rerun_job["rerun_of_run_id"] == official_job["run_id"]
        assert failed_rerun_job["rerun_source"]["source_status"] == "failed"
        assert failed_rerun_job["source_bundle_version"] == official_job["source_bundle_version"]
        assert failed_rerun_result is not None
        assert failed_rerun_result["status"] == "failed"
        assert "invalid for the official Julia-only gate" in str(failed_rerun_result["error"])
        assert failed_rerun_inspection["events"][0]["status"] == "queued"
        assert failed_rerun_inspection["rerun_source"]["source_run_id"] == official_job["run_id"]

        assert completed_job is not None
        assert completed_job["status"] == "completed"
        assert completed_rerun_job["run_id"] != diagnostic_job["run_id"]
        assert completed_rerun_job["rerun_of_run_id"] == diagnostic_job["run_id"]
        assert completed_rerun_job["rerun_source"]["source_status"] == "completed"
        assert completed_rerun_result is not None
        assert completed_rerun_result["status"] == "completed"
        assert completed_rerun_result["execution_mode"] == "diagnostic"
        assert completed_rerun_inspection["rerun_source"]["source_run_id"] == diagnostic_job["run_id"]
        assert completed_rerun_inspection["artifacts"]["summary_json"] is not None
    finally:
        cleanup_scenario_copy(diagnostic_queue_root)
        cleanup_scenario_copy(official_queue_root)
        cleanup_scenario_copy(diagnostic_scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_app_exposes_run_inspection() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    layout_repr = repr(app.layout)
    assert "run-jobs-refresh-button" in layout_repr
    assert "run-jobs-summary" in layout_repr
    assert "run-job-selected-id" in layout_repr
    assert "run-job-detail" in layout_repr
    assert "run-job-cancel-button" in layout_repr
    assert "run-job-rerun-button" in layout_repr
