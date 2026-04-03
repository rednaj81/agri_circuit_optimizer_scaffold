from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from decision_platform.api import run_pipeline
from decision_platform.api.run_pipeline import run_decision_pipeline
from tests.decision_platform.scenario_utils import cleanup_scenario_copy, prepare_scenario_copy


@pytest.mark.slow
def test_cli_uses_default_profile_and_selected_candidate(monkeypatch, capsys) -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_cli_selection",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = Path("tests/_tmp/decision_platform_cli_out")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    try:
        expected = run_decision_pipeline(scenario_dir)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_pipeline.py",
                "--scenario",
                str(scenario_dir),
                "--output-dir",
                str(output_dir),
            ],
        )
        run_pipeline.main()
        summary = json.loads(capsys.readouterr().out)
        assert summary["default_profile_id"] == expected["default_profile_id"]
        assert summary["selected_candidate_id"] == expected["selected_candidate_id"]
        assert summary["top_candidate"] == expected["selected_candidate_id"]
        assert summary["best_profile"] == expected["default_profile_id"]
    finally:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        cleanup_scenario_copy(scenario_dir)
