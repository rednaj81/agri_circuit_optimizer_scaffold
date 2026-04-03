from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from decision_platform.data_io.loader import ScenarioBundle
from decision_platform.julia_bridge.python_engine import emulate_watermodels_cli


def julia_available() -> bool:
    return shutil.which("julia") is not None


def evaluate_candidate_via_bridge(payload: dict, bundle: ScenarioBundle, *, prefer_real_julia: bool = True) -> dict:
    if prefer_real_julia and julia_available():
        return _call_real_julia(payload)
    return emulate_watermodels_cli(payload, bundle)


def _call_real_julia(payload: dict) -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "julia" / "bin" / "run_scenario.jl"
    with tempfile.TemporaryDirectory(prefix="decision-platform-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / "candidate_network.json"
        output_path = tmp_path / "result_metrics.json"
        input_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        subprocess.run(
            ["julia", "--project", str(repo_root / "julia"), str(script_path), str(input_path), str(output_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(output_path.read_text(encoding="utf-8"))
