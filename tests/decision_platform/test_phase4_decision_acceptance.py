from __future__ import annotations

import json

import pytest

from decision_platform.ui_dash.app import (
    render_decision_contrast_panel,
    render_decision_justification_panel,
    render_decision_signal_panel,
    render_decision_workspace_panel,
)


def _find_component_by_id(component: object, target_id: str) -> object | None:
    if getattr(component, "id", None) == target_id:
        return component
    children = getattr(component, "children", None)
    if children is None:
        return None
    child_items = children if isinstance(children, (list, tuple)) else [children]
    for child in child_items:
        found = _find_component_by_id(child, target_id)
        if found is not None:
            return found
    return None


def _collect_text(component: object) -> str:
    if component is None:
        return ""
    if isinstance(component, str):
        return component
    if isinstance(component, (int, float, bool)):
        return str(component)
    children = getattr(component, "children", None)
    if children is None:
        return ""
    child_items = children if isinstance(children, (list, tuple)) else [children]
    return "".join(_collect_text(child) for child in child_items)


@pytest.mark.fast
@pytest.mark.parametrize(
    ("summary", "expected_fragments"),
    [
        (
            {
                "candidate_id": "cand-01",
                "runner_up_candidate_id": "cand-02",
                "decision_status": "winner_clear",
                "technical_tie": False,
                "feasible": True,
                "winner_reason_summary": "Lidera com melhor equilíbrio entre custo e robustez.",
            },
            [
                "Winner claro",
                "Winner oficial agora",
                "Runner-up sob revisão",
                "Confirmar decisão final",
                "Decisão liberada",
                "Decisão pronta para confirmar",
                "Próxima ação humana",
                "Diferença principal agora",
                "Aprofundar se precisar",
            ],
        ),
        (
            {
                "candidate_id": "cand-01",
                "runner_up_candidate_id": "cand-02",
                "decision_status": "technical_tie",
                "technical_tie": True,
                "feasible": True,
                "key_factors": [{"summary": "winner e runner-up seguem empatados nas dimensões operacionais principais."}],
            },
            [
                "Empate técnico",
                "Fechar escolha assistida",
                "Empate técnico em revisão",
                "Empate técnico assistido",
                "Winner sugerido agora",
                "Runner-up ainda comparável",
                "Próxima ação humana",
                "Diferença principal em aberto",
                "Comparação em aberto",
            ],
        ),
        (
            {},
            [
                "Sem decisão utilizável",
                "Winner oficial indisponível",
                "Runner-up ainda indisponível",
                "Recuperar execução em Runs",
                "Passagem Runs -> Decisão",
                "Decisão bloqueada",
                "Diferença principal indisponível",
            ],
        ),
        (
            {
                "candidate_id": "cand-01",
                "runner_up_candidate_id": "cand-02",
                "decision_status": "winner_clear",
                "technical_tie": False,
                "feasible": False,
                "infeasibility_reason": "mandatory_route_failure",
            },
            [
                "Winner inviável",
                "Revisar bloqueio em Runs",
                "rota obrigatória não conseguiu fechar",
                "Bloqueio operacional",
                "Runner-up sob revisão",
                "Decisão bloqueada",
                "Diferença principal bloqueada",
            ],
        ),
    ],
)
def test_decision_workspace_first_fold_surfaces_primary_decision_states(summary: dict[str, object], expected_fragments: list[str]) -> None:
    panel = render_decision_workspace_panel(summary, {"visible_candidate_count": 3}, {"candidate_id": summary.get("candidate_id")})
    panel_text = _collect_text(panel)

    assert _find_component_by_id(panel, "decision-workspace-primary-fold") is not None
    assert _find_component_by_id(panel, "decision-workspace-state-hero") is not None
    assert _find_component_by_id(panel, "decision-workspace-state-rail") is not None
    assert "Leitura principal da decisão" in panel_text
    assert "Aprofundar se precisar" in panel_text
    for fragment in expected_fragments:
        assert fragment in panel_text


