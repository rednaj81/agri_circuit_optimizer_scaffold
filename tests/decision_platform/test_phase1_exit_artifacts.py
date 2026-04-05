from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


pytestmark = [pytest.mark.fast]

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR_GUIDANCE_PATH = REPO_ROOT / "docs" / "codex_dual_agent_runtime" / "supervisor_guidance.json"
PHASE1_MANIFEST_PATH = REPO_ROOT / "docs" / "codex_dual_agent_runtime" / "phase_0_validation_manifest.json"
PHASE1_HANDOFF_PATH = REPO_ROOT / "docs" / "2026-04-05_phase1_wave5_exit_handoff.md"
PHASE3_HANDOFF_PATH = REPO_ROOT / "docs" / "2026-04-05_phase3_wave1_queue_open_handoff.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
STOP_RULES_PATH = (
    REPO_ROOT
    / "docs"
    / "codex_dual_agent_hydraulic_autonomy_bundle"
    / "automation"
    / "stop_rules.md"
)
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


def test_phase1_exit_artifacts_are_plain_utf8_without_bom() -> None:
    for path in (
        SUPERVISOR_GUIDANCE_PATH,
        PHASE1_MANIFEST_PATH,
        PHASE1_HANDOFF_PATH,
        PHASE3_HANDOFF_PATH,
        PYPROJECT_PATH,
        STOP_RULES_PATH,
        PHASE_PLAN_PATH,
    ):
        _assert_utf8_without_bom(path)


