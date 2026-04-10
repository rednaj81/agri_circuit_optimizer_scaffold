from __future__ import annotations

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
                "Confirmar decisão assistida",
                "Decisão liberada",
            ],
        ),
        (
            {
                "candidate_id": "cand-01",
                "runner_up_candidate_id": "cand-02",
                "decision_status": "technical_tie",
                "technical_tie": True,
                "feasible": True,
            },
            [
                "Empate técnico",
                "Technical tie",
                "Explícito",
                "Fechar escolha assistida",
                "Empate técnico em revisão",
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
    assert "Faixa decisória operacional" in panel_text
    assert "Comparação assistida e contexto" in panel_text
    for fragment in expected_fragments:
        assert fragment in panel_text


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
    contrast_text = _collect_text(render_decision_contrast_panel(summary))
    signal_text = _collect_text(render_decision_signal_panel(summary))
    justification_text = _collect_text(render_decision_justification_panel(summary))

    assert "a escolha final pede leitura humana assistida" in contrast_text.lower()
    assert "a leitura continua em modo assistido" in signal_text.lower()
    assert "technical tie ativo; exporte apenas como decisão assistida" in justification_text.lower()
    assert "a escolha oficial segue viável na leitura atual do ranking" not in signal_text.lower()
