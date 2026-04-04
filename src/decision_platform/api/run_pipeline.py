from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from decision_platform.audit import build_engine_comparison_suite
from decision_platform.catalog.pipeline import build_solution_catalog, export_catalog
from decision_platform.data_io.loader import ScenarioBundle, load_scenario_bundle


class OfficialRuntimeConfigError(RuntimeError):
    pass


def run_decision_pipeline(
    scenario_dir: str | Path,
    output_dir: str | Path | None = None,
    *,
    include_engine_comparison: bool | None = None,
    allow_diagnostic_python_emulation: bool = False,
) -> dict[str, Any]:
    bundle = load_scenario_bundle(scenario_dir)
    _validate_runtime_policy(
        bundle,
        allow_diagnostic_python_emulation=allow_diagnostic_python_emulation,
    )
    result = build_solution_catalog(bundle)
    should_build_engine_comparison = False if include_engine_comparison is None else include_engine_comparison
    if should_build_engine_comparison:
        result["engine_comparison"] = build_engine_comparison_suite(bundle, julia_result=result)
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
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def _validate_runtime_policy(
    bundle: ScenarioBundle,
    *,
    allow_diagnostic_python_emulation: bool,
) -> None:
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


if __name__ == "__main__":
    main()
