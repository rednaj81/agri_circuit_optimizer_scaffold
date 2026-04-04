from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_decision_platform_runtime_validation.ps1"
PROFILE_PATH = REPO_ROOT / "scripts" / "decision_platform_runtime_validation_profiles.json"
LOGS_DIR = REPO_ROOT / "tests" / "_tmp" / "runtime_validation_script_logs"


def _run_validation_script(*args: str) -> subprocess.CompletedProcess[str]:
    if LOGS_DIR.exists():
        shutil.rmtree(LOGS_DIR)
    command = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(SCRIPT_PATH),
        *args,
        "-LogsDir",
        str(LOGS_DIR),
        "-DryRun",
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False, cwd=REPO_ROOT)


def _latest_report() -> dict:
    report_paths = sorted(LOGS_DIR.glob("decision-platform-runtime-validation_*.json"))
    assert report_paths
    return json.loads(report_paths[-1].read_text(encoding="utf-8"))


@pytest.mark.fast
@pytest.mark.parametrize(
    ("args", "expected_profile"),
    [
        (["-Mode", "official"], "official"),
        (["-Mode", "diagnostic", "-DisableRealJuliaProbe"], "diagnostic"),
        (["-Mode", "diagnostic", "-DisableRealJuliaProbe", "-IncludeEngineComparison"], "diagnostic_comparison"),
    ],
)
def test_runtime_validation_script_dry_run_uses_declared_profile_matrix(
    args: list[str],
    expected_profile: str,
) -> None:
    completed = _run_validation_script(*args)

    assert completed.returncode == 0, completed.stderr
    report = _latest_report()
    assert report["success"] is True
    assert report["validation_profile"] == expected_profile
    assert Path(report["profile_config_path"]).resolve() == PROFILE_PATH.resolve()


@pytest.mark.fast
def test_runtime_validation_script_rejects_diagnostic_profile_without_probe_flag() -> None:
    completed = _run_validation_script("-Mode", "diagnostic")

    assert completed.returncode != 0
    report = _latest_report()
    assert report["success"] is False
    assert any(
        step["status"] == "failed" and "exige -DisableRealJuliaProbe" in str(step.get("error"))
        for step in report["steps"]
    )
