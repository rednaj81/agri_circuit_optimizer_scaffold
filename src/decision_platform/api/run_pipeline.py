from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_platform.audit import build_engine_comparison_suite
from decision_platform.catalog.pipeline import build_solution_catalog, export_catalog
from decision_platform.data_io.loader import BUNDLE_MANIFEST_FILENAME, SCENARIO_BUNDLE_VERSION, ScenarioBundle, load_scenario_bundle
from decision_platform.julia_bridge.bridge import DISABLE_REAL_JULIA_PROBE_ENV, real_julia_probe_disabled


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
    bundle_reference = {
        "run_id": run_id,
        "scenario_provenance": scenario_provenance,
    }
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
        "source_bundle_manifest": scenario_provenance["bundle_manifest"],
        "source_bundle_files": scenario_provenance["bundle_files"],
        "scenario_provenance": scenario_provenance,
        "artifacts": {},
        "error": None,
        "runtime": None,
        "worker_mode": "serial",
    }
    _write_json(job_path, job)
    _append_run_event(job, status="queued", message="Run job queued.")
    _append_run_log(job, "queued: run job queued and awaiting serial worker.")
    return _read_run_job(job_path)


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
    return {
        "queue_root": str(_normalize_path(queue_root)),
        "worker_mode": "serial",
        "run_count": len(jobs),
        "status_counts": counts,
        "runs": [
            {
                "run_id": job["run_id"],
                "status": job["status"],
                "requested_execution_mode": job["requested_execution_mode"],
                "source_bundle_root": job["source_bundle_root"],
                "artifacts_dir": job["artifacts_dir"],
                "error": job.get("error"),
            }
            for job in jobs
        ],
    }


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
        return _transition_run_job(
            job,
            status="completed",
            message="Run job completed successfully.",
            runtime=runtime,
            error=None,
            artifacts=artifacts,
            selected_candidate_id=result.get("selected_candidate_id"),
            scenario_provenance=result.get("scenario_provenance"),
            result_summary_path=str(artifacts_dir / "summary.json"),
            execution_mode=runtime.get("execution_mode"),
            official_gate_valid=runtime.get("official_gate_valid"),
        )
    except Exception as exc:
        artifacts = _build_run_artifact_manifest(artifacts_dir)
        return _transition_run_job(
            job,
            status="failed",
            message=f"Run job failed: {exc}",
            error=str(exc),
            artifacts=artifacts,
            result_summary_path=str(artifacts_dir / "summary.json") if (artifacts_dir / "summary.json").exists() else None,
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
    return json.loads(job_path.read_text(encoding="utf-8"))


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
    if status == "running" and updated_job.get("started_at") is None:
        updated_job["started_at"] = updated_job["updated_at"]
    if status in TERMINAL_RUN_JOB_STATUSES:
        updated_job["finished_at"] = updated_job["updated_at"]
    updated_job.update(updates)
    _write_json(Path(updated_job["job_path"]), updated_job)
    _append_run_event(updated_job, status=status, message=message)
    _append_run_log(updated_job, f"{status}: {message}")
    return updated_job


def _build_run_artifact_manifest(artifacts_dir: Path) -> dict[str, Any]:
    if not artifacts_dir.exists():
        return {
            "artifacts_dir": str(artifacts_dir),
            "files": [],
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


if __name__ == "__main__":
    main()