def test_phase1_exit_artifacts_have_consistent_closed_state() -> None:
    guidance = json.loads(_assert_utf8_without_bom(SUPERVISOR_GUIDANCE_PATH))
    manifest = json.loads(_assert_utf8_without_bom(PHASE1_MANIFEST_PATH))
    handoff_text = _assert_utf8_without_bom(PHASE1_HANDOFF_PATH)
    phase3_handoff_text = _assert_utf8_without_bom(PHASE3_HANDOFF_PATH)
    pyproject_text = _assert_utf8_without_bom(PYPROJECT_PATH)
    stop_rules_text = _assert_utf8_without_bom(STOP_RULES_PATH)
    phase_plan = yaml.safe_load(_assert_utf8_without_bom(PHASE_PLAN_PATH))

    assert guidance["phase_1_continuation_policy"]["additional_functional_waves_allowed"] is False
    assert guidance["phase_1_continuation_policy"]["final_operational_correction_wave"] == 7
    assert guidance["phase_1_exit_evidence"]["manifest_block"] == "phase_1_exit_validation"
    assert guidance["phase_1_exit_evidence"]["handoff"] == "docs/2026-04-05_phase1_wave5_exit_handoff.md"

    assert manifest["phase_1_additional_functional_waves_allowed"] is False
    assert manifest["phase_1_additional_operational_waves_allowed"] is False
    assert manifest["phase_1_post_close_exception_policy"] == "critical_evidence_integrity_only"
    assert manifest["phase_1_stop_reason"] == "low_residual_value_redirect_to_phase_3"
    assert manifest["phase_1_stop_trigger"] == "three_consecutive_low_value_auditor_waves"
    assert manifest["phase_1_stop_wave_index"] == 6
    assert manifest["final_operational_correction_wave"] == 7
    assert manifest["current_phase_guidance"] == "docs/codex_dual_agent_runtime/supervisor_guidance.json"
    assert manifest["current_phase_exit"] == "phase_3"
    assert manifest["current_acceptance_target"] == "tests/decision_platform/test_phase3_queue_acceptance.py"
    assert manifest["current_phase_handoff"] == "docs/2026-04-05_phase3_wave1_queue_open_handoff.md"
    assert manifest["phase_1_exit_validation"]["status"] == "sealed"
    assert manifest["phase_1_exit_validation"]["sealed_baseline_only"] is True
    assert manifest["phase_1_exit_validation"]["historical_reference_only"] is True
    assert manifest["phase_1_exit_validation"]["closure_handoff"] == "docs/2026-04-05_phase1_wave5_exit_handoff.md"
    assert manifest["phase_1_exit_validation"]["historical_redirect_phase"] == "phase_2"
    assert manifest["phase_1_exit_validation"]["active_functional_phase"] == "phase_3"
    assert manifest["phase_1_exit_validation"]["future_operational_updates_allowed"] is False
    assert manifest["phase_1_exit_validation"]["future_functional_updates_allowed"] is False
    assert manifest["phase_1_exit_validation"]["redirect_future_sessions_to_phase"] == "phase_3"
    assert manifest["phase_1_exit_validation"]["post_close_exception_policy"] == "critical_evidence_integrity_only"
    assert manifest["phase_1_exit_validation"]["incremental_track_closed_after_this_wave"] is True
    assert manifest["phase_1_exit_validation"]["stop_trigger"] == "three_consecutive_low_value_auditor_waves"
    assert manifest["phase_1_exit_validation"]["stop_wave_index"] == 6
    assert manifest["phase_1_exit_validation"]["no_additional_phase1_functional_waves"] is True
    assert manifest["phase_1_exit_validation"]["phase_1_operational_track_closed"] is True
    assert manifest["phase_1_exit_validation"]["operational_closeout"] == (
        "wave_7_regression_fix_only_no_new_functional_scope"
    )
    assert "tests/decision_platform/test_phase1_exit_artifacts.py" in manifest["phase_1_exit_validation"][
        "supporting_tests"
    ]
    assert manifest["phase_3_current_validation"]["status"] == "active"
    assert manifest["phase_3_current_validation"]["active_functional_phase"] is True
    assert manifest["phase_3_current_validation"]["sealed_baselines"] == ["phase_1", "phase_2"]
    assert "cache_dir =" not in pyproject_text
    assert 'addopts = "-p no:cacheprovider"' in pyproject_text

    assert "Wave 7 is a corrective regression fix only" in handoff_text
    assert "No additional functional wave should be scheduled inside `phase_1`" in handoff_text
    assert "`phase_1` is closed at this point." in handoff_text
    assert "the historical redirect to `phase_2` has already been consumed and closed" in handoff_text
    assert "the current functional phase is `phase_3`" in handoff_text
    assert "Any active functional progress now belongs to `phase_3`" in handoff_text
    assert "historical-reference-only" in handoff_text
    assert "No additional low-value operational correction wave should be scheduled inside `phase_1`" in handoff_text
    assert "the only admissible exception inside `phase_1` is a critical evidence-integrity repair" in handoff_text
    assert "three consecutive low-value waves according to the Auditor" in handoff_text
    assert "canonical closeout reference" in phase3_handoff_text
    assert "historical-reference-only governance" in phase3_handoff_text
    assert "não abrir novas ondas incrementais de rotina nessa fase" in stop_rules_text
    assert "permitir exceção apenas para correção crítica de integridade de evidências" in stop_rules_text
    assert "`phase_1` e `phase_2` são baselines seladas" in stop_rules_text
    assert "a continuidade funcional ativa deve seguir somente em `phase_3`" in stop_rules_text
    assert "`phase_1` foi formalmente encerrada após 3 ondas consecutivas de baixo valor segundo o Auditor" in stop_rules_text

    phase1_plan = phase_plan["phase_1"]
    phase2_plan = phase_plan["phase_2"]
    phase3_plan = phase_plan["phase_3"]
    assert phase1_plan["status"] == "closed"
    assert phase1_plan["closure_mode"] == "sealed_after_wave_7_regression_fix"
    assert phase1_plan["next_phase_id"] == "phase_2"
    assert any("Nenhuma nova wave funcional" in entry for entry in phase1_plan["phase_exit_checklist"])
    assert any("continuidade funcional ativa agora está em `phase_3`" in entry for entry in phase1_plan["phase_exit_checklist"])
    assert any("não abrir novas waves, nem mesmo correções operacionais de baixo valor" in entry for entry in phase1_plan["phase_exit_checklist"])
    assert any("qualquer exceção deve se limitar a correção crítica de integridade de evidências" in entry for entry in phase1_plan["phase_exit_checklist"])
    assert any("3 ondas consecutivas de baixo valor segundo o Auditor" in entry for entry in phase1_plan["phase_exit_checklist"])
    assert phase1_plan["closure_handoff"]["summary_doc"] == "docs/2026-04-05_phase1_wave5_exit_handoff.md"
    assert "continuidade funcional ativa agora reside na phase_3" in phase1_plan["closure_handoff"]["transition_note"]
    assert "nova correção operacional de baixo valor" in phase1_plan["closure_handoff"]["transition_note"]
    assert phase1_plan["closure_handoff"]["post_close_exception_policy"] == "critical_evidence_integrity_only"
    assert phase1_plan["closure_handoff"]["stop_trigger"] == "three_consecutive_low_value_auditor_waves"
    assert phase2_plan["target"] == "Entregar studio de nós e arestas"
    assert phase2_plan["closure_handoff"]["summary_doc"] == "docs/2026-04-05_phase2_exit.md"
    assert any(
        "docs/2026-04-05_phase1_wave5_exit_handoff.md" in entry for entry in phase3_plan["phase_entry_checklist"]
    )
    assert any(
        "Qualquer continuidade futura deve seguir somente na phase_3" in entry for entry in phase3_plan["phase_entry_checklist"]
    )
