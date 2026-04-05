from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


pytestmark = [pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR_GUIDANCE_PATH = REPO_ROOT / "docs" / "codex_dual_agent_runtime" / "supervisor_guidance.json"
MANIFEST_PATH = REPO_ROOT / "docs" / "codex_dual_agent_runtime" / "phase_0_validation_manifest.json"
PHASE23_HANDOFF_PATH = REPO_ROOT / "docs" / "2026-04-05_phase2_to_phase3_handoff.md"
PHASE3_HANDOFF_PATH = REPO_ROOT / "docs" / "2026-04-05_phase3_wave1_queue_open_handoff.md"
PHASE_PLAN_PATH = (
    REPO_ROOT
    / "docs"
    / "codex_dual_agent_hydraulic_autonomy_bundle"
    / "automation"
    / "phase_plan.yaml"
)
UTF8_BOM = b"\xef\xbb\xbf"


def _assert_utf8_without_bom(path: Path) -> str:
    raw = path.read_bytes()
    assert not raw.startswith(UTF8_BOM), f"{path} must not start with a UTF-8 BOM"
    return path.read_text(encoding="utf-8")


def test_phase3_artifacts_are_plain_utf8_without_bom() -> None:
    for path in (
        SUPERVISOR_GUIDANCE_PATH,
        MANIFEST_PATH,
        PHASE23_HANDOFF_PATH,
        PHASE3_HANDOFF_PATH,
        PHASE_PLAN_PATH,
    ):
        _assert_utf8_without_bom(path)


def test_phase3_artifacts_have_consistent_active_state() -> None:
    guidance = json.loads(_assert_utf8_without_bom(SUPERVISOR_GUIDANCE_PATH))
    manifest = json.loads(_assert_utf8_without_bom(MANIFEST_PATH))
    phase23_handoff = _assert_utf8_without_bom(PHASE23_HANDOFF_PATH)
    phase3_handoff = _assert_utf8_without_bom(PHASE3_HANDOFF_PATH)
    phase_plan = yaml.safe_load(_assert_utf8_without_bom(PHASE_PLAN_PATH))

    assert guidance["phase_id"] == "phase_3"
    assert guidance["phase_assessment"] == "continue_phase"
    assert guidance["recommended_next_phase"] == "phase_3"
    assert guidance["current_phase_gate"]["manifest_block"] == "phase_3_current_validation"
    assert "tests/decision_platform/test_phase3_queue_acceptance.py" in guidance["current_phase_gate"]["tests"]
    assert guidance["closed_phases"]["phase_1"]["status"] == "closed"
    assert guidance["closed_phases"]["phase_2"]["status"] == "closed"
    assert guidance["phase_1_continuation_policy"]["additional_functional_waves_allowed"] is False

    assert manifest["current_phase_exit"] == "phase_3"
    assert manifest["current_phase_status"] == "active"
    assert manifest["current_acceptance_target"] == "tests/decision_platform/test_phase3_queue_acceptance.py"
    assert manifest["next_functional_phase"] == "phase_4"
    assert manifest["phase_1_exit_validation"]["status"] == "sealed"
    assert manifest["phase_2_exit_validation"]["status"] == "sealed"
    assert manifest["phase_3_current_validation"]["status"] == "active"
    assert manifest["phase_3_current_validation"]["acceptance_target"] == (
        "tests/decision_platform/test_phase3_queue_acceptance.py"
    )
    assert manifest["phase_3_current_validation"]["worker_mode"] == "serial"

    assert "`phase_2` está encerrada." in phase23_handoff
    assert "`phase_3` abriu" in phase23_handoff
    assert "tests/decision_platform/test_phase3_queue_acceptance.py" in phase23_handoff
    assert "worker serial explícito" in phase23_handoff
    assert "cancelamento explícito de jobs ainda em `queued`" in phase23_handoff
    assert "re-run explícito de runs `completed` ou `failed`" in phase23_handoff

    assert "Phase 3 Wave 1 - Queue Open Handoff" in phase3_handoff
    assert "tests/decision_platform/test_phase3_queue_acceptance.py" in phase3_handoff
    assert "phase_1` remains sealed" in phase3_handoff
    assert "phase_2` remains closed" in phase3_handoff
    assert "worker remains strictly serial" in phase3_handoff

    phase1_plan = phase_plan["phase_1"]
    phase2_plan = phase_plan["phase_2"]
    phase3_plan = phase_plan["phase_3"]
    assert phase1_plan["status"] == "closed"
    assert phase2_plan["status"] == "closed"
    assert phase2_plan["canonical_acceptance_target"] == "tests/decision_platform/test_phase2_exit_acceptance.py"
    assert phase3_plan["status"] == "in_progress"
    assert phase3_plan["current_acceptance_target"] == "tests/decision_platform/test_phase3_queue_acceptance.py"
    assert phase3_plan["current_handoff"] == "docs/2026-04-05_phase3_wave1_queue_open_handoff.md"
