from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from decision_platform.api import run_pipeline
from decision_platform.api.run_pipeline import OfficialRuntimeConfigError, run_decision_pipeline
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


@pytest.mark.slow
def test_cli_rejects_python_emulation_without_explicit_opt_in() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_cli_reject_python",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    try:
        with pytest.raises(OfficialRuntimeConfigError):
            run_decision_pipeline(scenario_dir)
    finally:
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_cli_rejects_disabled_probe_without_explicit_diagnostic_opt_in(monkeypatch) -> None:
    monkeypatch.setenv("DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE", "1")
    with pytest.raises(OfficialRuntimeConfigError) as exc:
        run_decision_pipeline("data/decision_platform/maquete_v2")
    assert "invalid for the official Julia-only gate" in str(exc.value)


@pytest.mark.fast
def test_cli_rejects_engine_comparison_without_explicit_diagnostic_opt_in() -> None:
    with pytest.raises(OfficialRuntimeConfigError) as exc:
        run_decision_pipeline(
            "data/decision_platform/maquete_v2",
            include_engine_comparison=True,
        )
    assert "--allow-diagnostic-python-emulation" in str(exc.value)


@pytest.mark.fast
def test_run_decision_pipeline_skips_engine_comparison_by_default(monkeypatch) -> None:
    monkeypatch.delenv("DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE", raising=False)
    bundle = SimpleNamespace(
        scenario_settings={"hydraulic_engine": {"primary": "watermodels_jl", "fallback": "none"}}
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(run_pipeline, "load_scenario_bundle", lambda scenario_dir: bundle)
    monkeypatch.setattr(
        run_pipeline,
        "build_solution_catalog",
        lambda loaded_bundle: {
            "scenario_id": "maquete_v2",
            "catalog": [{"metrics": {"feasible": True}}],
            "default_profile_id": "balanced",
            "selected_candidate_id": "candidate-001",
        },
    )
    monkeypatch.setattr(
        run_pipeline,
        "build_engine_comparison_suite",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("comparison should stay opt-in")),
    )
    monkeypatch.setattr(
        run_pipeline,
        "export_catalog",
        lambda result, output_dir: captured.update({"result": result, "output_dir": output_dir}) or {},
    )

    result = run_pipeline.run_decision_pipeline("dummy-scenario", "dummy-output")

    assert "engine_comparison" not in result
    assert result["runtime"]["execution_mode"] == "official"
    assert result["runtime"]["official_gate_valid"] is True
    assert result["runtime"]["started_at"]
    assert result["runtime"]["finished_at"]
    assert isinstance(result["runtime"]["duration_s"], float)
    assert captured["output_dir"] == "dummy-output"
    assert "engine_comparison" not in captured["result"]


@pytest.mark.slow
def test_cli_uses_default_profile_and_selected_candidate_with_explicit_diagnostic_opt_in(monkeypatch, capsys) -> None:
    output_dir = Path("tests/_tmp/decision_platform_cli_out")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        captured: dict[str, object] = {}

        def fake_run_decision_pipeline(
            scenario,
            output_dir_arg=None,
            *,
            include_engine_comparison=None,
            allow_diagnostic_python_emulation=False,
        ):
            captured["scenario"] = scenario
            captured["output_dir"] = output_dir_arg
            captured["include_engine_comparison"] = include_engine_comparison
            captured["allow_diagnostic_python_emulation"] = allow_diagnostic_python_emulation
            if output_dir_arg is not None and include_engine_comparison:
                Path(output_dir_arg).mkdir(parents=True, exist_ok=True)
                (Path(output_dir_arg) / "engine_comparison.json").write_text("{}", encoding="utf-8")
            return {
                "scenario_id": "maquete_v2",
                "catalog": [{"metrics": {"feasible": True}}],
                "default_profile_id": "balanced",
                "selected_candidate_id": "candidate-001",
                "runtime": {
                    "execution_mode": "diagnostic",
                    "official_gate_valid": False,
                    "started_at": "2026-04-04T00:00:00Z",
                    "finished_at": "2026-04-04T00:00:01Z",
                    "duration_s": 1.0,
                },
            }

        monkeypatch.setattr(run_pipeline, "run_decision_pipeline", fake_run_decision_pipeline)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_pipeline.py",
                "--scenario",
                "data/decision_platform/maquete_v2",
                "--output-dir",
                str(output_dir),
                "--allow-diagnostic-python-emulation",
                "--include-engine-comparison",
            ],
        )
        run_pipeline.main()
        summary = json.loads(capsys.readouterr().out)
        assert captured["scenario"] == "data/decision_platform/maquete_v2"
        assert captured["output_dir"] == str(output_dir)
        assert captured["include_engine_comparison"] is True
        assert captured["allow_diagnostic_python_emulation"] is True
        assert summary["default_profile_id"] == "balanced"
        assert summary["selected_candidate_id"] == "candidate-001"
        assert summary["top_candidate"] == "candidate-001"
        assert summary["best_profile"] == "balanced"
        assert summary["execution_mode"] == "diagnostic"
        assert summary["official_gate_valid"] is False
        assert summary["duration_s"] == 1.0
        assert (output_dir / "engine_comparison.json").exists()
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
