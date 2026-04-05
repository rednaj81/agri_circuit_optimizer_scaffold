from __future__ import annotations

import argparse
import json
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_platform.audit import build_engine_comparison_suite
from decision_platform.catalog.pipeline import build_solution_catalog, export_catalog
from decision_platform.data_io.loader import BUNDLE_MANIFEST_FILENAME, SCENARIO_BUNDLE_VERSION, ScenarioBundle, load_scenario_bundle
from decision_platform.julia_bridge.bridge import (
    DISABLE_REAL_JULIA_PROBE_ENV,
    real_julia_probe_disabled,
)


class OfficialRuntimeConfigError(RuntimeError):
    pass


DEFAULT_RUN_QUEUE_ROOT = Path("data/output/decision_platform/run_jobs")
RUN_JOB_STATUSES = (
    "queued",
    "preparing",
    "running",
    "exporting",
    "completed",
    "failed",
    "canceled",
)
ACTIVE_RUN_JOB_STATUSES = {"preparing", "running", "exporting"}
TERMINAL_RUN_JOB_STATUSES = {"completed", "failed", "canceled"}
RUN_JOB_TELEMETRY_FIELDS = (
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


def run_decision_pipeline(
    scenario_dir: str | Path,
    output_dir: str | Path | None = None,
    *,
    include_engine_comparison: bool | None = None,
    allow_diagnostic_python_emulation: bool = False,
) -> dict[str, Any]:
    normalized_scenario_dir = _normalize_path(scenario_dir)
    normalized_output_dir = _normalize_path(output_dir) if output_dir is not None else None
    started_at = datetime.now(UTC)
    try:
        bundle = _require_canonical_scenario_bundle(
            load_scenario_bundle(normalized_scenario_dir),
            consumer="Official decision_platform pipeline",
        )
    except (ValueError, FileNotFoundError) as exc:
        raise OfficialRuntimeConfigError(str(exc)) from exc
    should_build_engine_comparison = False if include_engine_comparison is None else include_engine_comparison
    _validate_runtime_policy(
        bundle,
        allow_diagnostic_python_emulation=allow_diagnostic_python_emulation,
        include_engine_comparison=should_build_engine_comparison,
    )
    scenario_provenance = _build_scenario_provenance(
        bundle,
        requested_scenario_dir=normalized_scenario_dir,
        output_dir=normalized_output_dir,
    )
    runtime_policy = _build_runtime_policy(
        allow_diagnostic_python_emulation=allow_diagnostic_python_emulation,
        include_engine_comparison=should_build_engine_comparison,
    )
    result = build_solution_catalog(bundle)
    result["scenario_bundle_root"] = scenario_provenance["scenario_root"]
    result["scenario_provenance"] = scenario_provenance
    result["runtime_policy"] = runtime_policy
    if should_build_engine_comparison:
        result["engine_comparison"] = build_engine_comparison_suite(bundle, julia_result=result)
        result["engine_comparison"]["execution_policy"] = runtime_policy
    result["runtime"] = _build_runtime_metadata(
        started_at=started_at,
        runtime_policy=runtime_policy,
        scenario_provenance=scenario_provenance,
    )
    if "engine_comparison" in result:
        result["engine_comparison"]["runtime"] = result["runtime"]
    if normalized_output_dir is not None:
        export_catalog(result, normalized_output_dir)
    return result


def create_run_job(
    scenario_dir: str | Path,
    *,
    queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT,
    include_engine_comparison: bool = False,
    allow_diagnostic_python_emulation: bool = False,
    rerun_source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_scenario_dir = _normalize_path(scenario_dir)
    normalized_queue_root = _normalize_path(queue_root)
    created_at = _utc_now_iso()
    bundle = _require_canonical_scenario_bundle(
        load_scenario_bundle(normalized_scenario_dir),
        consumer="decision_platform serial run queue",
    )
    run_id = _build_run_id()
    run_dir = normalized_queue_root / run_id
    artifacts_dir = run_dir / "artifacts"
    job_path = run_dir / "job.json"
    events_path = run_dir / "events.jsonl"
    log_path = run_dir / "run.log"
    bundle_reference_path = run_dir / "source_bundle_reference.json"
    run_dir.mkdir(parents=True, exist_ok=False)
    scenario_provenance = _build_scenario_provenance(
        bundle,
        requested_scenario_dir=normalized_scenario_dir,
        output_dir=artifacts_dir,
    )
    runtime_policy = _build_runtime_policy(
        allow_diagnostic_python_emulation=allow_diagnostic_python_emulation,
        include_engine_comparison=bool(include_engine_comparison),
    )
    initial_telemetry = _build_initial_run_job_telemetry(bundle, runtime_policy=runtime_policy)
    bundle_reference = {
        "run_id": run_id,
        "scenario_provenance": scenario_provenance,
    }
    if rerun_source is not None:
        bundle_reference["rerun_source"] = rerun_source
    bundle_reference_path.write_text(json.dumps(bundle_reference, indent=2, ensure_ascii=False), encoding="utf-8")
    job = {
        "run_id": run_id,
        "status": "queued",
        "created_at": created_at,
        "updated_at": created_at,
        "started_at": None,
        "finished_at": None,
        "requested_execution_mode": "diagnostic" if allow_diagnostic_python_emulation else "official",
        "allow_diagnostic_python_emulation": bool(allow_diagnostic_python_emulation),
        "include_engine_comparison": bool(include_engine_comparison),
        "queue_root": str(normalized_queue_root),
        "run_dir": str(run_dir),
        "artifacts_dir": str(artifacts_dir),
        "job_path": str(job_path),
        "events_path": str(events_path),
        "log_path": str(log_path),
        "source_bundle_reference_path": str(bundle_reference_path),
        "source_bundle_root": scenario_provenance["scenario_root"],
        "source_bundle_version": scenario_provenance["bundle_version"],
        "source_bundle_manifest": scenario_provenance["bundle_manifest"],
        "source_bundle_files": scenario_provenance["bundle_files"],
        "scenario_provenance": scenario_provenance,
        "rerun_of_run_id": str(rerun_source.get("source_run_id")) if rerun_source is not None else None,
        "rerun_source": rerun_source,
        "artifacts": {},
        "error": None,
        "runtime": None,
        "runtime_policy": runtime_policy,
        "worker_mode": "serial",
        "queue_summary": None,
        **initial_telemetry,
    }
    _write_json(job_path, job)
    _append_run_event(job, status="queued", message="Run job queued.")
    _append_run_log(job, "queued: run job queued and awaiting serial worker.")
    return _refresh_persisted_run_job_summary(_read_run_job(job_path))


def load_run_job(run_id: str, *, queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    normalized_queue_root = _normalize_path(queue_root)
    return _read_run_job(normalized_queue_root / run_id / "job.json")


def list_run_jobs(queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> list[dict[str, Any]]:
    normalized_queue_root = _normalize_path(queue_root)
    if not normalized_queue_root.exists():
        return []
    jobs: list[dict[str, Any]] = []
    for job_path in sorted(normalized_queue_root.glob("*/job.json")):
        jobs.append(_read_run_job(job_path))
    return sorted(jobs, key=lambda item: (str(item.get("created_at", "")), str(item.get("run_id", ""))))


def summarize_run_jobs(queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    jobs = list_run_jobs(queue_root)
    counts = {status: 0 for status in RUN_JOB_STATUSES}
    for job in jobs:
        status = str(job.get("status", "")).strip()
        if status in counts:
            counts[status] += 1
    latest_job = jobs[-1] if jobs else None
    active_run_ids = [job["run_id"] for job in jobs if job["status"] in ACTIVE_RUN_JOB_STATUSES]
    queued_run_ids = [job["run_id"] for job in jobs if job["status"] == "queued"]
    terminal_run_ids = [job["run_id"] for job in jobs if job["status"] in TERMINAL_RUN_JOB_STATUSES]
    return {
        "queue_root": str(_normalize_path(queue_root)),
        "worker_mode": "serial",
        "run_count": len(jobs),
        "status_counts": counts,
        "queue_state": "active" if active_run_ids else ("queued" if queued_run_ids else "idle"),
        "active_run_ids": active_run_ids,
        "queued_run_ids": queued_run_ids,
        "terminal_run_ids": terminal_run_ids,
        "next_queued_run_id": queued_run_ids[0] if queued_run_ids else None,
        "latest_run_id": latest_job["run_id"] if latest_job is not None else None,
        "latest_updated_at": latest_job.get("updated_at") if latest_job is not None else None,
        "runs": [
            {
                "run_id": job["run_id"],
                "status": job["status"],
                "requested_execution_mode": job["requested_execution_mode"],
                "execution_mode": job.get("execution_mode"),
                "official_gate_valid": job.get("official_gate_valid"),
                "policy_mode": job.get("policy_mode"),
                "started_at": job.get("started_at"),
                "finished_at": job.get("finished_at"),
                "duration_s": job.get("duration_s"),
                "source_bundle_root": job["source_bundle_root"],
                "artifacts_dir": job["artifacts_dir"],
                "rerun_of_run_id": job.get("rerun_of_run_id"),
                "lineage": dict((job.get("queue_summary") or {}).get("lineage") or _build_run_job_lineage_summary(job)),
                "evidence_summary": dict((job.get("queue_summary") or {}).get("evidence_summary") or _build_run_job_evidence_summary(job)),
                "summary_source": str((job.get("queue_summary") or {}).get("source") or "derived_on_read"),
                "error": job.get("error"),
                "failure_reason": job.get("failure_reason"),
            }
            for job in jobs
        ],
    }


def inspect_run_job(run_id: str, *, queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    job = load_run_job(run_id, queue_root=queue_root)
    return _build_run_job_detail(job)


def cancel_run_job(run_id: str, *, queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    job = load_run_job(run_id, queue_root=queue_root)
    if job["status"] in TERMINAL_RUN_JOB_STATUSES:
        return job
    if job["status"] != "queued":
        raise RuntimeError("Only queued run_job entries can be canceled in the serial phase_3 worker.")
    return _transition_run_job(
        job,
        status="canceled",
        message="Run job canceled before execution.",
        artifacts=_build_run_artifact_manifest(Path(job["artifacts_dir"])),
    )


def rerun_run_job(run_id: str, *, queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    source_job = load_run_job(run_id, queue_root=queue_root)
    if source_job["status"] not in TERMINAL_RUN_JOB_STATUSES:
        raise RuntimeError(
            "Only terminal run_job entries can be re-run explicitly in the serial phase_3 worker."
        )
    rerun_source = _build_rerun_source(source_job)
    return create_run_job(
        source_job["source_bundle_root"],
        queue_root=queue_root,
        include_engine_comparison=bool(source_job.get("include_engine_comparison")),
        allow_diagnostic_python_emulation=bool(source_job.get("allow_diagnostic_python_emulation")),
        rerun_source=rerun_source,
    )


def execute_run_job(run_id: str, *, queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    job = load_run_job(run_id, queue_root=queue_root)
    if job["status"] == "canceled":
        return job
    if job["status"] != "queued":
        raise RuntimeError("Serial worker can execute only queued run_job entries.")
    artifacts_dir = Path(job["artifacts_dir"])
    try:
        job = _transition_run_job(job, status="preparing", message="Preparing isolated run directory and artifact root.")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        job = _transition_run_job(job, status="running", message="Running decision_platform pipeline for queued run.")
        result = run_decision_pipeline(
            job["source_bundle_root"],
            artifacts_dir,
            include_engine_comparison=bool(job["include_engine_comparison"]),
            allow_diagnostic_python_emulation=bool(job["allow_diagnostic_python_emulation"]),
        )
        job = _transition_run_job(job, status="exporting", message="Exporting queued run artifacts and summary.")
        _append_run_log(job, f"runtime_policy: {result.get('runtime_policy', {}).get('policy_message', '')}")
        artifacts = _build_run_artifact_manifest(artifacts_dir)
        runtime = result.get("runtime", {})
        runtime_policy = result.get("runtime_policy", {})
        summary_payload = _read_json_if_exists(Path(artifacts.get("summary_json"))) if artifacts.get("summary_json") else {}
        return _transition_run_job(
            job,
            status="completed",
            message="Run job completed successfully.",
            runtime=runtime,
            runtime_policy=runtime_policy,
            error=None,
            artifacts=artifacts,
            selected_candidate_id=result.get("selected_candidate_id"),
            scenario_provenance=result.get("scenario_provenance"),
            result_summary_path=str(artifacts_dir / "summary.json"),
            **_build_run_job_telemetry_updates(
                job,
                runtime=runtime,
                runtime_policy=runtime_policy,
                summary_payload=summary_payload,
            ),
        )
    except Exception as exc:
        artifacts = _build_run_artifact_manifest(artifacts_dir)
        failure_reason = str(exc)
        failure_stacktrace_excerpt = traceback.format_exc()[-4000:]
        return _transition_run_job(
            job,
            status="failed",
            message=f"Run job failed: {exc}",
            error=failure_reason,
            artifacts=artifacts,
            result_summary_path=str(artifacts_dir / "summary.json") if (artifacts_dir / "summary.json").exists() else None,
            **_build_run_job_telemetry_updates(
                job,
                failure_reason=failure_reason,
                failure_stacktrace_excerpt=failure_stacktrace_excerpt,
                summary_payload=_read_json_if_exists(artifacts_dir / "summary.json"),
            ),
        )


def run_next_queued_job(
    *,
    queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT,
) -> dict[str, Any] | None:
    normalized_queue_root = _normalize_path(queue_root)
    jobs = list_run_jobs(normalized_queue_root)
    active_jobs = [job for job in jobs if job["status"] in ACTIVE_RUN_JOB_STATUSES]
    if active_jobs:
        active_run_ids = [job["run_id"] for job in active_jobs]
        raise RuntimeError(
            "Serial worker cannot start a new run_job while another run is active: "
            f"{active_run_ids}"
        )
    queued_job = next((job for job in jobs if job["status"] == "queued"), None)
    if queued_job is None:
        return None
    return execute_run_job(queued_job["run_id"], queue_root=normalized_queue_root)


def _require_canonical_scenario_bundle(
    bundle: ScenarioBundle,
    *,
    consumer: str,
) -> ScenarioBundle:
    if bundle.bundle_version == SCENARIO_BUNDLE_VERSION and bundle.bundle_manifest_path is not None:
        return bundle
    raise ValueError(
        f"{consumer} requires a canonical scenario bundle with '{BUNDLE_MANIFEST_FILENAME}' "
        f"and bundle_version '{SCENARIO_BUNDLE_VERSION}'. Legacy directory layouts are only "
        "supported for explicit low-level migration or test helpers."
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the decision platform pipeline.")
    parser.add_argument("--scenario", required=True, help="Scenario directory")
    parser.add_argument("--output-dir", required=False, help="Output directory for exports")
    parser.add_argument(
        "--include-engine-comparison",
        action="store_true",
        help="Export the diagnostic Julia-vs-Python comparison suite.",
    )
    parser.add_argument(
        "--allow-diagnostic-python-emulation",
        action="store_true",
        help="Allow python_emulated_julia for explicit diagnostic or audit runs only.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_decision_pipeline(
        args.scenario,
        args.output_dir,
        include_engine_comparison=args.include_engine_comparison,
        allow_diagnostic_python_emulation=args.allow_diagnostic_python_emulation,
    )
    summary = {
        "scenario_id": result["scenario_id"],
        "candidate_count": len(result["catalog"]),
        "feasible_count": sum(1 for item in result["catalog"] if bool(item["metrics"]["feasible"])),
        "scenario_bundle_root": result.get("scenario_bundle_root"),
        "scenario_bundle_version": result.get("scenario_bundle_version"),
        "scenario_bundle_manifest": result.get("scenario_bundle_manifest"),
        "scenario_bundle_files": result.get("scenario_bundle_files", {}),
        "scenario_provenance": result.get("scenario_provenance", {}),
        "default_profile_id": result.get("default_profile_id"),
        "best_profile": result.get("default_profile_id"),
        "selected_candidate_id": result.get("selected_candidate_id"),
        "top_candidate": result.get("selected_candidate_id"),
        "execution_mode": result.get("runtime", {}).get("execution_mode"),
        "official_gate_valid": result.get("runtime", {}).get("official_gate_valid"),
        "started_at": result.get("runtime", {}).get("started_at"),
        "finished_at": result.get("runtime", {}).get("finished_at"),
        "duration_s": result.get("runtime", {}).get("duration_s"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def _normalize_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _build_run_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{timestamp}_{uuid4().hex[:8]}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_run_job(job_path: Path) -> dict[str, Any]:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    normalized_job = _normalize_run_job(job)
    if normalized_job != job:
        _write_json(job_path, normalized_job)
    return normalized_job


def _read_run_events(events_path: Path) -> list[dict[str, Any]]:
    if not events_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def _append_run_event(job: dict[str, Any], *, status: str, message: str) -> None:
    event = {
        "timestamp": _utc_now_iso(),
        "run_id": job["run_id"],
        "status": status,
        "message": message,
    }
    events_path = Path(job["events_path"])
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _append_run_log(job: dict[str, Any], message: str) -> None:
    log_path = Path(job["log_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{_utc_now_iso()} {message}\n")


def _read_log_tail(log_path: Path, *, max_chars: int = 4000) -> str:
    if not log_path.exists():
        return ""
    text = log_path.read_text(encoding="utf-8")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _read_log_lines(log_path: Path) -> list[str]:
    if not log_path.exists():
        return []
    return [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _extract_logged_statuses(log_lines: list[str]) -> list[str]:
    statuses: list[str] = []
    for line in log_lines:
        _, _, message = line.partition(" ")
        status_candidate, separator, _ = message.partition(":")
        normalized = status_candidate.strip()
        if separator and normalized in RUN_JOB_STATUSES:
            statuses.append(normalized)
    return statuses


def _transition_run_job(
    job: dict[str, Any],
    *,
    status: str,
    message: str,
    **updates: Any,
) -> dict[str, Any]:
    if status not in RUN_JOB_STATUSES:
        raise ValueError(f"Unsupported run_job status: {status}")
    updated_job = dict(job)
    updated_job["status"] = status
    updated_job["updated_at"] = _utc_now_iso()
    updated_job.update(updates)
    if status == "running" and updated_job.get("started_at") is None:
        updated_job["started_at"] = updated_job["updated_at"]
    if status in TERMINAL_RUN_JOB_STATUSES and updated_job.get("finished_at") is None:
        updated_job["finished_at"] = updated_job["updated_at"]
    updated_job = _normalize_run_job(updated_job)
    _write_json(Path(updated_job["job_path"]), updated_job)
    _append_run_event(updated_job, status=status, message=message)
    _append_run_log(updated_job, f"{status}: {message}")
    return _refresh_persisted_run_job_summary(updated_job)


def _build_run_artifact_manifest(artifacts_dir: Path) -> dict[str, Any]:
    if not artifacts_dir.exists():
        return {
            "artifacts_dir": str(artifacts_dir),
            "files": [],
            "summary_json": None,
            "catalog_csv": None,
            "selected_candidate_json": None,
        }
    files = sorted(
        str(path.relative_to(artifacts_dir))
        for path in artifacts_dir.rglob("*")
        if path.is_file()
    )
    return {
        "artifacts_dir": str(artifacts_dir),
        "files": files,
        "summary_json": str(artifacts_dir / "summary.json") if (artifacts_dir / "summary.json").exists() else None,
        "catalog_csv": str(artifacts_dir / "catalog.csv") if (artifacts_dir / "catalog.csv").exists() else None,
        "selected_candidate_json": str(artifacts_dir / "selected_candidate.json")
        if (artifacts_dir / "selected_candidate.json").exists()
        else None,
    }


def _build_rerun_source(source_job: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_run_id": source_job["run_id"],
        "source_status": source_job["status"],
        "source_created_at": source_job.get("created_at"),
        "source_finished_at": source_job.get("finished_at"),
        "source_requested_execution_mode": source_job.get("requested_execution_mode"),
        "source_execution_mode": source_job.get("execution_mode"),
        "source_official_gate_valid": source_job.get("official_gate_valid"),
        "source_bundle_root": source_job.get("source_bundle_root"),
        "source_bundle_version": source_job.get("source_bundle_version"),
        "source_bundle_manifest": source_job.get("source_bundle_manifest"),
        "source_bundle_files": source_job.get("source_bundle_files", {}),
        "source_job_path": source_job.get("job_path"),
        "source_result_summary_path": source_job.get("result_summary_path"),
    }


def _build_run_job_detail(job: dict[str, Any]) -> dict[str, Any]:
    events_path = Path(job["events_path"])
    log_path = Path(job["log_path"])
    artifacts_dir = Path(job["artifacts_dir"])
    normalized_job = _normalize_run_job(job)
    source_bundle_reference_path = Path(normalized_job["source_bundle_reference_path"])
    events = _read_run_events(events_path)
    log_lines = _read_log_lines(log_path)
    artifacts = normalized_job.get("artifacts") or _build_run_artifact_manifest(artifacts_dir)
    return {
        **normalized_job,
        "events": events,
        "log_tail": _read_log_tail(log_path),
        "artifacts": artifacts,
        "evidence": _build_run_job_evidence(normalized_job, events=events, log_path=log_path, log_lines=log_lines, artifacts=artifacts),
        "source_bundle_reference": _read_json_if_exists(source_bundle_reference_path),
    }


def _build_scenario_provenance(
    bundle: ScenarioBundle,
    *,
    requested_scenario_dir: Path,
    output_dir: Path | None,
) -> dict[str, Any]:
    scenario_root = bundle.base_dir.expanduser().resolve(strict=False)
    manifest_path = bundle.bundle_manifest_path.expanduser().resolve(strict=False) if bundle.bundle_manifest_path else None
    return {
        "requested_scenario_dir": str(requested_scenario_dir),
        "scenario_root": str(scenario_root),
        "requested_dir_matches_bundle_root": requested_scenario_dir == scenario_root,
        "bundle_version": bundle.bundle_version,
        "bundle_manifest": str(manifest_path) if manifest_path else None,
        "bundle_files": {
            logical_name: str(path.relative_to(bundle.base_dir))
            for logical_name, path in bundle.resolved_files.items()
        },
        "output_dir": str(output_dir) if output_dir is not None else None,
    }


def _validate_runtime_policy(
    bundle: ScenarioBundle,
    *,
    allow_diagnostic_python_emulation: bool,
    include_engine_comparison: bool,
) -> None:
    probe_disabled = real_julia_probe_disabled()
    if include_engine_comparison and not allow_diagnostic_python_emulation:
        raise OfficialRuntimeConfigError(
            "Diagnostic engine comparison uses python_emulated_julia and requires explicit "
            "--allow-diagnostic-python-emulation opt-in."
        )
    if probe_disabled and not allow_diagnostic_python_emulation:
        raise OfficialRuntimeConfigError(
            f"{DISABLE_REAL_JULIA_PROBE_ENV}=1 disabled the real Julia probe. "
            "This execution is invalid for the official Julia-only gate; unset the override "
            "or rerun with --allow-diagnostic-python-emulation for explicit diagnostic use only."
        )
    if allow_diagnostic_python_emulation:
        return
    engine_cfg = bundle.scenario_settings.get("hydraulic_engine", {})
    primary_engine = str(engine_cfg.get("primary", "watermodels_jl")).strip()
    fallback_engine = str(engine_cfg.get("fallback", "none")).strip()
    if primary_engine == "watermodels_jl" and fallback_engine == "none":
        return
    raise OfficialRuntimeConfigError(
        "Official decision_platform runtime requires hydraulic_engine.primary=watermodels_jl "
        "and hydraulic_engine.fallback=none. Python emulation is diagnostic-only; rerun "
        "with --allow-diagnostic-python-emulation or allow_diagnostic_python_emulation=True "
        "only for audit, comparison or test flows."
    )


def _build_runtime_policy(
    *,
    allow_diagnostic_python_emulation: bool,
    include_engine_comparison: bool,
) -> dict[str, Any]:
    probe_disabled = real_julia_probe_disabled()
    diagnostic_features: list[str] = []
    if allow_diagnostic_python_emulation:
        diagnostic_features.append("python_emulation_opt_in")
    if include_engine_comparison:
        diagnostic_features.append("engine_comparison_opt_in")
    if probe_disabled:
        diagnostic_features.append("real_julia_probe_disabled")
    official_gate_valid = not diagnostic_features
    if probe_disabled:
        policy_mode = "diagnostic_override_probe_disabled"
        policy_message = (
            f"Diagnostic override {DISABLE_REAL_JULIA_PROBE_ENV}=1 disabled the real Julia probe. "
            "This run is not valid for the official Julia-only gate."
        )
    elif diagnostic_features:
        policy_mode = "diagnostic_opt_in"
        policy_message = (
            "Diagnostic features were enabled explicitly. This run should not be treated as the "
            "official Julia-only gate."
        )
    else:
        policy_mode = "official_julia_only"
        policy_message = "Official Julia-only gate: no diagnostic override or opt-in diagnostic feature is active."
    return {
        "policy_mode": policy_mode,
        "execution_mode": "official" if official_gate_valid else "diagnostic",
        "official_gate_valid": official_gate_valid,
        "allow_diagnostic_python_emulation": allow_diagnostic_python_emulation,
        "include_engine_comparison": include_engine_comparison,
        "real_julia_probe_disabled": probe_disabled,
        "real_julia_probe_disable_env": DISABLE_REAL_JULIA_PROBE_ENV if probe_disabled else None,
        "diagnostic_features": diagnostic_features,
        "policy_message": policy_message,
    }


def _build_runtime_metadata(
    *,
    started_at: datetime,
    runtime_policy: dict[str, Any],
    scenario_provenance: dict[str, Any],
) -> dict[str, Any]:
    finished_at = datetime.now(UTC)
    duration_s = round((finished_at - started_at).total_seconds(), 3)
    return {
        **runtime_policy,
        "scenario_provenance": scenario_provenance,
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": finished_at.isoformat().replace("+00:00", "Z"),
        "duration_s": duration_s,
    }


def _build_initial_run_job_telemetry(
    bundle: ScenarioBundle,
    *,
    runtime_policy: dict[str, Any],
) -> dict[str, Any]:
    probe_disabled = bool(runtime_policy.get("real_julia_probe_disabled"))
    return {
        "engine_requested": _read_requested_engine(bundle),
        "engine_used": None,
        "engine_mode": None,
        "julia_available": False if probe_disabled else None,
        "watermodels_available": False if probe_disabled else None,
        "real_julia_probe_disabled": probe_disabled,
        "execution_mode": runtime_policy.get("execution_mode"),
        "official_gate_valid": runtime_policy.get("official_gate_valid"),
        "duration_s": None,
        "policy_mode": runtime_policy.get("policy_mode"),
        "policy_message": runtime_policy.get("policy_message"),
        "failure_reason": None,
        "failure_stacktrace_excerpt": None,
    }


def _build_run_job_telemetry_updates(
    job: dict[str, Any],
    *,
    runtime: dict[str, Any] | None = None,
    runtime_policy: dict[str, Any] | None = None,
    summary_payload: dict[str, Any] | None = None,
    failure_reason: str | None = None,
    failure_stacktrace_excerpt: str | None = None,
) -> dict[str, Any]:
    runtime = runtime or {}
    runtime_policy = runtime_policy or {}
    summary_payload = summary_payload or {}
    return {
        "engine_requested": _coalesce(
            summary_payload.get("engine_requested"),
            job.get("engine_requested"),
        ),
        "engine_used": _coalesce(
            summary_payload.get("engine_used"),
            job.get("engine_used"),
        ),
        "engine_mode": _coalesce(
            summary_payload.get("engine_mode"),
            job.get("engine_mode"),
        ),
        "julia_available": _coalesce(
            summary_payload.get("julia_available"),
            job.get("julia_available"),
        ),
        "watermodels_available": _coalesce(
            summary_payload.get("watermodels_available"),
            job.get("watermodels_available"),
        ),
        "real_julia_probe_disabled": _coalesce(
            runtime.get("real_julia_probe_disabled"),
            summary_payload.get("real_julia_probe_disabled"),
            runtime_policy.get("real_julia_probe_disabled"),
            job.get("real_julia_probe_disabled"),
        ),
        "execution_mode": _coalesce(
            runtime.get("execution_mode"),
            summary_payload.get("execution_mode"),
            runtime_policy.get("execution_mode"),
            job.get("execution_mode"),
        ),
        "official_gate_valid": _coalesce(
            runtime.get("official_gate_valid"),
            summary_payload.get("official_gate_valid"),
            runtime_policy.get("official_gate_valid"),
            job.get("official_gate_valid"),
        ),
        "started_at": _coalesce(
            runtime.get("started_at"),
            summary_payload.get("runtime_started_at"),
            job.get("started_at"),
        ),
        "finished_at": _coalesce(
            runtime.get("finished_at"),
            summary_payload.get("runtime_finished_at"),
            job.get("finished_at"),
        ),
        "duration_s": _coalesce(
            runtime.get("duration_s"),
            summary_payload.get("runtime_duration_s"),
            job.get("duration_s"),
        ),
        "policy_mode": _coalesce(
            runtime.get("policy_mode"),
            summary_payload.get("runtime_policy_mode"),
            runtime_policy.get("policy_mode"),
            job.get("policy_mode"),
        ),
        "policy_message": _coalesce(
            runtime.get("policy_message"),
            summary_payload.get("runtime_policy_message"),
            runtime_policy.get("policy_message"),
            job.get("policy_message"),
        ),
        "failure_reason": _coalesce(
            failure_reason,
            job.get("failure_reason"),
        ),
        "failure_stacktrace_excerpt": _coalesce(
            failure_stacktrace_excerpt,
            job.get("failure_stacktrace_excerpt"),
        ),
    }


def _normalize_run_job(job: dict[str, Any]) -> dict[str, Any]:
    normalized_job = dict(job)
    runtime = dict(normalized_job.get("runtime") or {})
    runtime_policy = dict(normalized_job.get("runtime_policy") or {})
    summary_payload = _read_json_if_exists(_result_summary_path_for_job(normalized_job))

    for field, summary_key in (
        ("engine_requested", "engine_requested"),
        ("engine_used", "engine_used"),
        ("engine_mode", "engine_mode"),
        ("julia_available", "julia_available"),
        ("watermodels_available", "watermodels_available"),
        ("execution_mode", "execution_mode"),
        ("official_gate_valid", "official_gate_valid"),
        ("policy_mode", "runtime_policy_mode"),
        ("policy_message", "runtime_policy_message"),
        ("real_julia_probe_disabled", "real_julia_probe_disabled"),
    ):
        normalized_job[field] = _coalesce(
            normalized_job.get(field),
            runtime.get(field),
            runtime_policy.get(field),
            summary_payload.get(summary_key),
        )

    normalized_job["runtime_policy"] = {
        "policy_mode": _coalesce(runtime_policy.get("policy_mode"), normalized_job.get("policy_mode")),
        "execution_mode": _coalesce(runtime_policy.get("execution_mode"), normalized_job.get("execution_mode")),
        "official_gate_valid": _coalesce(
            runtime_policy.get("official_gate_valid"),
            normalized_job.get("official_gate_valid"),
        ),
        "allow_diagnostic_python_emulation": _coalesce(
            runtime_policy.get("allow_diagnostic_python_emulation"),
            normalized_job.get("allow_diagnostic_python_emulation"),
        ),
        "include_engine_comparison": _coalesce(
            runtime_policy.get("include_engine_comparison"),
            normalized_job.get("include_engine_comparison"),
        ),
        "real_julia_probe_disabled": _coalesce(
            runtime_policy.get("real_julia_probe_disabled"),
            normalized_job.get("real_julia_probe_disabled"),
        ),
        "real_julia_probe_disable_env": _coalesce(
            runtime_policy.get("real_julia_probe_disable_env"),
            runtime.get("real_julia_probe_disable_env"),
            DISABLE_REAL_JULIA_PROBE_ENV if normalized_job.get("real_julia_probe_disabled") else None,
        ),
        "diagnostic_features": list(runtime_policy.get("diagnostic_features") or []),
        "policy_message": _coalesce(runtime_policy.get("policy_message"), normalized_job.get("policy_message")),
    }
    if not normalized_job["runtime_policy"]["diagnostic_features"]:
        normalized_job["runtime_policy"]["diagnostic_features"] = _infer_diagnostic_features(normalized_job)

    normalized_job["engine_requested"] = _coalesce(
        normalized_job.get("engine_requested"),
        _read_requested_engine_from_job(normalized_job),
    )
    normalized_job["started_at"] = _coalesce(
        normalized_job.get("started_at"),
        runtime.get("started_at"),
        summary_payload.get("runtime_started_at"),
    )
    normalized_job["finished_at"] = _coalesce(
        normalized_job.get("finished_at"),
        runtime.get("finished_at"),
        summary_payload.get("runtime_finished_at"),
    )
    normalized_job["duration_s"] = _coalesce(
        normalized_job.get("duration_s"),
        runtime.get("duration_s"),
        summary_payload.get("runtime_duration_s"),
        _calculate_duration_seconds(normalized_job.get("started_at"), normalized_job.get("finished_at")),
    )
    normalized_job["failure_reason"] = _coalesce(normalized_job.get("failure_reason"), normalized_job.get("error"))
    normalized_job["failure_stacktrace_excerpt"] = normalized_job.get("failure_stacktrace_excerpt")
    queue_summary = dict(normalized_job.get("queue_summary") or {})
    if (
        queue_summary.get("status") != normalized_job.get("status")
        or queue_summary.get("updated_at") != normalized_job.get("updated_at")
        or "lineage" not in queue_summary
        or "evidence_summary" not in queue_summary
    ):
        normalized_job["queue_summary"] = _build_persisted_run_job_queue_summary(normalized_job)
    for field in RUN_JOB_TELEMETRY_FIELDS:
        normalized_job.setdefault(field, None)
    return normalized_job


def _read_requested_engine(bundle: ScenarioBundle) -> str:
    return str(bundle.scenario_settings.get("hydraulic_engine", {}).get("primary", "watermodels_jl")).strip()


def _read_requested_engine_from_job(job: dict[str, Any]) -> str | None:
    source_bundle_root = job.get("source_bundle_root")
    if not source_bundle_root:
        return None
    try:
        bundle = load_scenario_bundle(source_bundle_root)
    except Exception:
        return None
    return _read_requested_engine(bundle)


def _result_summary_path_for_job(job: dict[str, Any]) -> Path | None:
    summary_path = job.get("result_summary_path")
    if summary_path:
        return Path(summary_path)
    artifacts = job.get("artifacts") or {}
    summary_json = artifacts.get("summary_json")
    if summary_json:
        return Path(summary_json)
    return None


def _read_json_if_exists(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _build_run_job_evidence(
    job: dict[str, Any],
    *,
    events: list[dict[str, Any]],
    log_path: Path,
    log_lines: list[str],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    status = str(job.get("status") or "")
    event_statuses = [str(event.get("status")) for event in events if event.get("status")]
    run_dir = Path(job["run_dir"])
    queue_root = Path(job["queue_root"])
    artifacts_dir = Path(job["artifacts_dir"])
    log_statuses = _extract_logged_statuses(log_lines)
    if status in {"queued", "canceled"}:
        artifact_expectation = "no_execution_artifacts_expected"
    elif status == "completed":
        artifact_expectation = "summary_artifacts_expected"
    else:
        artifact_expectation = "execution_log_expected"
    return {
        "run_id": job["run_id"],
        "artifact_expectation": artifact_expectation,
        "run_dir_exists": run_dir.exists(),
        "run_dir_isolated": run_dir.parent == queue_root,
        "artifacts_dir_exists": artifacts_dir.exists(),
        "artifact_file_count": len(artifacts.get("files") or []),
        "artifact_files": list(artifacts.get("files") or []),
        "has_summary_json": bool(artifacts.get("summary_json")),
        "has_catalog_csv": bool(artifacts.get("catalog_csv")),
        "has_selected_candidate_json": bool(artifacts.get("selected_candidate_json")),
        "log_exists": log_path.exists(),
        "log_line_count": len(log_lines),
        "log_statuses": log_statuses,
        "final_status_logged": status in log_statuses,
        "event_count": len(event_statuses),
        "event_statuses": event_statuses,
        "final_status_recorded": bool(event_statuses) and event_statuses[-1] == status,
    }


def _build_run_job_lineage_summary(job: dict[str, Any]) -> dict[str, Any]:
    rerun_source = dict(job.get("rerun_source") or {})
    return {
        "is_rerun": bool(job.get("rerun_of_run_id")),
        "source_run_id": job.get("rerun_of_run_id"),
        "source_status": rerun_source.get("source_status"),
        "source_execution_mode": rerun_source.get("source_execution_mode"),
        "source_finished_at": rerun_source.get("source_finished_at"),
    }


def _build_persisted_run_job_queue_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "persisted_queue_summary",
        "status": job.get("status"),
        "updated_at": job.get("updated_at"),
        "lineage": _build_run_job_lineage_summary(job),
        "evidence_summary": _build_run_job_evidence_summary(job),
    }


def _refresh_persisted_run_job_summary(job: dict[str, Any]) -> dict[str, Any]:
    refreshed_job = dict(job)
    refreshed_job["queue_summary"] = _build_persisted_run_job_queue_summary(refreshed_job)
    _write_json(Path(refreshed_job["job_path"]), refreshed_job)
    return refreshed_job


def _build_run_job_evidence_summary(job: dict[str, Any]) -> dict[str, Any]:
    log_path = Path(job["log_path"])
    artifacts_dir = Path(job["artifacts_dir"])
    events = _read_run_events(Path(job["events_path"]))
    log_lines = _read_log_lines(log_path)
    artifacts = job.get("artifacts") or _build_run_artifact_manifest(artifacts_dir)
    evidence = _build_run_job_evidence(job, events=events, log_path=log_path, log_lines=log_lines, artifacts=artifacts)
    return {
        "artifact_expectation": evidence["artifact_expectation"],
        "artifacts_dir_exists": evidence["artifacts_dir_exists"],
        "artifact_file_count": evidence["artifact_file_count"],
        "has_summary_json": evidence["has_summary_json"],
        "has_selected_candidate_json": evidence["has_selected_candidate_json"],
        "log_exists": evidence["log_exists"],
        "final_status_logged": evidence["final_status_logged"],
        "final_status_recorded": evidence["final_status_recorded"],
    }


def _infer_diagnostic_features(job: dict[str, Any]) -> list[str]:
    features: list[str] = []
    if job.get("allow_diagnostic_python_emulation"):
        features.append("python_emulation_opt_in")
    if job.get("include_engine_comparison"):
        features.append("engine_comparison_opt_in")
    if job.get("real_julia_probe_disabled"):
        features.append("real_julia_probe_disabled")
    return features


def _calculate_duration_seconds(started_at: Any, finished_at: Any) -> float | None:
    if finished_at in (None, ""):
        return None
    started = _parse_iso_timestamp(started_at)
    finished = _parse_iso_timestamp(finished_at)
    if finished is None:
        return None
    if started is None:
        return 0.0
    return round(max((finished - started).total_seconds(), 0.0), 3)


def _parse_iso_timestamp(value: Any) -> datetime | None:
    text = str(value).strip() if value not in (None, "") else ""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


if __name__ == "__main__":
    main()
