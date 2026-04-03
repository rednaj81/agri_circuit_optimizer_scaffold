from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from decision_platform.data_io.loader import ScenarioBundle
from decision_platform.julia_bridge.python_engine import emulate_watermodels_cli


class JuliaBridgeError(RuntimeError):
    pass


def find_julia_executable() -> str | None:
    env_override = os.environ.get("JULIA_EXE", "").strip()
    if env_override and Path(env_override).exists():
        return env_override
    shell_julia = shutil.which("julia")
    if shell_julia and "WindowsApps" not in shell_julia:
        return shell_julia
    matches = sorted(Path("C:/Users").glob("*/.julia/juliaup/julia-*/bin/julia.exe"))
    if matches:
        return str(matches[-1])
    return shell_julia


def julia_available() -> bool:
    julia_exe = find_julia_executable()
    if not julia_exe:
        return False
    try:
        subprocess.run(
            [julia_exe, "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return True
    except Exception:
        return False


@lru_cache(maxsize=4)
def watermodels_available(project_dir: str | None = None) -> bool:
    julia_exe = find_julia_executable()
    if not julia_exe:
        return False
    repo_root = Path(__file__).resolve().parents[3]
    julia_project = str(Path(project_dir) if project_dir else repo_root / "julia")
    try:
        completed = subprocess.run(
            [
                julia_exe,
                f"--project={julia_project}",
                "-e",
                "using JuMP, HiGHS, WaterModels, JSON3; println(\"watermodels-ok\")",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return "watermodels-ok" in completed.stdout
    except Exception:
        return False


def evaluate_candidate_via_bridge(payload: dict, bundle: ScenarioBundle, *, prefer_real_julia: bool = True) -> dict:
    engine_cfg = bundle.scenario_settings.get("hydraulic_engine", {})
    engine_requested = str(engine_cfg.get("primary", "watermodels_jl"))
    fallback_engine = str(engine_cfg.get("fallback", "none"))
    julia_ok = julia_available()
    watermodels_ok = watermodels_available()

    if engine_requested == "python_emulated_julia":
        metrics = emulate_watermodels_cli(payload, bundle)
        return _decorate_engine_metadata(
            metrics,
            engine_requested=engine_requested,
            engine_used="python_emulated_julia",
            engine_mode="python_fallback_primary",
            julia_ok=julia_ok,
            watermodels_ok=watermodels_ok,
            warning=None,
        )

    if prefer_real_julia and julia_ok and watermodels_ok:
        metrics = _call_real_julia(payload)
        return _decorate_engine_metadata(
            metrics,
            engine_requested=engine_requested,
            engine_used="watermodels_jl",
            engine_mode="real_julia",
            julia_ok=julia_ok,
            watermodels_ok=watermodels_ok,
            warning=None,
        )

    if fallback_engine == "python_emulated_julia":
        warning = (
            "Falling back to python_emulated_julia because Julia/WaterModels is unavailable."
        )
        metrics = emulate_watermodels_cli(payload, bundle)
        return _decorate_engine_metadata(
            metrics,
            engine_requested=engine_requested,
            engine_used="python_emulated_julia",
            engine_mode="fallback_emulated",
            julia_ok=julia_ok,
            watermodels_ok=watermodels_ok,
            warning=warning,
        )

    raise JuliaBridgeError(
        "Scenario requires primary engine 'watermodels_jl' with fallback 'none', "
        "but Julia/WaterModels is unavailable. Install Julia, JuMP, HiGHS and WaterModels "
        "and configure JULIA_EXE if needed."
    )


def _decorate_engine_metadata(
    metrics: dict,
    *,
    engine_requested: str,
    engine_used: str,
    engine_mode: str,
    julia_ok: bool,
    watermodels_ok: bool,
    warning: str | None,
) -> dict:
    enriched = dict(metrics)
    enriched["engine_requested"] = engine_requested
    enriched["engine_used"] = engine_used
    enriched["engine_mode"] = engine_mode
    enriched["julia_available"] = julia_ok
    enriched["watermodels_available"] = watermodels_ok
    enriched["engine_warning"] = warning
    return enriched


def _call_real_julia(payload: dict) -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "julia" / "bin" / "run_scenario.jl"
    julia_exe = find_julia_executable()
    if not julia_exe:
        raise JuliaBridgeError("Julia executable not found.")
    with tempfile.TemporaryDirectory(prefix="decision-platform-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        input_path = tmp_path / "candidate_network.json"
        output_path = tmp_path / "result_metrics.json"
        input_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            [
                julia_exe,
                f"--project={repo_root / 'julia'}",
                str(script_path),
                str(input_path),
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        result = json.loads(output_path.read_text(encoding="utf-8"))
        result["julia_stdout"] = completed.stdout
        result["julia_stderr"] = completed.stderr
        return result
