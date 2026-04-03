from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from decision_platform.catalog.pipeline import build_solution_catalog, export_catalog
from decision_platform.data_io.loader import load_scenario_bundle


def run_decision_pipeline(scenario_dir: str | Path, output_dir: str | Path | None = None) -> dict[str, Any]:
    bundle = load_scenario_bundle(scenario_dir)
    result = build_solution_catalog(bundle)
    if output_dir is not None:
        export_catalog(result, output_dir)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the decision platform pipeline.")
    parser.add_argument("--scenario", required=True, help="Scenario directory")
    parser.add_argument("--output-dir", required=False, help="Output directory for exports")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_decision_pipeline(args.scenario, args.output_dir)
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


if __name__ == "__main__":
    main()
