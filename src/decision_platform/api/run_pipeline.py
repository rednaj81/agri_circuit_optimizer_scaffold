from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from decision_platform.audit import build_engine_comparison_suite
from decision_platform.catalog.pipeline import build_solution_catalog, export_catalog
from decision_platform.data_io.loader import ScenarioBundle, load_scenario_bundle
from decision_platform.julia_bridge.bridge import DISABLE_REAL_JULIA_PROBE_ENV, real_julia_probe_disabled


class OfficialRuntimeConfigError(RuntimeError):
    pass


def run_decision_pipeline(
    scenario_dir: str | Path,
    output_dir: str | Path | None = None,
    *,
    include_engine_comparison: bool | None = None,
    allow_diagnostic_python_emulation: bool = False,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    bundle = load_scenario_bundle(scenario_dir)
    should_build_engine_comparison = False if include_engine_comparison is None else include_engine_comparison
    _validate_runtime_policy(
        bundle,
        allow_diagnostic_python_emulation=allow_diagnostic_python_emulation,
        include_engine_comparison=should_build_engine_comparison,
    )
    runtime_policy = _build_runtime_policy(
        allow_diagnostic_python_emulation=allow_diagnostic_python_emulation,
        include_engine_comparison=should_build_engine_comparison,
    )
    result = build_solution_catalog(bundle)
    result["runtime_policy"] = runtime_policy
    if should_build_engine_comparison:
        result["engine_comparison"] = build_engine_comparison_suite(bundle, julia_result=result)
        result["engine_comparison"]["execution_policy"] = runtime_policy
    result["runtime"] = _build_runtime_metadata(
        started_at=started_at,
        runtime_policy=runtime_policy,
    )
    if "engine_comparison" in result:
        result["engine_comparison"]["runtime"] = result["runtime"]
    if output_dir is not None:
        export_catalog(result, output_dir)
    return result


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
) -> dict[str, Any]:
    finished_at = datetime.now(UTC)
    duration_s = round((finished_at - started_at).total_seconds(), 3)
    return {
        **runtime_policy,
        "started_at": started_at.isoformat().replace("+00:00", "Z"),
        "finished_at": finished_at.isoformat().replace("+00:00", "Z"),
        "duration_s": duration_s,
    }


if __name__ == "__main__":
    main()
