from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

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
from decision_platform.ui_dash.app import build_app, build_run_job_detail_summary, build_run_jobs_snapshot
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_maquete_v2_acceptance_scenario,
    prepare_isolated_tmp_dir,
)

RUN_DETAIL_TELEMETRY_FIELDS = (
    "engine_requested",
    "engine_used",
    "engine_mode",
    "julia_available",
    "watermodels_available",
    "real_julia_probe_disabled",
    "execution_mode",
    "official_gate_valid",
    "started_at",
    "finished_at",
    "duration_s",
    "policy_mode",
    "policy_message",
    "failure_reason",
    "failure_stacktrace_excerpt",
)


def _get_callback(app: object, *, input_id: str) -> Callable[..., Any]:
    callback_map = getattr(app, "callback_map", {})
    for metadata in callback_map.values():
        if any(item["id"] == input_id for item in metadata.get("inputs", [])):
            callback = metadata.get("callback")
            if callback is not None:
                return getattr(callback, "__wrapped__", callback)
    raise KeyError(f"Callback not found for input_id={input_id!r}")


def _assert_run_detail_has_telemetry(detail: dict[str, Any]) -> None:
    telemetry = detail.get("telemetry") or {
        field: detail.get(field)
        for field in RUN_DETAIL_TELEMETRY_FIELDS
    }
    for field in RUN_DETAIL_TELEMETRY_FIELDS:
        assert field in detail
        assert field in telemetry
        if "telemetry" in detail:
            assert detail[field] == telemetry[field]


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
            completed_detail = build_run_job_detail_summary(completed_job["run_id"], queue_root=queue_root)

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
            _assert_run_detail_has_telemetry(completed_detail)
            assert completed_detail["engine_requested"] == "watermodels_jl"
            assert completed_detail["engine_used"] == "python_emulated_julia"
            assert completed_detail["engine_mode"] == "fallback_emulated"
            assert completed_detail["julia_available"] is False
            assert completed_detail["watermodels_available"] is False
            assert completed_detail["real_julia_probe_disabled"] is True
            assert completed_detail["execution_mode"] == "diagnostic"
            assert completed_detail["official_gate_valid"] is False
            assert completed_detail["started_at"] is not None
            assert completed_detail["finished_at"] is not None
            assert float(completed_detail["duration_s"]) >= 0.0
            assert completed_detail["policy_mode"] == "diagnostic_override_probe_disabled"
            assert "disabled the real Julia probe" in str(completed_detail["policy_message"])
            assert completed_detail["failure_reason"] is None
            assert completed_detail["failure_stacktrace_excerpt"] is None
            assert completed_detail["inspection"]["queue_root"] == str(queue_root.resolve())

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
        failed_detail = build_run_job_detail_summary(official_job["run_id"], queue_root=official_queue_root)
        diagnostic_job = create_run_job(
            diagnostic_scenario_dir,
            queue_root=diagnostic_queue_root,
            allow_diagnostic_python_emulation=True,
        )
        with diagnostic_runtime_test_mode():
            completed_job = run_next_queued_job(queue_root=diagnostic_queue_root)
        completed_detail = build_run_job_detail_summary(diagnostic_job["run_id"], queue_root=diagnostic_queue_root)

        assert official_job["requested_execution_mode"] == "official"
        assert failed_job is not None
        assert failed_job["status"] == "failed"
        assert "invalid for the official Julia-only gate" in str(failed_job["error"])
        assert failed_job["artifacts"]["summary_json"] is None
        _assert_run_detail_has_telemetry(failed_detail)
        assert failed_detail["engine_requested"] == "watermodels_jl"
        assert failed_detail["engine_used"] is None
        assert failed_detail["engine_mode"] is None
        assert failed_detail["julia_available"] is False
        assert failed_detail["watermodels_available"] is False
        assert failed_detail["real_julia_probe_disabled"] is True
        assert failed_detail["execution_mode"] == "diagnostic"
        assert failed_detail["official_gate_valid"] is False
        assert failed_detail["started_at"] is not None
        assert failed_detail["finished_at"] is not None
        assert float(failed_detail["duration_s"]) >= 0.0
        assert failed_detail["policy_mode"] == "diagnostic_override_probe_disabled"
        assert "official Julia-only gate" in str(failed_detail["policy_message"])
        assert "invalid for the official Julia-only gate" in str(failed_detail["failure_reason"])
        assert "OfficialRuntimeConfigError" in str(failed_detail["failure_stacktrace_excerpt"])

        assert diagnostic_job["requested_execution_mode"] == "diagnostic"
        assert completed_job is not None
        assert completed_job["status"] == "completed"
        assert completed_job["execution_mode"] == "diagnostic"
        assert completed_job["official_gate_valid"] is False
        assert completed_job["result_summary_path"].endswith("summary.json")
        _assert_run_detail_has_telemetry(completed_detail)
        assert completed_detail["engine_used"] == "python_emulated_julia"
        assert completed_detail["policy_mode"] == "diagnostic_override_probe_disabled"
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
        _assert_run_detail_has_telemetry(inspection)
        assert inspection["engine_requested"] == "watermodels_jl"
        assert inspection["engine_used"] is None
        assert inspection["engine_mode"] is None
        assert inspection["julia_available"] is False
        assert inspection["watermodels_available"] is False
        assert inspection["real_julia_probe_disabled"] is True
        assert inspection["execution_mode"] == "diagnostic"
        assert inspection["official_gate_valid"] is False
        assert inspection["started_at"] is None
        assert inspection["finished_at"] is not None
        assert inspection["duration_s"] == 0.0
        assert inspection["policy_mode"] == "diagnostic_override_probe_disabled"
        assert inspection["failure_reason"] is None
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
            canceled_rerun_source = rerun_run_job(completed_rerun_job["run_id"], queue_root=diagnostic_queue_root)
            canceled_rerun_source = cancel_run_job(canceled_rerun_source["run_id"], queue_root=diagnostic_queue_root)
            canceled_rerun_job = rerun_run_job(canceled_rerun_source["run_id"], queue_root=diagnostic_queue_root)
            canceled_rerun_result = run_next_queued_job(queue_root=diagnostic_queue_root)

        failed_rerun_inspection = inspect_run_job(failed_rerun_job["run_id"], queue_root=official_queue_root)
        completed_rerun_inspection = inspect_run_job(completed_rerun_job["run_id"], queue_root=diagnostic_queue_root)
        canceled_rerun_inspection = inspect_run_job(canceled_rerun_job["run_id"], queue_root=diagnostic_queue_root)

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
        _assert_run_detail_has_telemetry(failed_rerun_inspection)
        assert failed_rerun_inspection["failure_reason"] == failed_rerun_result["error"]
        assert failed_rerun_inspection["policy_mode"] == "diagnostic_override_probe_disabled"

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
        _assert_run_detail_has_telemetry(completed_rerun_inspection)
        assert completed_rerun_inspection["engine_used"] == "python_emulated_julia"
        assert completed_rerun_inspection["failure_reason"] is None

        assert canceled_rerun_source["status"] == "canceled"
        assert canceled_rerun_job["run_id"] != canceled_rerun_source["run_id"]
        assert canceled_rerun_job["rerun_of_run_id"] == canceled_rerun_source["run_id"]
        assert canceled_rerun_job["rerun_source"]["source_status"] == "canceled"
        assert canceled_rerun_result is not None
        assert canceled_rerun_result["status"] == "completed"
        assert canceled_rerun_result["execution_mode"] == "diagnostic"
        assert canceled_rerun_inspection["source_bundle_reference"]["run_id"] == canceled_rerun_job["run_id"]
        assert canceled_rerun_inspection["source_bundle_reference"]["rerun_source"]["source_run_id"] == canceled_rerun_source["run_id"]
        assert canceled_rerun_inspection["source_bundle_reference"]["scenario_provenance"]["bundle_manifest"]
        _assert_run_detail_has_telemetry(canceled_rerun_inspection)
        assert canceled_rerun_inspection["engine_used"] == "python_emulated_julia"
        assert canceled_rerun_inspection["failure_reason"] is None
    finally:
        cleanup_scenario_copy(diagnostic_queue_root)
        cleanup_scenario_copy(official_queue_root)
        cleanup_scenario_copy(diagnostic_scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_reopens_persisted_run_state_for_inspection() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_reopen_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    queue_root = prepare_isolated_tmp_dir("phase3_queue_reopen_root")
    try:
        with diagnostic_runtime_test_mode():
            completed_candidate = create_run_job(
                scenario_dir,
                queue_root=queue_root,
                allow_diagnostic_python_emulation=True,
            )
            completed_job = run_next_queued_job(queue_root=queue_root)
            rerun_candidate = rerun_run_job(completed_candidate["run_id"], queue_root=queue_root)
            canceled_job = cancel_run_job(rerun_candidate["run_id"], queue_root=queue_root)

        reopened_snapshot = build_run_jobs_snapshot(queue_root, preferred_run_id=canceled_job["run_id"])
        completed_detail = build_run_job_detail_summary(completed_job["run_id"], queue_root=queue_root)
        canceled_detail = build_run_job_detail_summary(canceled_job["run_id"], queue_root=queue_root)
        with diagnostic_runtime_test_mode():
            app = build_app(scenario_dir, run_queue_root=queue_root)

        layout_repr = repr(app.layout)
        queue_root_str = str(queue_root.resolve())
        queue_root_store = next(
            child for child in app.layout.children if getattr(child, "id", None) == "run-queue-root"
        )

        assert completed_job is not None
        assert completed_job["status"] == "completed"
        assert reopened_snapshot["summary"]["queue_root"] == queue_root_str
        assert reopened_snapshot["summary"]["status_counts"]["completed"] == 1
        assert reopened_snapshot["summary"]["status_counts"]["canceled"] == 1
        assert reopened_snapshot["selected_run_id"] == canceled_job["run_id"]
        assert reopened_snapshot["selected_run_detail"]["status"] == "canceled"
        assert reopened_snapshot["selected_run_detail"]["rerun_of_run_id"] == completed_candidate["run_id"]
        assert reopened_snapshot["selected_run_detail"]["source_bundle_reference_path"] == canceled_job["source_bundle_reference_path"]
        assert reopened_snapshot["selected_run_detail"]["source_bundle_reference"]["rerun_source"]["source_run_id"] == completed_candidate["run_id"]
        _assert_run_detail_has_telemetry(reopened_snapshot["selected_run_detail"])
        assert reopened_snapshot["summary"]["queue_state"] == "idle"
        assert reopened_snapshot["summary"]["queued_run_ids"] == []
        assert reopened_snapshot["summary"]["terminal_run_ids"] == [
            completed_job["run_id"],
            canceled_job["run_id"],
        ]
        assert completed_detail["status"] == "completed"
        assert completed_detail["artifacts"]["summary_json"] is not None
        assert completed_detail["events"][-1]["status"] == "completed"
        _assert_run_detail_has_telemetry(completed_detail)
        assert canceled_detail["status"] == "canceled"
        assert canceled_detail["events"][-1]["status"] == "canceled"
        assert canceled_detail["artifacts"]["summary_json"] is None
        assert canceled_detail["source_bundle_reference_path"] == canceled_job["source_bundle_reference_path"]
        assert canceled_detail["source_bundle_reference"]["rerun_source"]["source_run_id"] == completed_candidate["run_id"]
        assert canceled_detail["inspection"]["source_bundle_reference_path"] == canceled_job["source_bundle_reference_path"]
        _assert_run_detail_has_telemetry(canceled_detail)
        assert "run-queue-root" in layout_repr
        assert queue_root_store.data == queue_root_str
        assert canceled_job["run_id"] in layout_repr
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_app_can_enqueue_and_run_next_via_callbacks() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_ui_enqueue_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    queue_root = prepare_isolated_tmp_dir("phase3_queue_ui_enqueue_root")
    try:
        with diagnostic_runtime_test_mode():
            app = build_app(scenario_dir, run_queue_root=queue_root)

        enqueue_callback = _get_callback(app, input_id="run-job-enqueue-button")
        run_next_callback = _get_callback(app, input_id="run-jobs-run-next-button")

        enqueue_result = enqueue_callback(1, str(Path(scenario_dir).resolve()), str(queue_root.resolve()))
        queued_summary = json.loads(enqueue_result[0])
        queued_detail = json.loads(enqueue_result[3])

        assert queued_summary["status_counts"]["queued"] == 1
        assert queued_summary["queue_state"] == "queued"
        assert queued_summary["next_queued_run_id"] == enqueue_result[2]
        assert queued_detail["status"] == "queued"
        assert queued_detail["requested_execution_mode"] == "diagnostic"
        _assert_run_detail_has_telemetry(queued_detail)
        assert queued_detail["engine_requested"] == "watermodels_jl"
        assert queued_detail["policy_mode"] == "diagnostic_opt_in"
        assert "enfileirada em modo diagnostic" in enqueue_result[4]

        with diagnostic_runtime_test_mode():
            run_next_result = run_next_callback(1, enqueue_result[2], str(queue_root.resolve()))

        completed_summary = json.loads(run_next_result[0])
        completed_detail = json.loads(run_next_result[3])

        assert completed_summary["status_counts"]["queued"] == 0
        assert completed_summary["status_counts"]["completed"] == 1
        assert completed_detail["status"] == "completed"
        assert completed_detail["execution_mode"] == "diagnostic"
        assert completed_detail["artifacts"]["summary_json"] is not None
        _assert_run_detail_has_telemetry(completed_detail)
        assert completed_detail["engine_used"] == "python_emulated_julia"
        assert "-> completed" in run_next_result[4]
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_app_can_cancel_and_rerun_via_callbacks() -> None:
    scenario_dir = prepare_maquete_v2_acceptance_scenario(
        "maquete_v2_phase3_ui_cancel_rerun_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    queue_root = prepare_isolated_tmp_dir("phase3_queue_ui_cancel_rerun_root")
    try:
        with diagnostic_runtime_test_mode():
            app = build_app(scenario_dir, run_queue_root=queue_root)

        enqueue_callback = _get_callback(app, input_id="run-job-enqueue-button")
        cancel_callback = _get_callback(app, input_id="run-job-cancel-button")
        run_next_callback = _get_callback(app, input_id="run-jobs-run-next-button")
        rerun_callback = _get_callback(app, input_id="run-job-rerun-button")

        first_enqueue = enqueue_callback(1, str(Path(scenario_dir).resolve()), str(queue_root.resolve()))
        canceled_result = cancel_callback(1, first_enqueue[2], str(queue_root.resolve()))
        canceled_summary = json.loads(canceled_result[0])
        canceled_detail = json.loads(canceled_result[3])

        assert canceled_summary["status_counts"]["canceled"] == 1
        assert canceled_detail["status"] == "canceled"
        assert canceled_detail["artifacts"]["summary_json"] is None
        _assert_run_detail_has_telemetry(canceled_detail)
        assert "-> canceled" in canceled_result[4]

        rerun_canceled_result = rerun_callback(1, canceled_result[2], str(queue_root.resolve()))
        rerun_canceled_summary = json.loads(rerun_canceled_result[0])
        rerun_canceled_detail = json.loads(rerun_canceled_result[3])

        assert rerun_canceled_summary["status_counts"]["queued"] == 1
        assert rerun_canceled_summary["status_counts"]["canceled"] == 1
        assert rerun_canceled_detail["status"] == "queued"
        assert rerun_canceled_detail["rerun_of_run_id"] == canceled_result[2]
        assert rerun_canceled_detail["source_bundle_reference"]["rerun_source"]["source_status"] == "canceled"
        _assert_run_detail_has_telemetry(rerun_canceled_detail)
        assert "re-run de" in rerun_canceled_result[4]

        second_enqueue = enqueue_callback(2, str(Path(scenario_dir).resolve()), str(queue_root.resolve()))
        with diagnostic_runtime_test_mode():
            completed_rerun_from_canceled = run_next_callback(1, rerun_canceled_result[2], str(queue_root.resolve()))
            completed_result = run_next_callback(2, second_enqueue[2], str(queue_root.resolve()))
        rerun_result = rerun_callback(1, completed_result[2], str(queue_root.resolve()))
        rerun_summary = json.loads(rerun_result[0])
        rerun_detail = json.loads(rerun_result[3])

        assert rerun_summary["status_counts"]["queued"] == 1
        assert rerun_summary["status_counts"]["completed"] == 2
        assert rerun_summary["status_counts"]["canceled"] == 1
        assert json.loads(completed_rerun_from_canceled[3])["rerun_of_run_id"] == canceled_result[2]
        assert rerun_detail["status"] == "queued"
        assert rerun_detail["rerun_of_run_id"] == completed_result[2]
        assert rerun_detail["rerun_source"]["source_run_id"] == completed_result[2]
        _assert_run_detail_has_telemetry(rerun_detail)
        assert "re-run de" in rerun_result[4]
    finally:
        cleanup_scenario_copy(queue_root)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_phase3_queue_acceptance_app_run_next_keeps_official_mode_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv(bridge.DISABLE_REAL_JULIA_PROBE_ENV, "1")
    queue_root = prepare_isolated_tmp_dir("phase3_queue_ui_official_root")
    try:
        app = build_app("data/decision_platform/maquete_v2", run_queue_root=queue_root)
        enqueue_callback = _get_callback(app, input_id="run-job-enqueue-button")
        run_next_callback = _get_callback(app, input_id="run-jobs-run-next-button")

        enqueue_result = enqueue_callback(1, str(Path("data/decision_platform/maquete_v2").resolve()), str(queue_root.resolve()))
        failed_result = run_next_callback(1, enqueue_result[2], str(queue_root.resolve()))
        failed_summary = json.loads(failed_result[0])
        failed_detail = json.loads(failed_result[3])

        assert failed_summary["status_counts"]["failed"] == 1
        assert failed_detail["status"] == "failed"
        assert failed_detail["requested_execution_mode"] == "official"
        _assert_run_detail_has_telemetry(failed_detail)
        assert failed_detail["failure_reason"] == failed_detail["error"]
        assert failed_detail["policy_mode"] == "diagnostic_override_probe_disabled"
        assert "invalid for the official Julia-only gate" in str(failed_detail["error"])
        assert "-> failed" in failed_result[4]
    finally:
        cleanup_scenario_copy(queue_root)


@pytest.mark.fast
def test_phase3_queue_acceptance_app_exposes_run_inspection() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    layout_repr = repr(app.layout)
    assert "run-job-enqueue-button" in layout_repr
    assert "run-jobs-run-next-button" in layout_repr
    assert "run-jobs-refresh-button" in layout_repr
    assert "run-jobs-summary" in layout_repr
    assert "run-job-selected-id" in layout_repr
    assert "run-job-detail" in layout_repr
    assert "run-job-cancel-button" in layout_repr
    assert "run-job-rerun-button" in layout_repr
