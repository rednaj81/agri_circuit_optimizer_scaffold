from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from decision_platform.api.run_pipeline import (
    cancel_run_job,
    create_run_job,
    inspect_run_job,
    load_run_job,
    list_run_jobs,
    rerun_run_job,
    run_next_queued_job,
    summarize_run_jobs,
)
from decision_platform.julia_bridge import bridge
from decision_platform.ui_dash.app import (
    build_app,
    build_run_job_detail_summary,
    build_run_jobs_snapshot,
    render_run_job_detail_panel,
    render_run_jobs_overview_panel,
    render_runs_workspace_panel,
)
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


def _get_callback(app: object, *, input_id: str, output_prefix: str | None = None) -> Callable[..., Any]:
    callback_map = getattr(app, "callback_map", {})
    for callback_key, metadata in callback_map.items():
        if output_prefix is not None and not str(callback_key).startswith(output_prefix):
            continue
        if any(item["id"] == input_id for item in metadata.get("inputs", [])):
            callback = metadata.get("callback")
            if callback is not None:
                return getattr(callback, "__wrapped__", callback)
    raise KeyError(f"Callback not found for input_id={input_id!r} output_prefix={output_prefix!r}")


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


def _assert_run_evidence(detail: dict[str, Any], *, expected_status: str) -> dict[str, Any]:
    evidence = detail.get("evidence")
    assert isinstance(evidence, dict)
    selected_run_id = detail["selected_run_id"] if "selected_run_id" in detail else detail["run_id"]
    assert evidence["run_id"] == selected_run_id
    assert evidence["run_dir_exists"] is True
    assert evidence["run_dir_isolated"] is True
    assert evidence["log_exists"] is True
    assert evidence["final_status_logged"] is True
    assert evidence["final_status_recorded"] is True
    assert evidence["event_statuses"][-1] == expected_status
    return evidence


def _assert_persisted_queue_summary(
    job: dict[str, Any],
    *,
    expected_status: str,
    source_run_id: str | None = None,
) -> dict[str, Any]:
    queue_summary = job.get("queue_summary")
    assert isinstance(queue_summary, dict)
    assert queue_summary["source"] == "persisted_queue_summary"
    assert queue_summary["refresh_path"] == "canonical_persist_run_job"
    assert queue_summary["status"] == expected_status
    assert queue_summary["lineage"]["source_run_id"] == source_run_id
    assert queue_summary["evidence_summary"]["final_status_recorded"] is True
    return queue_summary


@pytest.mark.fast
def test_phase3_queue_acceptance_runs_ui_surfaces_operational_queue_and_detail_language() -> None:
    workspace = render_runs_workspace_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 3,
            "next_queued_run_id": "run-003",
            "active_run_ids": ["run-002"],
            "queued_run_ids": ["run-003"],
            "latest_run_id": "run-001",
            "status_counts": {"completed": 1, "failed": 1},
        },
        {},
    )
    overview = render_run_jobs_overview_panel(
        {
            "run_count": 3,
            "queue_state": "running",
            "next_queued_run_id": "run-003",
            "active_run_ids": ["run-002"],
            "queued_run_ids": ["run-003"],
            "latest_run_id": "run-001",
            "latest_updated_at": "2026-04-09T00:00:00Z",
            "terminal_run_ids": ["run-001"],
            "status_counts": {"completed": 1, "failed": 1},
            "worker_mode": "serial",
        }
    )
    detail = render_run_job_detail_panel(
        {
            "selected_run_id": "run-002",
            "status": "running",
            "requested_execution_mode": "diagnostic",
            "official_gate_valid": False,
            "duration_s": 9.4,
            "policy_mode": "diagnostic_override_probe_disabled",
            "source_bundle_root": "data/decision_platform/maquete_v2",
            "engine_used": "python_emulated_julia",
            "events": [
                {"status": "queued", "message": "Run criada."},
                {"status": "running", "message": "Execução principal em andamento."},
            ],
            "artifacts": {
                "artifacts_dir": "artifacts/run-002",
            },
            "events_path": "events.jsonl",
            "log_path": "run.log",
        }
    )

    workspace_text = _collect_text(workspace)
    overview_text = _collect_text(overview)
    detail_text = _collect_text(detail)

    assert "Gate do cenário e limites desta leitura" in workspace_text
    assert "Limitação agora" in workspace_text
    assert "O cenário já passou no gate principal" in workspace_text
    assert "Resultado útil" in workspace_text
    assert "Na fila" in overview_text
    assert "Executando" in overview_text
    assert "Resultado recente" in overview_text
    assert "Próxima ação recomendada" in overview_text
    assert "Eventos relevantes" in detail_text
    assert "Resultado e artefatos" in detail_text
    assert "Pode agir agora" in detail_text
    assert "Contexto técnico secundário desta run" in detail_text


