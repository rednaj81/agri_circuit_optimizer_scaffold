from __future__ import annotations

import json
import os
import shutil
import subprocess
from uuid import uuid4
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_PATH = REPO_ROOT / "scripts" / "decision_platform_runtime_validation_profiles.json"
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_decision_platform_runtime_validation.ps1"
TEST_LOG_ROOT = REPO_ROOT / "tests" / "_tmp" / "runtime_validation_pytests"


def _load_profiles() -> dict:
    return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


def _profile_to_args(profile_name: str, profile: dict) -> list[str]:
    args = ["-Mode", profile["mode"]]
    if profile.get("require_disable_real_julia_probe_flag"):
        args.append("-DisableRealJuliaProbe")
    if profile.get("include_engine_comparison"):
        args.append("-IncludeEngineComparison")
    return args


def _make_logs_dir(prefix: str) -> Path:
    logs_dir = TEST_LOG_ROOT / f"{prefix}-{uuid4().hex}"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _run_validation_script(*args: str, logs_dir: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    command = [
        "pwsh",
        "-NoProfile",
        "-File",
        str(SCRIPT_PATH),
        *args,
        "-LogsDir",
        str(logs_dir),
        "-DryRun",
    ]
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _read_single_report(logs_dir: Path) -> dict:
    reports = sorted(logs_dir.glob("decision-platform-runtime-validation_*.json"))
    assert len(reports) == 1
    return json.loads(reports[0].read_text(encoding="utf-8"))


@pytest.mark.fast
def test_runtime_validation_profiles_define_expected_matrix() -> None:
    profiles = _load_profiles()

    assert profiles["probe_override_env"] == "DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE"
    assert set(profiles["profiles"]) == {"official", "diagnostic", "diagnostic_comparison"}
    assert profiles["profiles"]["official"]["mode"] == "official"
    assert profiles["profiles"]["diagnostic"]["mode"] == "diagnostic"
    assert profiles["profiles"]["diagnostic_comparison"]["include_engine_comparison"] is True
    assert "engine_comparison.json" in profiles["profiles"]["diagnostic_comparison"]["artifacts"]["required"]
    assert "engine_comparison.json" in profiles["profiles"]["official"]["artifacts"]["forbidden"]


@pytest.mark.fast
@pytest.mark.parametrize("profile_name", ["official", "diagnostic", "diagnostic_comparison"])
def test_runtime_validation_script_uses_declarative_profile_matrix(profile_name: str) -> None:
    profiles = _load_profiles()
    profile = profiles["profiles"][profile_name]
    logs_dir = _make_logs_dir(profile_name)
    try:
        result = _run_validation_script(*_profile_to_args(profile_name, profile), logs_dir=logs_dir)

        assert result.returncode == 0, result.stderr or result.stdout

        report = _read_single_report(logs_dir)
        assert report["success"] is True
        assert report["validation_profile"] == profile_name
        assert report["profile_config_path"].endswith("decision_platform_runtime_validation_profiles.json")
        assert report["steps"][-1]["status"] == "passed"
    finally:
        shutil.rmtree(logs_dir, ignore_errors=True)


@pytest.mark.fast
def test_runtime_validation_script_blocks_probe_override_for_official_profile() -> None:
    profiles = _load_profiles()
    logs_dir = _make_logs_dir("official-negative")
    try:
        result = _run_validation_script(
            *_profile_to_args("official", profiles["profiles"]["official"]),
            logs_dir=logs_dir,
            extra_env={profiles["probe_override_env"]: "1"},
        )

        assert result.returncode != 0

        report = _read_single_report(logs_dir)
        assert report["success"] is False
        assert report["validation_profile"] == "official"
        assert report["steps"][0]["status"] == "failed"
        assert profiles["probe_override_env"] in report["steps"][0]["error"]
        assert "official" in report["steps"][0]["error"]
    finally:
        shutil.rmtree(logs_dir, ignore_errors=True)
