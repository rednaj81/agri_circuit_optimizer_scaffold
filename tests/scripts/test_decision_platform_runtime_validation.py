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
PHASE_PLAN_PATH = REPO_ROOT / "docs" / "codex_dual_agent_hydraulic_autonomy_bundle" / "automation" / "phase_plan.yaml"


def _load_profiles() -> dict:
    return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


EXPECTED_PROFILE_SEMANTICS = {
    "official_preflight": {
        "validation_flow": "preflight",
        "validation_sufficiency": "triage_only",
        "official_gate_complete": False,
    },
    "official": {
        "validation_flow": "full",
        "validation_sufficiency": "official_evidence",
        "official_gate_complete": True,
        "execution_mode": "official",
        "official_gate_valid": True,
    },
    "diagnostic": {
        "validation_flow": "full",
        "validation_sufficiency": "diagnostic_evidence",
        "official_gate_complete": False,
        "execution_mode": "diagnostic",
        "official_gate_valid": False,
    },
    "diagnostic_comparison": {
        "validation_flow": "full",
        "validation_sufficiency": "diagnostic_evidence",
        "official_gate_complete": False,
        "execution_mode": "diagnostic",
        "official_gate_valid": False,
    },
}


def _profile_to_args(profile_name: str, profile: dict) -> list[str]:
    args = ["-Mode", profile["mode"]]
    if profile.get("validation_flow") == "preflight":
        args.append("-OfficialPreflight")
    if profile.get("require_disable_real_julia_probe_flag"):
        args.append("-DisableRealJuliaProbe")
    if profile.get("include_engine_comparison"):
        args.append("-IncludeEngineComparison")
    return args