@pytest.mark.fast
def test_phase4_open_doc_inherits_phase3_evidence_blocker_honestly() -> None:
    from pathlib import Path

    open_text = Path("docs/2026-04-10_phase_ux_refinement_phase4_open.md").read_text(encoding="utf-8")

    assert "ux_phase_4" in open_text
    assert "blocked_on_evidence" in open_text
    assert "ux_phase_3" in open_text


@pytest.mark.fast
def test_wave8_snapshot_keeps_inherited_evidence_blocker_visible() -> None:
    from pathlib import Path

    snapshot = json.loads(Path("docs/2026-04-10_phase_ux_refinement_wave8_ui_snapshot.json").read_text(encoding="utf-8"))

    assert snapshot["phase_id"] == "phase_ux_refinement"
    assert snapshot["ux_phase_id"] == "ux_phase_4"
    assert snapshot["wave_index"] == 8
    assert "ux_phase_3=blocked_on_evidence" in snapshot["inherited_constraints"]
    assert snapshot["scenarios"]["technical_tie"]["contains"]["primary_difference"] is True
    assert snapshot["scenarios"]["technical_tie"]["contains"]["next_human_action"] is True


@pytest.mark.fast
def test_infeasible_decision_state_stays_blocked_across_secondary_panels() -> None:
    summary = {
        "candidate_id": "cand-01",
        "runner_up_candidate_id": "cand-02",
        "official_product_candidate_id": "cand-01",
        "decision_status": "winner_clear",
        "technical_tie": False,
        "feasible": False,
        "infeasibility_reason": "mandatory_route_failure",
        "winner_reason_summary": "Segue na frente por custo, mas sem fechar as rotas obrigatórias.",
        "key_factors": [{"summary": "o runner-up mantém leitura operacional mais segura."}],
    }
    contrast_text = _collect_text(render_decision_contrast_panel(summary))
    signal_text = _collect_text(render_decision_signal_panel(summary))
    justification_text = _collect_text(render_decision_justification_panel(summary))

    assert "winner atual permanece bloqueado" in contrast_text.lower()
    assert "a escolha oficial ficou inviável" in signal_text.lower()
    assert "exportação bloqueada enquanto o winner em leitura seguir inviável" in justification_text.lower()
    assert "use exportação apenas depois de confirmar o contraste final" not in justification_text.lower()


@pytest.mark.fast
def test_technical_tie_state_keeps_assisted_language_across_secondary_panels() -> None:
    summary = {
        "candidate_id": "cand-01",
        "runner_up_candidate_id": "cand-02",
        "official_product_candidate_id": "cand-03",
        "decision_status": "technical_tie",
        "technical_tie": True,
        "feasible": True,
        "winner_reason_summary": "O perfil atual ainda não separou o winner com folga suficiente.",
        "key_factors": [{"summary": "winner e runner-up seguem praticamente empatados nas dimensões principais."}],
    }
    workspace_text = _collect_text(render_decision_workspace_panel(summary, {"visible_candidate_count": 3}, {"candidate_id": "cand-03"}))
    contrast_text = _collect_text(render_decision_contrast_panel(summary))
    signal_text = _collect_text(render_decision_signal_panel(summary))
    justification_text = _collect_text(render_decision_justification_panel(summary))

    assert "winner sugerido agora" in workspace_text.lower()
    assert "runner-up ainda comparável" in workspace_text.lower()
    assert "escolha final humana" in workspace_text.lower()
    assert "diferença principal em aberto" in workspace_text.lower()
    assert "registre o critério humano do empate" in workspace_text.lower()
    assert "registrar a escolha humana final" in workspace_text.lower()
    assert "exporte apenas como decisão assistida" in workspace_text.lower()
    assert "comparação principal continua assistida" in contrast_text.lower()
    assert "o que está empatado" in contrast_text.lower()
    assert "a leitura continua em modo assistido" in signal_text.lower()
    assert "technical tie ativo; exporte apenas como decisão assistida" in justification_text.lower()
    assert "a escolha oficial segue viável na leitura atual do ranking" not in signal_text.lower()