@pytest.mark.fast
def test_phase3_queue_acceptance_run_actions_follow_selected_run_state() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="run-job-detail", output_prefix="run-jobs-run-next-button.children")

    queued_result = callback(
        [{"node_id": "W"}, {"node_id": "P1"}],
        [{"link_id": "L001", "from_node": "W", "to_node": "P1"}],
        [{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}],
        json.dumps({"next_queued_run_id": "run-002", "active_run_ids": [], "queued_run_ids": ["run-002"]}, ensure_ascii=False),
        json.dumps({"selected_run_id": "run-002", "status": "queued"}, ensure_ascii=False),
    )
    running_result = callback(
        [{"node_id": "W"}, {"node_id": "P1"}],
        [{"link_id": "L001", "from_node": "W", "to_node": "P1"}],
        [{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}],
        json.dumps({"next_queued_run_id": None, "active_run_ids": ["run-002"], "queued_run_ids": []}, ensure_ascii=False),
        json.dumps({"selected_run_id": "run-002", "status": "running"}, ensure_ascii=False),
    )
    completed_result = callback(
        [{"node_id": "W"}, {"node_id": "P1"}],
        [{"link_id": "L001", "from_node": "W", "to_node": "P1"}],
        [{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}],
        json.dumps({"next_queued_run_id": None, "active_run_ids": [], "queued_run_ids": []}, ensure_ascii=False),
        json.dumps({"selected_run_id": "run-002", "status": "completed"}, ensure_ascii=False),
    )

    assert queued_result == (
        "Executar próxima run (run-002)",
        False,
        "Cancelar esta run",
        False,
        "Reexecução indisponível neste estado",
        True,
    )
    assert running_result == (
        "Aguardar execução atual",
        True,
        "Cancelar esta run",
        False,
        "Reexecução indisponível neste estado",
        True,
    )
    assert completed_result == (
        "Sem próxima run na fila",
        True,
        "Cancelamento indisponível neste estado",
        True,
        "Reexecutar esta run",
        False,
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
        assert _assert_persisted_queue_summary(first_job, expected_status="queued")["evidence_summary"]["artifact_file_count"] == 0
        assert _assert_persisted_queue_summary(second_job, expected_status="queued")["evidence_summary"]["artifact_file_count"] == 0
        assert first_result is not None
        assert second_result is not None
        assert first_result["run_id"] != second_result["run_id"]
        assert first_result["status"] == "completed"
        assert second_result["status"] == "completed"
        assert _assert_persisted_queue_summary(first_result, expected_status="completed")["evidence_summary"]["has_summary_json"] is True
        assert _assert_persisted_queue_summary(second_result, expected_status="completed")["evidence_summary"]["has_summary_json"] is True
        assert [job["status"] for job in after_first].count("completed") == 1
        assert [job["status"] for job in after_first].count("queued") == 1
        assert final_summary["worker_mode"] == "serial"
        assert final_summary["status_counts"]["completed"] == 2
        assert final_summary["status_counts"]["queued"] == 0
        assert all(run["lineage"]["is_rerun"] is False for run in final_summary["runs"])
        assert all(run["evidence_summary"]["has_summary_json"] is True for run in final_summary["runs"])
        assert all(run["summary_source"] == "persisted_queue_summary" for run in final_summary["runs"])

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
            completed_evidence = _assert_run_evidence(completed_detail, expected_status="completed")
            assert completed_evidence["artifact_expectation"] == "summary_artifacts_expected"
            assert completed_evidence["artifacts_dir_exists"] is True
            assert completed_evidence["artifact_file_count"] > 0
            assert completed_evidence["has_summary_json"] is True
            assert completed_evidence["has_catalog_csv"] is True
            assert completed_evidence["has_selected_candidate_json"] is True
            assert completed_evidence["log_statuses"] == ["queued", "preparing", "running", "exporting", "completed"]

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
        assert _assert_persisted_queue_summary(official_job, expected_status="queued")["evidence_summary"]["artifact_file_count"] == 0
        assert failed_job is not None
        assert failed_job["status"] == "failed"
        assert _assert_persisted_queue_summary(failed_job, expected_status="failed")["evidence_summary"]["has_summary_json"] is False
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
        failed_evidence = _assert_run_evidence(failed_detail, expected_status="failed")
        assert failed_evidence["artifact_expectation"] == "execution_log_expected"
        assert failed_evidence["artifacts_dir_exists"] is True
        assert failed_evidence["has_summary_json"] is False
        assert failed_evidence["artifact_file_count"] == 0
        assert failed_evidence["log_statuses"][-1] == "failed"

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
        assert _assert_persisted_queue_summary(canceled_job, expected_status="canceled")["evidence_summary"]["artifact_file_count"] == 0
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
        canceled_evidence = _assert_run_evidence(inspection, expected_status="canceled")
        assert canceled_evidence["artifact_expectation"] == "no_execution_artifacts_expected"
        assert canceled_evidence["artifacts_dir_exists"] is False
        assert canceled_evidence["artifact_file_count"] == 0
        assert canceled_evidence["has_summary_json"] is False
        assert canceled_evidence["log_statuses"] == ["queued", "canceled"]
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
        assert _assert_persisted_queue_summary(failed_rerun_job, expected_status="queued", source_run_id=official_job["run_id"])
        assert failed_rerun_job["source_bundle_version"] == official_job["source_bundle_version"]
        assert failed_rerun_result is not None
        assert failed_rerun_result["status"] == "failed"
        assert _assert_persisted_queue_summary(failed_rerun_result, expected_status="failed", source_run_id=official_job["run_id"])
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
        assert _assert_persisted_queue_summary(completed_rerun_job, expected_status="queued", source_run_id=diagnostic_job["run_id"])
        assert completed_rerun_result is not None
        assert completed_rerun_result["status"] == "completed"
        assert _assert_persisted_queue_summary(completed_rerun_result, expected_status="completed", source_run_id=diagnostic_job["run_id"])
        assert completed_rerun_result["execution_mode"] == "diagnostic"
        assert completed_rerun_inspection["rerun_source"]["source_run_id"] == diagnostic_job["run_id"]
        assert completed_rerun_inspection["artifacts"]["summary_json"] is not None
        _assert_run_detail_has_telemetry(completed_rerun_inspection)
        assert completed_rerun_inspection["engine_used"] == "python_emulated_julia"
        assert completed_rerun_inspection["failure_reason"] is None

        assert canceled_rerun_source["status"] == "canceled"
        assert _assert_persisted_queue_summary(canceled_rerun_source, expected_status="canceled", source_run_id=completed_rerun_job["run_id"])
        assert canceled_rerun_job["run_id"] != canceled_rerun_source["run_id"]
        assert canceled_rerun_job["rerun_of_run_id"] == canceled_rerun_source["run_id"]
        assert canceled_rerun_job["rerun_source"]["source_status"] == "canceled"
        assert _assert_persisted_queue_summary(canceled_rerun_job, expected_status="queued", source_run_id=canceled_rerun_source["run_id"])
        assert canceled_rerun_result is not None
        assert canceled_rerun_result["status"] == "completed"
        assert _assert_persisted_queue_summary(canceled_rerun_result, expected_status="completed", source_run_id=canceled_rerun_source["run_id"])
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
            app = build_app(
                scenario_dir,
                run_queue_root=queue_root,
                bootstrap_pipeline=False,
            )

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
        persisted_canceled_job = load_run_job(canceled_job["run_id"], queue_root=queue_root)
        assert persisted_canceled_job["queue_summary"]["source"] == "persisted_queue_summary"
        assert persisted_canceled_job["queue_summary"]["lineage"]["source_run_id"] == completed_candidate["run_id"]
        assert persisted_canceled_job["queue_summary"]["evidence_summary"]["artifact_file_count"] == 0
        assert reopened_snapshot["selected_run_summary"]["run_id"] == canceled_job["run_id"]
        assert reopened_snapshot["selected_run_summary"]["lineage"]["source_run_id"] == completed_candidate["run_id"]
        assert reopened_snapshot["selected_run_summary"]["lineage"]["source_status"] == "completed"
        assert reopened_snapshot["selected_run_summary"]["evidence_summary"]["artifact_file_count"] == 0
        assert reopened_snapshot["selected_run_summary"]["evidence_summary"]["final_status_logged"] is True
        assert reopened_snapshot["selected_run_summary"]["summary_source"] == "persisted_queue_summary"
        assert reopened_snapshot["selected_run_summary"]["evidence_summary"] == persisted_canceled_job["queue_summary"]["evidence_summary"]
        assert reopened_snapshot["selected_run_detail"]["status"] == "canceled"
        assert reopened_snapshot["selected_run_detail"]["queue_summary"] == persisted_canceled_job["queue_summary"]
        assert reopened_snapshot["selected_run_detail"]["queue_summary"]["refresh_path"] == "canonical_persist_run_job"
        assert reopened_snapshot["selected_run_detail"]["rerun_of_run_id"] == completed_candidate["run_id"]
        assert reopened_snapshot["selected_run_detail"]["source_bundle_reference_path"] == canceled_job["source_bundle_reference_path"]
        assert reopened_snapshot["selected_run_detail"]["source_bundle_reference"]["rerun_source"]["source_run_id"] == completed_candidate["run_id"]
        _assert_run_detail_has_telemetry(reopened_snapshot["selected_run_detail"])
        reopened_canceled_evidence = _assert_run_evidence(reopened_snapshot["selected_run_detail"], expected_status="canceled")
        assert reopened_canceled_evidence["artifact_file_count"] == 0
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
        assert _assert_run_evidence(completed_detail, expected_status="completed")["has_summary_json"] is True
        assert canceled_detail["status"] == "canceled"
        assert canceled_detail["events"][-1]["status"] == "canceled"
        assert canceled_detail["artifacts"]["summary_json"] is None
        assert canceled_detail["source_bundle_reference_path"] == canceled_job["source_bundle_reference_path"]
        assert canceled_detail["source_bundle_reference"]["rerun_source"]["source_run_id"] == completed_candidate["run_id"]
        assert canceled_detail["inspection"]["source_bundle_reference_path"] == canceled_job["source_bundle_reference_path"]
        _assert_run_detail_has_telemetry(canceled_detail)
        assert _assert_run_evidence(canceled_detail, expected_status="canceled")["log_statuses"] == ["queued", "canceled"]
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
            app = build_app(
                scenario_dir,
                run_queue_root=queue_root,
                bootstrap_pipeline=False,
            )

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
            app = build_app(
                scenario_dir,
                run_queue_root=queue_root,
                bootstrap_pipeline=False,
            )

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
        rerun_summary_entry = next(run for run in rerun_summary["runs"] if run["run_id"] == rerun_result[2])
        assert rerun_summary_entry["lineage"]["source_run_id"] == completed_result[2]
        assert rerun_summary_entry["lineage"]["source_status"] == "completed"
        assert rerun_summary_entry["evidence_summary"]["artifact_expectation"] == "no_execution_artifacts_expected"
        assert rerun_summary_entry["evidence_summary"]["artifact_file_count"] == 0
        assert rerun_summary_entry["summary_source"] == "persisted_queue_summary"
        assert rerun_detail["status"] == "queued"
        assert rerun_detail["queue_summary"]["lineage"]["source_run_id"] == completed_result[2]
        assert rerun_detail["queue_summary"]["evidence_summary"] == rerun_summary_entry["evidence_summary"]
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
        app = build_app(
            "data/decision_platform/maquete_v2",
            run_queue_root=queue_root,
            bootstrap_pipeline=False,
        )
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
        app = build_app(
            "data/decision_platform/maquete_v2",
            bootstrap_pipeline=False,
        )

    layout_repr = repr(app.layout)
    assert "run-job-enqueue-button" in layout_repr
    assert "run-jobs-run-next-button" in layout_repr
    assert "run-jobs-refresh-button" in layout_repr
    assert "run-jobs-summary" in layout_repr
    assert "run-job-selected-id" in layout_repr
    assert "run-job-detail" in layout_repr
    assert "run-job-cancel-button" in layout_repr
    assert "run-job-rerun-button" in layout_repr