def _make_logs_dir(prefix: str) -> Path:
    logs_dir = TEST_LOG_ROOT / f"{prefix}-{uuid4().hex}"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _run_validation_script(
    *args: str,
    logs_dir: Path,
    manifest_path: Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
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
        "-ManifestPath",
        str(manifest_path),
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


def _read_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@pytest.mark.fast
def test_runtime_validation_profiles_define_expected_matrix() -> None:
    profiles = _load_profiles()

    assert profiles["probe_override_env"] == "DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE"
    assert set(profiles["profiles"]) == set(EXPECTED_PROFILE_SEMANTICS)
    for profile_name, semantics in EXPECTED_PROFILE_SEMANTICS.items():
        profile = profiles["profiles"][profile_name]
        assert profile["validation_flow"] == semantics["validation_flow"]
        assert profile["validation_sufficiency"] == semantics["validation_sufficiency"]
    assert profiles["profiles"]["official"]["mode"] == "official"
    assert profiles["profiles"]["diagnostic"]["mode"] == "diagnostic"
    assert profiles["profiles"]["diagnostic_comparison"]["include_engine_comparison"] is True
    assert "engine_comparison.json" in profiles["profiles"]["diagnostic_comparison"]["artifacts"]["required"]
    assert "engine_comparison.json" in profiles["profiles"]["official"]["artifacts"]["forbidden"]


@pytest.mark.fast
def test_runtime_validation_profile_semantics_cover_phase0_exit_invariants() -> None:
    profiles = _load_profiles()["profiles"]

    preflight = profiles["official_preflight"]
    assert preflight["validation_flow"] == "preflight"
    assert preflight["validation_sufficiency"] == "triage_only"
    assert preflight["preflight_expectations"]["boolean_fields"]["official_gate_valid"] is True

    official = profiles["official"]
    assert official["validation_flow"] == "full"
    assert official["validation_sufficiency"] == "official_evidence"
    assert official["summary_expectations"]["string_fields"]["execution_mode"] == "official"
    assert official["summary_expectations"]["boolean_fields"]["official_gate_valid"] is True

    for profile_name in ("diagnostic", "diagnostic_comparison"):
        profile = profiles[profile_name]
        assert profile["validation_flow"] == "full"
        assert profile["validation_sufficiency"] == "diagnostic_evidence"
        assert profile["summary_expectations"]["string_fields"]["execution_mode"] == "diagnostic"
        assert profile["summary_expectations"]["boolean_fields"]["official_gate_valid"] is False


@pytest.mark.fast
def test_phase0_exit_checklist_references_the_same_semantics() -> None:
    checklist_text = PHASE_PLAN_PATH.read_text(encoding="utf-8")

    assert "phase_exit_checklist" in checklist_text
    assert "official_preflight" in checklist_text
    assert "triage_only" in checklist_text
    assert "official_gate_complete=false" in checklist_text
    assert "official_gate_complete=true" in checklist_text
    assert "execution_mode=official" in checklist_text
    assert "execution_mode=diagnostic" in checklist_text


@pytest.mark.fast
@pytest.mark.parametrize("profile_name", ["official_preflight", "official", "diagnostic", "diagnostic_comparison"])
def test_runtime_validation_script_uses_declarative_profile_matrix(profile_name: str) -> None:
    profiles = _load_profiles()
    profile = profiles["profiles"][profile_name]
    semantics = EXPECTED_PROFILE_SEMANTICS[profile_name]
    logs_dir = _make_logs_dir(profile_name)
    manifest_path = logs_dir / "phase_0_validation_manifest.json"
    try:
        result = _run_validation_script(
            *_profile_to_args(profile_name, profile),
            logs_dir=logs_dir,
            manifest_path=manifest_path,
        )

        assert result.returncode == 0, result.stderr or result.stdout

        report = _read_single_report(logs_dir)
        manifest = _read_manifest(manifest_path)
        assert report["success"] is True
        assert report["validation_profile"] == profile_name
        assert report["validation_flow"] == semantics["validation_flow"]
        assert report["validation_sufficiency"] == profile["validation_sufficiency"]
        assert report["official_gate_complete"] is semantics["official_gate_complete"]
        assert report["profile_config_path"].endswith("decision_platform_runtime_validation_profiles.json")
        assert report["validation_manifest_path"].endswith("phase_0_validation_manifest.json")
        assert report["steps"][-1]["status"] == "passed"
        assert manifest["phase_id"] == "phase_0"
        assert manifest["official_validation_profile"] == "official"
        assert set(manifest["profiles"]) == set(EXPECTED_PROFILE_SEMANTICS)
        manifest_entry = manifest["profiles"][profile_name]
        assert manifest_entry["validation_profile"] == profile_name
        assert manifest_entry["validation_flow"] == semantics["validation_flow"]
        assert manifest_entry["validation_sufficiency"] == semantics["validation_sufficiency"]
        assert manifest_entry["official_gate_complete"] is semantics["official_gate_complete"]
        assert manifest_entry["status"] == "passed"
        assert Path(manifest_entry["last_report_path"]).name.startswith(f"decision-platform-runtime-validation_{profile_name}_")
        if profile["validation_flow"] == "preflight":
            assert len(report["steps"]) == 3
            assert report["steps"][-1]["name"] == "3. Validar preflight oficial"
            assert manifest_entry["summary_path"] is None
            assert manifest_entry["evidence"]["official_gate_valid"] is True
        else:
            assert len(report["steps"]) == 5
            assert manifest_entry["evidence"]["execution_mode"] == semantics["execution_mode"]
            assert manifest_entry["evidence"]["official_gate_valid"] is semantics["official_gate_valid"]
    finally:
        shutil.rmtree(logs_dir, ignore_errors=True)


@pytest.mark.fast
def test_runtime_validation_script_blocks_probe_override_for_official_profile() -> None:
    profiles = _load_profiles()
    logs_dir = _make_logs_dir("official-negative")
    manifest_path = logs_dir / "phase_0_validation_manifest.json"
    try:
        result = _run_validation_script(
            *_profile_to_args("official", profiles["profiles"]["official"]),
            logs_dir=logs_dir,
            manifest_path=manifest_path,
            extra_env={profiles["probe_override_env"]: "1"},
        )

        assert result.returncode != 0

        report = _read_single_report(logs_dir)
        manifest = _read_manifest(manifest_path)
        assert report["success"] is False
        assert report["validation_profile"] == "official"
        assert report["steps"][0]["status"] == "failed"
        assert profiles["probe_override_env"] in report["steps"][0]["error"]
        assert "official" in report["steps"][0]["error"]
        assert manifest["profiles"]["official"]["status"] == "failed"
    finally:
        shutil.rmtree(logs_dir, ignore_errors=True)


@pytest.mark.fast
def test_runtime_validation_script_blocks_probe_override_for_official_preflight() -> None:
    profiles = _load_profiles()
    logs_dir = _make_logs_dir("official-preflight-negative")
    manifest_path = logs_dir / "phase_0_validation_manifest.json"
    try:
        result = _run_validation_script(
            *_profile_to_args("official_preflight", profiles["profiles"]["official_preflight"]),
            logs_dir=logs_dir,
            manifest_path=manifest_path,
            extra_env={profiles["probe_override_env"]: "1"},
        )

        assert result.returncode != 0

        report = _read_single_report(logs_dir)
        manifest = _read_manifest(manifest_path)
        assert report["success"] is False
        assert report["validation_profile"] == "official_preflight"
        assert report["official_gate_complete"] is False
        assert report["steps"][0]["status"] == "failed"
        assert profiles["probe_override_env"] in report["steps"][0]["error"]
        assert manifest["profiles"]["official_preflight"]["status"] == "failed"
    finally:
        shutil.rmtree(logs_dir, ignore_errors=True)
