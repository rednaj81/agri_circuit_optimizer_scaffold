from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import pandas as pd
import yaml

from decision_platform.api.run_pipeline import (
    DEFAULT_RUN_QUEUE_ROOT,
    OfficialRuntimeConfigError,
    cancel_run_job,
    create_run_job,
    inspect_run_job,
    rerun_run_job,
    run_decision_pipeline,
    run_next_queued_job,
    summarize_run_jobs,
)
from decision_platform.catalog.explanation import build_selected_candidate_explanation
from decision_platform.catalog.pipeline import resolve_selected_candidate
from decision_platform.data_io.loader import BUNDLE_MANIFEST_FILENAME, SCENARIO_BUNDLE_VERSION, load_scenario_bundle
from decision_platform.data_io.storage import bundle_authoring_payload, save_authored_scenario_bundle
from decision_platform.ranking.scoring import apply_dynamic_weights
from decision_platform.rendering.circuit import build_solution_comparison_figure
from decision_platform.ui_dash._compat import DASH_AVAILABLE, Dash, Input, Output, State, cyto, dag, dcc, html


UI_FONT_STACK = '"IBM Plex Sans", "Segoe UI", sans-serif'
UI_PAGE_STYLE = {
    "minHeight": "100vh",
    "padding": "18px",
    "background": "linear-gradient(180deg, #f4efe6 0%, #eef4f1 48%, #f8fafb 100%)",
    "color": "#18322c",
    "fontFamily": UI_FONT_STACK,
}
UI_SHELL_STYLE = {
    "maxWidth": "1720px",
    "margin": "0 auto",
}
UI_HERO_STYLE = {
    "padding": "20px",
    "borderRadius": "24px",
    "background": "linear-gradient(135deg, #103b35 0%, #1f5c51 58%, #d7e5c1 100%)",
    "color": "#f5f3ee",
    "boxShadow": "0 18px 40px rgba(16, 59, 53, 0.16)",
    "marginBottom": "14px",
}
UI_CARD_STYLE = {
    "background": "rgba(255, 255, 255, 0.92)",
    "border": "1px solid rgba(16, 59, 53, 0.12)",
    "borderRadius": "20px",
    "padding": "18px",
    "boxShadow": "0 14px 36px rgba(27, 45, 39, 0.08)",
}
UI_MUTED_CARD_STYLE = {
    **UI_CARD_STYLE,
    "background": "rgba(248, 250, 247, 0.96)",
}
UI_SECTION_STYLE = {
    "display": "grid",
    "gap": "16px",
    "marginTop": "18px",
}
UI_TWO_COLUMN_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(320px, 1fr))",
    "gap": "16px",
}
UI_THREE_COLUMN_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
    "gap": "12px",
}
UI_FIELD_BLOCK_STYLE = {
    "display": "grid",
    "gap": "6px",
    "marginBottom": "10px",
}
UI_ACTION_ROW_STYLE = {
    "display": "flex",
    "flexWrap": "wrap",
    "gap": "10px",
    "marginTop": "12px",
}
UI_BUTTON_STYLE = {
    "padding": "10px 14px",
    "borderRadius": "12px",
    "border": "1px solid rgba(16, 59, 53, 0.18)",
    "background": "#f5f8f4",
    "cursor": "pointer",
}
UI_BUTTON_LINK_STYLE = {
    **UI_BUTTON_STYLE,
    "display": "inline-flex",
    "alignItems": "center",
    "justifyContent": "center",
    "textDecoration": "none",
    "color": "#18322c",
    "fontWeight": 700,
}
UI_PRIMARY_BUTTON_LINK_STYLE = {
    **UI_BUTTON_LINK_STYLE,
    "background": "#103b35",
    "border": "1px solid #103b35",
    "color": "#f5f3ee",
}
UI_NAV_LINK_STYLE = {
    "display": "inline-flex",
    "alignItems": "center",
    "justifyContent": "center",
    "padding": "10px 14px",
    "borderRadius": "999px",
    "border": "1px solid rgba(255, 255, 255, 0.22)",
    "background": "rgba(255, 255, 255, 0.12)",
    "color": "#f5f3ee",
    "fontWeight": 700,
    "textDecoration": "none",
}
UI_JOURNEY_PANEL_STYLE = {
    **UI_CARD_STYLE,
    "marginBottom": "12px",
}
UI_JOURNEY_CARD_STYLE = {
    **UI_MUTED_CARD_STYLE,
    "padding": "14px",
    "display": "grid",
    "gap": "8px",
    "height": "100%",
}
UI_JOURNEY_CARD_ACTIVE_STYLE = {
    **UI_JOURNEY_CARD_STYLE,
    "background": "linear-gradient(135deg, rgba(16, 59, 53, 0.95) 0%, rgba(31, 92, 81, 0.92) 100%)",
    "border": "1px solid rgba(16, 59, 53, 0.24)",
    "color": "#f5f3ee",
    "boxShadow": "0 18px 36px rgba(16, 59, 53, 0.18)",
}
UI_PERSISTENT_BANNER_STYLE = {
    **UI_CARD_STYLE,
    "marginBottom": "12px",
    "position": "sticky",
    "top": "10px",
    "zIndex": 10,
    "backdropFilter": "blur(18px)",
}
UI_STUDIO_MAIN_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "minmax(0, 1.75fr) minmax(360px, 430px)",
    "gap": "18px",
    "alignItems": "start",
}
UI_STUDIO_SIDEBAR_STYLE = {
    "display": "grid",
    "gap": "14px",
    "alignContent": "start",
}
UI_STUDIO_CANVAS_CARD_STYLE = {
    **UI_CARD_STYLE,
    "padding": "16px",
}
UI_COMPACT_BANNER_CARD_STYLE = {
    **UI_MUTED_CARD_STYLE,
    "padding": "12px 14px",
}
UI_PILL_STYLE = {
    "display": "inline-flex",
    "alignItems": "center",
    "padding": "6px 10px",
    "borderRadius": "999px",
    "fontSize": "12px",
    "fontWeight": 700,
    "background": "#dfeee7",
    "color": "#104338",
}
UI_DEBUG_PRE_STYLE = {
    "whiteSpace": "pre-wrap",
    "background": "#10231e",
    "color": "#eaf1ee",
    "padding": "14px",
    "borderRadius": "14px",
    "overflowX": "auto",
    "fontSize": "12px",
}


def _safe_json_loads(text: Any) -> dict[str, Any]:
    if isinstance(text, dict):
        return text
    if not isinstance(text, str) or not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _journey_step_card(step: str, title: str, description: str) -> Any:
    return html.Div(
        style={
            "padding": "12px 14px",
            "borderRadius": "16px",
            "background": "rgba(255, 255, 255, 0.15)",
            "border": "1px solid rgba(255, 255, 255, 0.18)",
        },
        children=[
            html.Div(step, style={"fontSize": "11px", "fontWeight": 700, "letterSpacing": "0.12em", "opacity": 0.8}),
            html.Div(title, style={"fontSize": "18px", "fontWeight": 700, "marginTop": "4px"}),
            html.Div(description, style={"fontSize": "13px", "lineHeight": "1.45", "marginTop": "4px"}),
        ],
    )


def _hero_navigation_link(label: str, href: str, component_id: str) -> Any:
    return html.A(label, href=href, id=component_id, style=UI_NAV_LINK_STYLE)


def _button_link(label: str, href: str, component_id: str, *, primary: bool = False) -> Any:
    return html.A(
        label,
        href=href,
        id=component_id,
        style=UI_PRIMARY_BUTTON_LINK_STYLE if primary else UI_BUTTON_LINK_STYLE,
    )


def _guidance_card(label: str, text: str) -> Any:
    return html.Div(
        style={**UI_MUTED_CARD_STYLE, "padding": "12px"},
        children=[
            html.Div(label, style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(text, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
        ],
    )


def _journey_card_status_pill(label: str, *, active: bool) -> Any:
    if active:
        style = {
            "display": "inline-flex",
            "alignItems": "center",
            "padding": "6px 10px",
            "borderRadius": "999px",
            "fontSize": "12px",
            "fontWeight": 700,
            "background": "rgba(255, 255, 255, 0.14)",
            "color": "#f5f3ee",
        }
    else:
        style = UI_PILL_STYLE
    return html.Span(label, style=style)


def _space_switcher_link(label: str, space: str, active_space: str | None) -> Any:
    is_active = str(active_space or "studio") == space
    style = {
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "padding": "8px 12px",
        "borderRadius": "999px",
        "border": "1px solid rgba(16, 59, 53, 0.12)",
        "textDecoration": "none",
        "fontWeight": 700,
        "color": "#18322c",
        "background": "#f4f8f5" if not is_active else "#103b35",
    }
    if is_active:
        style["color"] = "#f5f3ee"
        style["boxShadow"] = "0 8px 18px rgba(16, 59, 53, 0.18)"
    return html.A(label, href=f"?tab={space}", id=f"product-space-switcher-{space}-link", style=style)


def _screen_opening_panel(
    title: str,
    headline: str,
    objective: str,
    next_action: str,
    flow_cards: list[tuple[str, str]],
    ctas: list[Any],
) -> Any:
    return html.Div(
        children=[
            html.H3(title, style={"marginTop": 0}),
            html.Div("Estado atual", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(headline, style={"fontWeight": 700, "lineHeight": "1.5", "margin": "6px 0 14px"}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Objetivo desta área", objective),
                    _guidance_card("Próxima ação", next_action),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[_guidance_card(label, text) for label, text in flow_cards],
            ),
            html.Div(style={**UI_ACTION_ROW_STYLE, "marginTop": "14px"}, children=ctas),
        ]
    )


def _product_space_content(space: str | None) -> dict[str, str]:
    normalized = str(space or "studio").strip().lower()
    if normalized == "runs":
        return {
            "label": "Runs",
            "headline": "Fila local e execução em foco",
            "description": "Aqui a jornada sai do preparo do cenário e vira leitura operacional da fila, da run em foco e do último resultado.",
            "objective": "Decidir se ainda falta corrigir o cenário, executar a próxima rodada ou já abrir a decisão assistida.",
            "next_action": "Revise a fila e a execução em foco antes de avançar para Decisão.",
        }
    if normalized == "decision":
        return {
            "label": "Decisão",
            "headline": "Winner, runner-up e contraste com contexto",
            "description": "Aqui a jornada deixa de ser operacional e passa a ser comparativa, mantendo candidato oficial, runner-up e sinais de risco na mesma leitura.",
            "objective": "Confirmar se já existe escolha oficial legível ou se ainda falta contraste para a decisão humana assistida.",
            "next_action": "Valide winner, runner-up e sinais de risco antes de exportar ou abrir Auditoria.",
        }
    if normalized == "audit":
        return {
            "label": "Auditoria",
            "headline": "Trilha canônica e evidência técnica",
            "description": "Aqui ficam bundle, YAMLs e tabelas completas para reconciliação e explicabilidade, fora do caminho primário de produto.",
            "objective": "Aprofundar persistência, contrato e evidência técnica sem recolocar isso na primeira dobra das outras áreas.",
            "next_action": "Use esta área apenas quando a leitura principal não for suficiente para reconciliar o cenário ou a decisão.",
        }
    return {
        "label": "Studio",
        "headline": "Grafo de negócio e readiness do cenário",
        "description": "Aqui a jornada começa no canvas principal, com foco em montar o cenário, revisar readiness e manter a leitura na camada de negócio.",
        "objective": "Deixar o cenário claro o suficiente para seguir para Runs sem depender da trilha técnica como superfície principal.",
        "next_action": "Resolva readiness, projeção e foco do canvas antes de abrir a fila.",
    }


def _journey_space_state(space: str, studio_summary: dict[str, Any], run_summary: dict[str, Any], decision_summary: dict[str, Any]) -> dict[str, str]:
    if space == "studio":
        status = str(studio_summary.get("status") or "needs_attention")
        blocker_count = int(studio_summary.get("blocker_count", 0) or 0)
        warning_count = int(studio_summary.get("warning_count", 0) or 0)
        if status == "ready":
            state_label = "Pronto para Runs"
        elif blocker_count:
            state_label = "Bloqueios no cenário"
        elif warning_count:
            state_label = "Readiness parcial"
        else:
            state_label = "Montagem em andamento"
        return {
            "purpose": "Montar o cenário no grafo de negócio e liberar o gate principal de readiness.",
            "state_label": state_label,
            "state_text": str(studio_summary.get("readiness_headline") or "A leitura principal ainda depende de revisão estrutural no Studio."),
            "next_action": str((studio_summary.get("next_steps") or ["Revise o readiness e a projeção do cenário antes de abrir a fila."])[0]),
            "href": "?tab=studio",
        }
    if space == "runs":
        next_queued_run_id = str(run_summary.get("next_queued_run_id") or "").strip()
        active_run_ids = [str(item) for item in run_summary.get("active_run_ids", []) if str(item).strip()]
        failed_count = int((run_summary.get("status_counts") or {}).get("failed", 0) or 0)
        run_count = int(run_summary.get("run_count", 0) or 0)
        if active_run_ids:
            state_label = "Execução em andamento"
            state_text = f"Há uma run em andamento agora ({active_run_ids[0]})."
            next_action = "Acompanhe a execução em foco antes de abrir outra rodada ou avançar para Decisão."
        elif next_queued_run_id:
            state_label = "Fila pronta"
            state_text = f"A próxima run da fila é {next_queued_run_id}."
            next_action = "Revise a fila e execute apenas a próxima rodada necessária."
        elif failed_count and run_count:
            state_label = "Histórico exige revisão"
            state_text = "A fila está sem pendências, mas ainda há falhas recentes no histórico."
            next_action = "Abra a run em foco e revise o bloqueio antes de reenfileirar."
        elif run_count:
            state_label = "Histórico disponível"
            state_text = "A fila local está livre e já existe histórico suficiente para leitura operacional."
            next_action = "Use a run em foco para decidir se já vale abrir a Decisão ou executar outra rodada."
        else:
            state_label = "Sem runs"
            state_text = "Nenhuma run foi registrada ainda para este cenário."
            next_action = "Enfileire o cenário atual quando o Studio estiver pronto."
        return {
            "purpose": "Ler fila, execução atual e último resumo executivo sem depender de logs brutos.",
            "state_label": state_label,
            "state_text": state_text,
            "next_action": next_action,
            "href": "?tab=runs",
        }
    if space == "decision":
        decision_state = _decision_primary_state(decision_summary)
        return {
            "purpose": "Comparar winner, runner-up e technical tie com leitura humana assistida.",
            "state_label": decision_state["state_label"],
            "state_text": decision_state["headline"],
            "next_action": decision_state["next_action"],
            "href": "?tab=decision",
        }
    return {
        "purpose": "Reconciliar bundle, contrato e trilha técnica fora da superfície principal.",
        "state_label": "Trilha técnica",
        "state_text": "Persistência do bundle, YAMLs e tabelas completas continuam preservadas para reconciliação.",
        "next_action": "Abra esta área apenas quando a leitura principal de Studio, Runs ou Decisão não for suficiente.",
        "href": "?tab=audit",
    }


def _space_transition_guidance(
    space: str,
    studio_summary: dict[str, Any],
    run_summary: dict[str, Any],
    decision_summary: dict[str, Any],
) -> dict[str, str]:
    studio_status = str(studio_summary.get("status") or "needs_attention").strip().lower()
    studio_blocker_count = int(studio_summary.get("blocker_count", 0) or 0)
    studio_warning_count = int(studio_summary.get("warning_count", 0) or 0)
    run_count = int(run_summary.get("run_count", 0) or 0)
    next_queued_run_id = str(run_summary.get("next_queued_run_id") or "").strip()
    active_run_ids = [str(item) for item in run_summary.get("active_run_ids", []) if str(item).strip()]
    decision_candidate_id = str(decision_summary.get("candidate_id") or decision_summary.get("selected_candidate_id") or "").strip()
    decision_state = _decision_primary_state(decision_summary)

    if space == "studio":
        if studio_status == "ready":
            return {
                "flow_label": "Fluxo liberado",
                "flow_text": str(studio_summary.get("readiness_headline") or "O cenário já pode sair do Studio sem depender da trilha técnica."),
                "target_space": "runs",
                "target_label": "Seguir para Runs",
                "target_reason": "O gate principal de readiness está liberado; a fila passa a ser a próxima leitura principal.",
            }
        if studio_blocker_count:
            return {
                "flow_label": "Bloqueado no Studio",
                "flow_text": str(studio_summary.get("readiness_headline") or "Ainda existem bloqueios impedindo a passagem segura para Runs."),
                "target_space": "studio",
                "target_label": "Continuar no Studio",
                "target_reason": str(studio_summary.get("primary_action") or "Corrija conectividade, rotas obrigatórias e medição direta no canvas antes de sair desta área."),
            }
        if studio_warning_count:
            return {
                "flow_label": "Readiness parcial",
                "flow_text": str(studio_summary.get("readiness_headline") or "Ainda existem avisos que merecem revisão antes da fila."),
                "target_space": "studio",
                "target_label": "Fechar avisos no Studio",
                "target_reason": str(studio_summary.get("primary_action") or "Revise os avisos do cenário antes de decidir se já vale abrir Runs."),
            }
        return {
            "flow_label": "Montagem em andamento",
            "flow_text": "O canvas ainda segue como superfície principal para completar a leitura do cenário.",
            "target_space": "studio",
            "target_label": "Continuar no Studio",
            "target_reason": "Termine a montagem e a revisão do readiness antes de avançar para a fila.",
        }
    if space == "runs":
        if decision_candidate_id:
            return {
                "flow_label": "Decisão disponível",
                "flow_text": decision_state["headline"],
                "target_space": "decision",
                "target_label": "Ir para Decisão",
                "target_reason": "Já existe resultado utilizável para comparar winner, runner-up e sinais de risco.",
            }
        if active_run_ids:
            return {
                "flow_label": "Execução em andamento",
                "flow_text": f"A run {active_run_ids[0]} ainda está em processamento e segue como foco desta área.",
                "target_space": "runs",
                "target_label": "Acompanhar Runs",
                "target_reason": "Espere a execução terminar antes de trocar a leitura principal para Decisão.",
            }
        if next_queued_run_id:
            return {
                "flow_label": "Fila pronta",
                "flow_text": f"A próxima run na fila é {next_queued_run_id}.",
                "target_space": "runs",
                "target_label": "Revisar fila",
                "target_reason": "Confirme a próxima rodada necessária antes de abrir outra área.",
            }
        if studio_status != "ready":
            return {
                "flow_label": "Studio ainda bloqueia a fila",
                "flow_text": str(studio_summary.get("readiness_headline") or "O cenário ainda não está pronto para sustentar uma nova run."),
                "target_space": "studio",
                "target_label": "Voltar ao Studio",
                "target_reason": str(studio_summary.get("primary_action") or "Feche os bloqueios do cenário antes de insistir em Runs."),
            }
        if run_count:
            return {
                "flow_label": "Histórico sem decisão clara",
                "flow_text": "Já existe histórico, mas a leitura principal ainda não liberou uma decisão utilizável.",
                "target_space": "runs",
                "target_label": "Continuar em Runs",
                "target_reason": "Revise a execução mais recente e decida se vale reenfileirar ou abrir Decisão com cautela.",
            }
        return {
            "flow_label": "Fila vazia",
            "flow_text": "Nenhuma run foi registrada ainda para este cenário.",
            "target_space": "studio" if studio_status != "ready" else "runs",
            "target_label": "Preparar próxima run" if studio_status == "ready" else "Voltar ao Studio",
            "target_reason": (
                "O cenário já passou pelo gate principal; agora a próxima ação é enfileirar a primeira run."
                if studio_status == "ready"
                else "A fila ainda não deve virar o foco principal enquanto o Studio segue bloqueado."
            ),
        }
    if space == "decision":
        if not decision_candidate_id:
            return {
                "flow_label": "Decisão ainda depende de Runs",
                "flow_text": decision_state["headline"],
                "target_space": "runs",
                "target_label": "Voltar para Runs",
                "target_reason": "Sem execução utilizável, a próxima ação continua sendo recuperar contexto em Runs.",
            }
        if decision_summary.get("feasible") is False:
            return {
                "flow_label": "Winner bloqueado",
                "flow_text": decision_state["headline"],
                "target_space": "runs",
                "target_label": "Voltar para Runs",
                "target_reason": "A leitura principal segue travada; vale rever a execução antes de aprofundar a trilha técnica.",
            }
        if str(decision_summary.get("decision_status") or "").strip().lower() == "technical_tie" or bool(decision_summary.get("technical_tie")):
            return {
                "flow_label": "Comparação ainda em aberto",
                "flow_text": decision_state["headline"],
                "target_space": "decision",
                "target_label": "Manter comparação aberta",
                "target_reason": "O próximo passo continua sendo comparar winner e runner-up antes de chamar Auditoria.",
            }
        return {
            "flow_label": "Decisão principal legível",
            "flow_text": decision_state["headline"],
            "target_space": "audit",
            "target_label": "Abrir Auditoria só se precisar",
            "target_reason": "A trilha técnica continua secundária e só deve entrar quando a leitura principal não bastar.",
        }
    if decision_candidate_id:
        return {
            "flow_label": "Auditoria em modo de apoio",
            "flow_text": "A decisão principal já está legível; esta área segue como reconciliação técnica sob demanda.",
            "target_space": "decision",
            "target_label": "Voltar para Decisão",
            "target_reason": "Retorne para a leitura principal assim que a evidência técnica necessária estiver reconciliada.",
        }
    if studio_status != "ready":
        return {
            "flow_label": "Auditoria não substitui o Studio",
            "flow_text": "O cenário ainda depende do canvas principal para fechar readiness.",
            "target_space": "studio",
            "target_label": "Voltar ao Studio",
            "target_reason": "Use Auditoria apenas como trilha de apoio; a próxima ação real continua no Studio.",
        }
    return {
        "flow_label": "Auditoria não substitui Runs",
        "flow_text": "Sem decisão utilizável, esta área continua secundária diante da fila e da execução.",
        "target_space": "runs",
        "target_label": "Voltar para Runs",
        "target_reason": "A próxima leitura principal ainda depende de run utilizável ou histórico operacional.",
    }


def _journey_space_card(
    *,
    space: str,
    title: str,
    active_tab: str | None,
    studio_summary: dict[str, Any],
    run_summary: dict[str, Any],
    decision_summary: dict[str, Any],
) -> Any:
    state = _journey_space_state(space, studio_summary, run_summary, decision_summary)
    guidance = _space_transition_guidance(space, studio_summary, run_summary, decision_summary)
    is_active = str(active_tab or "studio") == space
    card_style = UI_JOURNEY_CARD_ACTIVE_STYLE if is_active else UI_JOURNEY_CARD_STYLE
    muted_color = "#d9ece5" if is_active else "#5b756d"
    return html.Div(
        id=f"product-journey-card-{space}",
        style=card_style,
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "gap": "10px", "alignItems": "center", "flexWrap": "wrap"},
                children=[
                    html.Div(title, style={"fontSize": "18px", "fontWeight": 700}),
                    _journey_card_status_pill("Espaço ativo" if is_active else "Espaço principal", active=is_active),
                ],
            ),
            html.Div(state["purpose"], style={"lineHeight": "1.5", "color": muted_color if is_active else "#496158"}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "gridTemplateColumns": "1fr", "gap": "8px"},
                children=[
                    _guidance_card("Estado atual", state["state_label"]),
                    _guidance_card("Próxima ação", state["next_action"]),
                    _guidance_card("Transição sugerida", guidance["target_reason"]),
                ],
            ),
            _button_link(
                guidance["target_label"],
                f"?tab={guidance['target_space']}",
                f"product-journey-open-{space}-link",
                primary=is_active,
            ),
        ],
    )


def render_product_journey_panel(
    active_tab: str | None,
    studio_summary: dict[str, Any],
    run_summary: dict[str, Any],
    decision_summary: dict[str, Any],
) -> Any:
    return html.Details(
        open=False,
        children=[
            html.Summary("Jornada principal completa"),
            html.Div(
                "Escolha a próxima área pelo estado do produto",
                style={"fontSize": "13px", "fontWeight": 700, "marginTop": "10px", "color": "#35524a"},
            ),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))", "gap": "12px", "marginTop": "12px"},
                children=[
                    _journey_space_card(
                        space="studio",
                        title="Studio",
                        active_tab=active_tab,
                        studio_summary=studio_summary,
                        run_summary=run_summary,
                        decision_summary=decision_summary,
                    ),
                    _journey_space_card(
                        space="runs",
                        title="Runs",
                        active_tab=active_tab,
                        studio_summary=studio_summary,
                        run_summary=run_summary,
                        decision_summary=decision_summary,
                    ),
                    _journey_space_card(
                        space="decision",
                        title="Decisão",
                        active_tab=active_tab,
                        studio_summary=studio_summary,
                        run_summary=run_summary,
                        decision_summary=decision_summary,
                    ),
                    _journey_space_card(
                        space="audit",
                        title="Auditoria",
                        active_tab=active_tab,
                        studio_summary=studio_summary,
                        run_summary=run_summary,
                        decision_summary=decision_summary,
                    ),
                ],
            ),
        ]
    )


def render_product_space_banner(
    space: str | None,
    studio_summary: dict[str, Any] | None = None,
    run_summary: dict[str, Any] | None = None,
    decision_summary: dict[str, Any] | None = None,
) -> Any:
    normalized = str(space or "studio").strip().lower()
    content = _product_space_content(normalized)
    guidance = _space_transition_guidance(normalized, studio_summary or {}, run_summary or {}, decision_summary or {})
    return html.Div(
        children=[
            html.Div(
                style={"display": "flex", "justifyContent": "space-between", "gap": "12px", "alignItems": "center", "flexWrap": "wrap"},
                children=[
                    html.Div(
                        children=[
                            html.Div("Espaço ativo", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#47665d"}),
                            html.H2(content["label"], style={"margin": "6px 0 4px"}),
                            html.Div(content["headline"], style={"fontWeight": 700, "lineHeight": "1.4"}),
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Div("Trocar espaço", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#47665d", "marginBottom": "8px"}),
                            html.Div(
                                style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                                children=[
                                    _space_switcher_link("Studio", "studio", normalized),
                                    _space_switcher_link("Runs", "runs", normalized),
                                    _space_switcher_link("Decisão", "decision", normalized),
                                    _space_switcher_link("Auditoria", "audit", normalized),
                                ],
                            ),
                        ]
                    ),
                ],
            ),
            html.Div(
                style={**UI_COMPACT_BANNER_CARD_STYLE, "marginTop": "10px"},
                children=[
                    html.Div("O que esta área resolve", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(content["objective"], style={"fontWeight": 700, "lineHeight": "1.45", "marginTop": "6px"}),
                    html.Div("Estado do fluxo agora", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(f"{guidance['flow_label']}: {guidance['flow_text']}", style={"fontWeight": 700, "lineHeight": "1.45", "marginTop": "6px"}),
                    html.Div("Próximo destino sugerido", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d", "marginTop": "8px"}),
                    html.Div(f"{guidance['target_label']}: {guidance['target_reason']}", style={"lineHeight": "1.45", "marginTop": "6px", "color": "#496158"}),
                ],
            ),
        ]
    )


def _section_intro(title: str, description: str, *, state_hint: str | None = None, action_hint: str | None = None) -> Any:
    hint_children = []
    for label, text in [("Estado atual", state_hint), ("Próxima ação", action_hint)]:
        if not text:
            continue
        hint_children.append(
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "12px"},
                children=[
                    html.Div(label, style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(text, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                ],
            )
        )
    return html.Div(
        style=UI_CARD_STYLE,
        children=[
            html.Div(title, style={"fontSize": "12px", "letterSpacing": "0.12em", "textTransform": "uppercase", "color": "#47665d"}),
            html.H2(title, style={"margin": "8px 0 8px"}),
            html.P(description, style={"margin": 0, "lineHeight": "1.6"}),
            html.Div(style={**UI_TWO_COLUMN_STYLE, "marginTop": "14px"}, children=hint_children) if hint_children else html.Span(),
        ],
    )


def _field_block(label: str, field: Any) -> Any:
    return html.Div(
        style=UI_FIELD_BLOCK_STYLE,
        children=[
            html.Label(label, style={"fontSize": "13px", "fontWeight": 700}) if label else html.Span(),
            field,
        ],
    )


def _status_tone(status: str | None) -> tuple[str, str]:
    normalized = str(status or "").strip().lower()
    if normalized in {"completed", "ready", "idle", "winner_clear"}:
        return "#dff2e8", "#0f5132"
    if normalized in {"queued", "running", "active", "needs_attention", "technical_tie"}:
        return "#fff1cc", "#7a5a00"
    if normalized in {"failed", "error", "blocked", "canceled"}:
        return "#f9d8d4", "#8c2f1e"
    return "#e5ece9", "#24453c"


def render_status_banner(message: Any) -> Any:
    text = str(message or "").strip()
    if not text:
        text = "Sem alerta operacional no momento."
    background, color = _status_tone("ok" if "sem alerta" in text.lower() else ("error" if "error" in text.lower() else "needs_attention"))
    return html.Div(
        style={"padding": "12px 14px", "borderRadius": "14px", "background": background, "color": color, "fontWeight": 700},
        children=text,
    )


def _metric_card(label: str, value: Any, note: str | None = None) -> Any:
    return html.Div(
        style={**UI_MUTED_CARD_STYLE, "padding": "14px"},
        children=[
            html.Div(label, style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.08em", "color": "#5b756d"}),
            html.Div(str(value), style={"fontSize": "24px", "fontWeight": 700, "marginTop": "6px"}),
            html.Div(note or "", style={"fontSize": "13px", "lineHeight": "1.5", "marginTop": "4px", "color": "#496158"}),
        ],
    )


def _bullet_list(items: list[str], empty_label: str) -> Any:
    if not items:
        return html.Div(empty_label, style={"color": "#496158"})
    return html.Ul([html.Li(str(item)) for item in items], style={"margin": "8px 0 0 18px", "lineHeight": "1.6"})


def _label_value_list(items: list[tuple[str, Any]]) -> Any:
    return html.Ul(
        [html.Li([html.Span(f"{label}: ", style={"fontWeight": 700}), str(value or "-")]) for label, value in items],
        style={"margin": "8px 0 0 18px", "lineHeight": "1.6"},
    )


def _guided_empty_state(title: str, state_text: str, next_action: str) -> Any:
    return html.Div(
        children=[
            html.H3(title, style={"marginTop": 0}),
            html.Div(state_text, style={"lineHeight": "1.6"}),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(next_action, style={"lineHeight": "1.6", "fontWeight": 700}),
        ]
    )


def _humanize_infeasibility_reason(reason: Any) -> str:
    normalized = str(reason or "").strip()
    if not normalized:
        return "nenhum"
    reason_lookup = {
        "mandatory_route_failure": "uma rota obrigatória não conseguiu fechar com a configuração atual",
        "connectivity": "faltou conectividade para cumprir pelo menos uma rota obrigatória",
        "components": "faltaram componentes compatíveis para montar a alternativa",
        "measurement": "a rota exige medição direta, mas não há medição compatível disponível",
        "family_rules": "a alternativa viola regras estruturais da família topológica escolhida",
        "hydraulics": "a capacidade hidráulica ou de medição não sustenta a rota exigida",
        "fallback_not_allowed": "o caminho oficial Julia-only não ficou disponível para sustentar a execução requerida",
        "python_engine_fallback": "o caminho oficial Julia-only não ficou disponível e o fallback não é aceitável no fluxo oficial",
        "no_path": "não existe caminho conectado para atender a rota requerida",
        "no_pump_available": "não há bomba compatível disponível para a rota exigida",
        "measurement_required_without_compatible_meter": "a rota exige medição direta e não há medidor compatível disponível",
        "idle_pumps_not_allowed": "a alternativa deixa bombas ociosas em uma família que não aceita esse estado",
        "idle_meters_not_allowed": "a alternativa deixa medidores ociosos em uma família que não aceita esse estado",
        "insufficient_effective_capacity": "a capacidade efetiva ficou abaixo do necessário para cumprir a rota",
        "hydraulic_or_meter_infeasible": "as restrições hidráulicas ou de medição impediram fechar a alternativa",
        "quality_gate": "a alternativa falhou em um gate de qualidade obrigatório",
        "unknown": "há uma restrição estrutural sem classificação legível; revise a trilha técnica para detalhar",
    }
    if normalized.startswith("quality_rule:"):
        rule_id = normalized.split(":", 1)[1].strip() or "gate de qualidade"
        return f"a alternativa falhou em um gate de qualidade obrigatório ({rule_id})"
    return reason_lookup.get(
        normalized,
        "há uma restrição estrutural não traduzida na leitura de produto; revise a trilha técnica para detalhar",
    )


def _humanize_route_issue(reason: Any) -> str:
    normalized = str(reason or "").strip()
    if not normalized:
        return "sem motivo registrado"
    route_lookup = {
        "no_path": "sem caminho conectado",
        "no_pump_available": "sem bomba compatível disponível",
        "measurement_required_without_compatible_meter": "sem medição direta compatível",
        "idle_pumps_not_allowed": "família não aceita bombas ociosas nesta rota",
        "idle_meters_not_allowed": "família não aceita medidores ociosos nesta rota",
        "insufficient_effective_capacity": "capacidade efetiva abaixo do necessário",
        "hydraulic_or_meter_infeasible": "restrição hidráulica ou de medição",
    }
    return route_lookup.get(normalized, normalized)


def _humanize_readiness_status(status: Any) -> str:
    lookup = {
        "ready": "Pronto",
        "needs_attention": "Exige atenção",
        "blocked": "Bloqueado",
        "partial": "Parcial",
        "complete": "Completo",
        "degraded": "Degradado",
    }
    normalized = str(status or "").strip().lower()
    return lookup.get(normalized, normalized.replace("_", " ") or "-")


def _humanize_run_status(status: Any) -> str:
    lookup = {
        "idle": "Pronto",
        "queued": "Na fila",
        "running": "Em execução",
        "completed": "Concluída",
        "failed": "Falhou",
        "canceled": "Cancelada",
        "unknown": "Sem contexto",
    }
    normalized = str(status or "").strip().lower()
    return lookup.get(normalized, normalized.replace("_", " ") or "-")


def _humanize_audit_status(status: Any) -> str:
    lookup = {
        "idle": "Pronto",
        "saved": "Concluído",
        "persisted": "Concluído",
        "saving": "Em execução",
        "error": "Bloqueado",
        "failed": "Bloqueado",
        "unknown": "Sem contexto",
    }
    normalized = str(status or "").strip().lower()
    return lookup.get(normalized, normalized.replace("_", " ") or "-")


def _humanize_decision_status(status: Any) -> str:
    normalized = str(status or "").strip().lower()
    if normalized == "technical_tie":
        return "Empate técnico"
    if normalized == "winner_clear":
        return "Winner claro"
    return normalized.replace("_", " ") or "-"


def _decision_primary_state(summary: dict[str, Any]) -> dict[str, str]:
    candidate_id = str(summary.get("candidate_id") or "").strip()
    runner_up_id = str(summary.get("runner_up_candidate_id") or "").strip()
    decision_status = str(summary.get("decision_status") or ("technical_tie" if summary.get("technical_tie") else "winner_clear"))
    infeasibility_reason = _humanize_infeasibility_reason(summary.get("infeasibility_reason"))
    feasible_is_false = summary.get("feasible") is False
    if not candidate_id:
        return {
            "state_label": "Sem decisão utilizável",
            "headline": "Ainda falta uma run utilizável para abrir winner, runner-up e contraste com segurança.",
            "next_action": "Volte para Runs, confirme uma execução concluída e retorne quando existir resultado comparável.",
            "contrast_state": "Sem winner e runner-up legíveis nesta leitura.",
            "winner_guidance": "Nenhum candidato oficial apareceu a partir da execução atual.",
            "runner_up_guidance": "Sem runner-up comparável até existir uma run utilizável.",
        }
    if feasible_is_false:
        return {
            "state_label": "Winner inviável",
            "headline": "Existe um winner visível, mas ele ainda não pode ser oficializado na leitura principal.",
            "next_action": "Use o motivo de inviabilidade e o runner-up para decidir se vale revisar a run atual ou voltar ao cenário.",
            "contrast_state": "A escolha oficial segue bloqueada; trate o runner-up como referência comparativa, não como liberação automática.",
            "winner_guidance": f"{candidate_id} lidera o ranking atual, mas segue inviável porque {infeasibility_reason}.",
            "runner_up_guidance": (
                f"{runner_up_id} segue como melhor contraste enquanto o winner permanece bloqueado."
                if runner_up_id
                else "Ainda não existe runner-up comparável para apoiar a leitura do bloqueio."
            ),
        }
    if decision_status == "technical_tie":
        return {
            "state_label": "Empate técnico",
            "headline": "Winner e runner-up seguem próximos o suficiente para exigir decisão humana assistida.",
            "next_action": "Mantenha a comparação aberta, valide os sinais de risco e aprofunde a Auditoria apenas se precisar reconciliar a trilha técnica.",
            "contrast_state": "Empate técnico ativo; mantenha o runner-up visível antes de oficializar.",
            "winner_guidance": f"{candidate_id} ocupa a dianteira atual, mas ainda sem separação confortável para oficialização imediata.",
            "runner_up_guidance": (
                f"{runner_up_id} permanece próximo o suficiente para sustentar o empate técnico."
                if runner_up_id
                else "Ainda falta um runner-up legível para sustentar o empate técnico com honestidade."
            ),
        }
    return {
        "state_label": "Winner claro",
        "headline": "A execução atual já entrega um winner legível e um runner-up de referência para a decisão assistida.",
        "next_action": "Confirme o runner-up e os sinais de risco antes de oficializar; abra Auditoria só se precisar aprofundar evidências técnicas.",
        "contrast_state": "Winner claro; use o runner-up como contraste de referência antes de exportar.",
        "winner_guidance": f"{candidate_id} lidera a leitura atual com contraste suficiente para sustentar a escolha principal.",
        "runner_up_guidance": (
            f"{runner_up_id} segue como melhor alternativa comparável abaixo da escolha oficial."
            if runner_up_id
            else "Ainda não há runner-up comparável, então trate a oficialização com cautela adicional."
        ),
    }


def _coerce_float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _humanize_readiness_issue(issue: Any) -> str:
    text = str(issue or "").strip()
    if not text:
        return "Sem detalhe registrado."
    if " entra em W" in text:
        link_id = text.split(" entra em W", 1)[0]
        return f"A conexão {link_id} termina em W, mas W deve apenas iniciar fluxo."
    if " sai de S" in text:
        link_id = text.split(" sai de S", 1)[0]
        return f"A conexão {link_id} sai de S, mas S deve aparecer apenas como destino final."
    if text.startswith("Rotas com dosagem sem medicao direta:"):
        route_ids = text.split(":", 1)[1].strip()
        return f"Há rotas com dosagem sem medição direta compatível: {route_ids}."
    if " referencia source inexistente:" in text:
        route_id, source = text.split(" referencia source inexistente:", 1)
        return f"A rota {route_id} aponta para uma origem que não está disponível no cenário: {source.strip()}."
    if " referencia sink inexistente:" in text:
        route_id, sink = text.split(" referencia sink inexistente:", 1)
        return f"A rota {route_id} aponta para um destino que não está disponível no cenário: {sink.strip()}."
    if " ainda nao tem saida conectada a partir de " in text:
        route_id, source = text.split(" ainda nao tem saida conectada a partir de ", 1)
        return f"A rota {route_id} ainda não encontrou uma saída conectada a partir de {source.strip()}."
    if " ainda nao tem entrada conectada em " in text:
        route_id, sink = text.split(" ainda nao tem entrada conectada em ", 1)
        return f"A rota {route_id} ainda não encontrou uma entrada conectada em {sink.strip()}."
    if text.startswith("Nos sem conexao no grafo visivel:"):
        node_ids = text.split(":", 1)[1].strip()
        return f"Ainda existem entidades sem conexão na leitura principal do grafo: {node_ids}."
    return text


def _guided_empty_state(title: str, headline: str, next_action: str, *, tone: str = "needs_attention") -> Any:
    background, color = _status_tone(tone)
    return html.Div(
        children=[
            html.H3(title, style={"marginTop": 0}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 14px", "flexWrap": "wrap"},
                children=[
                    html.Span("Aguardando contexto", style={"padding": "6px 10px", "borderRadius": "999px", "background": background, "color": color, "fontWeight": 700}),
                    html.Span(headline, style={"fontWeight": 700, "lineHeight": "1.5"}),
                ],
            ),
            html.H4("Próxima ação", style={"marginBottom": "6px"}),
            html.Div(next_action, style={"lineHeight": "1.6", "fontWeight": 700}),
        ],
    )


def _coerce_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    return normalized in {"1", "true", "yes", "y"}


def _timestamp_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _primary_tab_from_search(search: str | None, default: str = "studio") -> str:
    if not search:
        return default
    params = parse_qs(str(search).lstrip("?"))
    candidate = str((params.get("tab") or [default])[0]).strip().lower()
    if candidate in {"studio", "runs", "decision", "audit"}:
        return candidate
    return default


NODE_TYPE_LABELS = {
    "water_tank": "Tanque de água",
    "product_tank": "Tanque de produto",
    "mixer_tank": "Misturador",
    "incorporator_tank": "Incorporador",
    "external_outlet": "Saída externa",
    "service_return": "Retorno de serviço",
    "junction": "Junção operacional",
}
EDGE_ARCHETYPE_LABELS = {
    "tank_tap": "Tomada de tanque",
    "service_tap": "Tomada de serviço",
    "supply_tap": "Entrada de água",
    "outlet_tap": "Saída do circuito",
    "bus_segment": "Trecho do barramento",
    "pump_island_segment": "Trecho com ilha de bomba",
    "upper_bypass_segment": "Trecho do bypass superior",
    "vertical_link": "Conexão vertical",
}
BUSINESS_NODE_PRESETS = {
    "source": {
        "button_label": "Nova fonte",
        "button_hint": "Entrada de água visível no Studio.",
        "node_id_prefix": "SOURCE",
        "node_type": "water_tank",
        "default_label": "Nova fonte",
        "zone": "supply",
        "allow_inbound": False,
        "allow_outbound": True,
        "requires_mixing_service": False,
    },
    "product": {
        "button_label": "Novo produto",
        "button_hint": "Tanque ou ponto de produto de negócio.",
        "node_id_prefix": "PRODUCT",
        "node_type": "product_tank",
        "default_label": "Novo produto",
        "zone": "process",
        "allow_inbound": True,
        "allow_outbound": True,
        "requires_mixing_service": False,
    },
    "mixer": {
        "button_label": "Novo misturador",
        "button_hint": "Etapa principal de mistura no fluxo.",
        "node_id_prefix": "MIX",
        "node_type": "mixer_tank",
        "default_label": "Novo misturador",
        "zone": "process",
        "allow_inbound": True,
        "allow_outbound": True,
        "requires_mixing_service": False,
    },
    "service": {
        "button_label": "Novo serviço",
        "button_hint": "Ponto de serviço ou incorporador visível.",
        "node_id_prefix": "SERVICE",
        "node_type": "incorporator_tank",
        "default_label": "Novo serviço",
        "zone": "service",
        "allow_inbound": True,
        "allow_outbound": True,
        "requires_mixing_service": True,
    },
    "outlet": {
        "button_label": "Nova saída",
        "button_hint": "Saída externa ou entrega principal.",
        "node_id_prefix": "OUTLET",
        "node_type": "external_outlet",
        "default_label": "Nova saída",
        "zone": "outlet",
        "allow_inbound": True,
        "allow_outbound": False,
        "requires_mixing_service": False,
    },
}
BUSINESS_EDGE_ARCHETYPE_OPTIONS = [
    {"label": "Entrada de água", "value": "supply_tap"},
    {"label": "Tomada de tanque", "value": "tank_tap"},
    {"label": "Tomada de serviço", "value": "service_tap"},
    {"label": "Trecho do barramento", "value": "bus_segment"},
    {"label": "Trecho com ilha de bomba", "value": "pump_island_segment"},
    {"label": "Conexão vertical", "value": "vertical_link"},
    {"label": "Saída do circuito", "value": "outlet_tap"},
]
STUDIO_CONTEXT_MENU = [
    {
        "id": "add-source-node",
        "label": "Adicionar fonte aqui",
        "availableOn": ["canvas"],
        "tooltipText": "Cria uma fonte de água visível no Studio exatamente neste ponto.",
    },
    {
        "id": "add-product-node",
        "label": "Adicionar produto aqui",
        "availableOn": ["canvas"],
        "tooltipText": "Cria um tanque de produto na posição clicada.",
    },
    {
        "id": "add-mixer-node",
        "label": "Adicionar misturador aqui",
        "availableOn": ["canvas"],
        "tooltipText": "Cria uma etapa de mistura na posição clicada.",
    },
    {
        "id": "add-service-node",
        "label": "Adicionar serviço aqui",
        "availableOn": ["canvas"],
        "tooltipText": "Cria um ponto de serviço visível na posição clicada.",
    },
    {
        "id": "add-outlet-node",
        "label": "Adicionar saída aqui",
        "availableOn": ["canvas"],
        "tooltipText": "Cria uma saída principal na posição clicada.",
    },
    {
        "id": "duplicate-node",
        "label": "Duplicar entidade",
        "availableOn": ["node"],
        "tooltipText": "Duplica a entidade selecionada mantendo-a no canvas principal.",
    },
    {
        "id": "start-route-from-node",
        "label": "Iniciar rota daqui",
        "availableOn": ["node"],
        "tooltipText": "Marca esta entidade como origem da próxima rota criada direto no canvas.",
    },
    {
        "id": "remove-node",
        "label": "Remover entidade",
        "availableOn": ["node"],
        "tooltipText": "Tenta remover a entidade selecionada da malha principal.",
    },
    {
        "id": "create-route-from-edge",
        "label": "Criar rota deste trecho",
        "availableOn": ["edge"],
        "tooltipText": "Cria uma rota de negócio usando a conexão selecionada como origem e destino visíveis.",
    },
    {
        "id": "mark-route-mandatory",
        "label": "Marcar rota como obrigatória",
        "availableOn": ["edge"],
        "tooltipText": "Promove a rota ligada a este trecho para obrigatória sem abrir o workbench.",
    },
    {
        "id": "mark-route-desirable",
        "label": "Marcar rota como desejável",
        "availableOn": ["edge"],
        "tooltipText": "Marca a rota ligada a este trecho como desejável sem endurecer a constraint.",
    },
    {
        "id": "mark-route-optional",
        "label": "Marcar rota como opcional",
        "availableOn": ["edge"],
        "tooltipText": "Mantém a rota ligada a este trecho como opcional na leitura principal.",
    },
    {
        "id": "reverse-edge",
        "label": "Inverter direção",
        "availableOn": ["edge"],
        "tooltipText": "Inverte a direção da conexão selecionada sem abrir a bancada avançada.",
    },
    {
        "id": "remove-edge",
        "label": "Remover conexão",
        "availableOn": ["edge"],
        "tooltipText": "Remove a conexão selecionada da superfície principal.",
    },
    {
        "id": "open-workbench",
        "label": "Abrir workbench avançado",
        "availableOn": ["node", "edge", "canvas"],
        "tooltipText": "Abre a bancada avançada sem recolocar a trilha técnica na primeira dobra.",
    },
]


def _studio_node_business_label(row: dict[str, Any] | None) -> str:
    if not row:
        return "-"
    label = str(row.get("label", "")).strip()
    node_id = str(row.get("node_id", "")).strip()
    return label or node_id or "Entidade sem rótulo"


def _studio_node_role_label(row: dict[str, Any] | None) -> str:
    if not row:
        return "Entidade"
    return NODE_TYPE_LABELS.get(str(row.get("node_type", "")).strip(), "Entidade do cenário")


def _studio_edge_role_label(row: dict[str, Any] | None) -> str:
    if not row:
        return "Conexão"
    return EDGE_ARCHETYPE_LABELS.get(str(row.get("archetype", "")).strip(), "Conexão do cenário")


def _business_node_choice_options(nodes_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    options = []
    for row in _visible_studio_nodes(nodes_rows):
        node_id = str(row.get("node_id", "")).strip()
        if not node_id:
            continue
        options.append(
            {
                "label": f"{_studio_node_business_label(row)} ({_studio_node_role_label(row)})",
                "value": node_id,
            }
        )
    return options


def _studio_quick_link_defaults(
    nodes_rows: list[dict[str, Any]],
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
) -> tuple[str | None, str | None]:
    options = [option["value"] for option in _business_node_choice_options(nodes_rows)]
    if len(options) < 2:
        return None, None
    preferred_source = str(node_summary.get("selected_node_id") or edge_summary.get("selected_edge", {}).get("from_node") or "").strip()
    preferred_target = str(edge_summary.get("selected_edge", {}).get("to_node") or "").strip()
    source = preferred_source if preferred_source in options else options[0]
    target_candidates = [candidate for candidate in options if candidate != source]
    if preferred_target in target_candidates:
        target = preferred_target
    else:
        target = target_candidates[0] if target_candidates else None
    return source, target


def _is_internal_studio_node(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    if str(row.get("node_type", "")).strip() == "junction":
        return True
    zone = str(row.get("zone", "")).strip().lower()
    if zone in {"internal", "hub"}:
        return True
    if bool(row.get("is_candidate_hub")):
        return True
    labels = " ".join(
        str(row.get(field, "")).strip().lower()
        for field in ("node_id", "label", "notes")
    )
    return "hub" in labels and str(row.get("node_type", "")).strip() == "junction"


def _visible_studio_nodes(nodes_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in nodes_rows if not _is_internal_studio_node(row)]


def _visible_studio_node_ids(nodes_rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row.get("node_id", "")).strip()
        for row in _visible_studio_nodes(nodes_rows)
        if str(row.get("node_id", "")).strip()
    }


def _visible_studio_edges(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    visible_node_ids = _visible_studio_node_ids(nodes_rows)
    visible_edges: list[dict[str, Any]] = []
    for row in candidate_links_rows:
        source = str(row.get("from_node", "")).strip()
        target = str(row.get("to_node", "")).strip()
        if source in visible_node_ids and target in visible_node_ids:
            visible_edges.append(dict(row))
    return visible_edges


def _humanize_label_list(items: list[str]) -> str:
    unique_items = list(
        dict.fromkeys(
            str(item).strip()
            for item in items
            if str(item).strip()
        )
    )
    if not unique_items:
        return ""
    if len(unique_items) == 1:
        return unique_items[0]
    if len(unique_items) == 2:
        return f"{unique_items[0]} e {unique_items[1]}"
    if len(unique_items) == 3:
        return f"{unique_items[0]}, {unique_items[1]} e {unique_items[2]}"
    return f"{unique_items[0]}, {unique_items[1]}, {unique_items[2]} e mais {len(unique_items) - 3}"


def _route_intent_value(route: dict[str, Any] | None) -> str:
    if _coerce_truthy((route or {}).get("mandatory")):
        return "mandatory"
    route_group = str((route or {}).get("route_group", "")).strip().lower()
    if route_group == "desirable":
        return "desirable"
    return "optional"


def _route_intent_label(intent: Any) -> str:
    normalized = str(intent or "optional").strip().lower()
    lookup = {
        "mandatory": "Obrigatória",
        "optional": "Opcional",
        "desirable": "Desejável",
    }
    return lookup.get(normalized, "Opcional")


def _route_intent_badge_style(intent: Any) -> dict[str, Any]:
    normalized = str(intent or "optional").strip().lower()
    background = "#e2e8f0"
    color = "#334155"
    if normalized == "mandatory":
        background = "#d1fae5"
        color = "#065f46"
    elif normalized == "desirable":
        background = "#fef3c7"
        color = "#92400e"
    return {
        "display": "inline-flex",
        "alignItems": "center",
        "padding": "6px 10px",
        "borderRadius": "999px",
        "fontSize": "12px",
        "fontWeight": 700,
        "background": background,
        "color": color,
    }


def _route_focus_rows(
    route_rows: list[dict[str, Any]] | None,
    *,
    focus_node_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    normalized_routes = [dict(route) for route in (route_rows or [])]
    normalized_focus = {
        str(node_id).strip()
        for node_id in (focus_node_ids or set())
        if str(node_id).strip()
    }
    if normalized_focus:
        filtered_routes = [
            route
            for route in normalized_routes
            if str(route.get("source") or "").strip() in normalized_focus
            or str(route.get("sink") or "").strip() in normalized_focus
        ]
        if filtered_routes:
            normalized_routes = filtered_routes
    return sorted(
        normalized_routes,
        key=lambda route: (
            0 if _route_intent_value(route) == "mandatory" else (1 if _route_intent_value(route) == "desirable" else 2),
            -float(route.get("weight") or 0.0),
            str(route.get("route_id") or ""),
        ),
    )


def _route_choice_options(
    route_rows: list[dict[str, Any]] | None,
    *,
    focus_node_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for route in _route_focus_rows(route_rows, focus_node_ids=focus_node_ids):
        route_id = str(route.get("route_id") or "").strip()
        if not route_id:
            continue
        source = str(route.get("source") or "-").strip() or "-"
        sink = str(route.get("sink") or "-").strip() or "-"
        label = f"{route_id} · {source} -> {sink} · {_route_intent_label(_route_intent_value(route))}"
        options.append({"label": label, "value": route_id})
    return options


def _default_route_focus_selection(
    route_rows: list[dict[str, Any]] | None,
    *,
    focus_node_ids: set[str] | None = None,
    preferred_route_id: str | None = None,
) -> str | None:
    preferred = str(preferred_route_id or "").strip()
    options = _route_choice_options(route_rows, focus_node_ids=focus_node_ids)
    option_values = [str(option["value"]) for option in options]
    if preferred and preferred in option_values:
        return preferred
    return option_values[0] if option_values else None


def _route_studio_form_values(
    route_rows: list[dict[str, Any]] | None,
    *,
    focus_node_ids: set[str] | None = None,
    selected_route_id: str | None = None,
) -> dict[str, Any]:
    selected_id = _default_route_focus_selection(
        route_rows,
        focus_node_ids=focus_node_ids,
        preferred_route_id=selected_route_id,
    )
    selected_row = next(
        (
            dict(route)
            for route in (route_rows or [])
            if str(route.get("route_id") or "").strip() == selected_id
        ),
        None,
    )
    if selected_row is None:
        return {
            "route_id": None,
            "intent": "optional",
            "measurement_required": [],
            "dose_min_l": None,
            "q_min_delivered_lpm": None,
            "notes": "",
            "source": "",
            "sink": "",
        }
    return {
        "route_id": selected_id,
        "intent": _route_intent_value(selected_row),
        "measurement_required": ["measurement_required"] if _coerce_truthy(selected_row.get("measurement_required")) else [],
        "dose_min_l": float(selected_row.get("dose_min_l") or 0.0),
        "q_min_delivered_lpm": float(selected_row.get("q_min_delivered_lpm") or 0.0),
        "notes": str(selected_row.get("notes") or "").strip(),
        "source": str(selected_row.get("source") or "").strip(),
        "sink": str(selected_row.get("sink") or "").strip(),
    }


def apply_route_studio_edit(
    route_rows: list[dict[str, Any]],
    *,
    selected_route_id: str | None,
    intent: str | None,
    measurement_required: bool,
    dose_min_l: Any,
    q_min_delivered_lpm: Any,
    notes: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_route_focus_selection(route_rows, preferred_route_id=selected_route_id)
    if not selected_id:
        raise ValueError("Selecione uma rota antes de aplicar a edição local.")
    normalized_intent = str(intent or "optional").strip().lower()
    if normalized_intent not in {"mandatory", "optional", "desirable"}:
        raise ValueError(f"Intento de rota desconhecido: {intent}")
    updated_rows: list[dict[str, Any]] = []
    for row in route_rows:
        current = dict(row)
        if str(current.get("route_id") or "").strip() != selected_id:
            updated_rows.append(current)
            continue
        current["mandatory"] = 1 if normalized_intent == "mandatory" else 0
        current["route_group"] = "desirable" if normalized_intent == "desirable" else ("core" if normalized_intent == "mandatory" else "optional")
        current["measurement_required"] = 1 if measurement_required else 0
        current["dose_min_l"] = float(dose_min_l or 0.0)
        current["q_min_delivered_lpm"] = float(q_min_delivered_lpm or 0.0)
        current["notes"] = str(notes or "").strip()
        updated_rows.append(current)
    return updated_rows, selected_id


def _next_route_identifier(route_rows: list[dict[str, Any]]) -> str:
    numeric_suffixes: list[int] = []
    existing_ids = {
        str(row.get("route_id") or "").strip()
        for row in route_rows
        if str(row.get("route_id") or "").strip()
    }
    for route_id in existing_ids:
        if route_id.startswith("R") and route_id[1:].isdigit():
            numeric_suffixes.append(int(route_id[1:]))
    next_number = max(numeric_suffixes, default=0) + 1
    candidate = f"R{next_number:03d}"
    while candidate in existing_ids:
        next_number += 1
        candidate = f"R{next_number:03d}"
    return candidate


def _route_ids_for_edge_context(
    route_rows: list[dict[str, Any]],
    *,
    edge_row: dict[str, Any] | None,
) -> list[str]:
    if not edge_row:
        return []
    from_node = str(edge_row.get("from_node") or "").strip()
    to_node = str(edge_row.get("to_node") or "").strip()
    route_ids = [
        str(route.get("route_id") or "").strip()
        for route in route_rows
        if str(route.get("source") or "").strip() == from_node
        and str(route.get("sink") or "").strip() == to_node
    ]
    return [route_id for route_id in route_ids if route_id]


def create_route_from_edge_studio_selection(
    route_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
    candidate_links_rows: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], str]:
    selected_id = _default_edge_studio_selection(candidate_links_rows or [], preferred_link_id=selected_link_id)
    edge_row = next(
        (
            dict(row)
            for row in (candidate_links_rows or [])
            if str(row.get("link_id") or "").strip() == selected_id
        ),
        None,
    )
    if edge_row is None:
        raise ValueError("Selecione uma conexão visível antes de criar uma rota.")
    existing_route_ids = _route_ids_for_edge_context(route_rows, edge_row=edge_row)
    if existing_route_ids:
        raise ValueError(
            "Este trecho já possui rota registrada no Studio: "
            + ", ".join(existing_route_ids[:3])
        )
    from_node = str(edge_row.get("from_node") or "").strip()
    to_node = str(edge_row.get("to_node") or "").strip()
    if not from_node or not to_node:
        raise ValueError("A conexão selecionada não possui origem e destino válidos para criar uma rota.")
    next_route_id = _next_route_identifier(route_rows)
    new_row = {
        "route_id": next_route_id,
        "source": from_node,
        "sink": to_node,
        "mandatory": 0,
        "route_group": "optional",
        "q_min_delivered_lpm": 10.0,
        "measurement_required": 0,
        "dose_min_l": 0.0,
        "dose_error_max_pct": 0.0,
        "cleaning_required": 1,
        "allow_series_pumps": 1,
        "weight": 5.0,
        "notes": f"Rota criada no canvas: {from_node} -> {to_node}",
    }
    return [*route_rows, new_row], next_route_id


def create_route_between_business_nodes(
    route_rows: list[dict[str, Any]],
    *,
    source_node_id: str,
    sink_node_id: str,
) -> tuple[list[dict[str, Any]], str]:
    normalized_source = str(source_node_id or "").strip()
    normalized_sink = str(sink_node_id or "").strip()
    if not normalized_source or not normalized_sink:
        raise ValueError("Selecione origem e destino de negócio antes de criar a rota.")
    if normalized_source == normalized_sink:
        raise ValueError("A rota no Studio precisa ligar duas entidades de negócio diferentes.")
    duplicate_route_id = next(
        (
            str(route.get("route_id") or "").strip()
            for route in route_rows
            if str(route.get("source") or "").strip() == normalized_source
            and str(route.get("sink") or "").strip() == normalized_sink
        ),
        "",
    )
    if duplicate_route_id:
        raise ValueError(f"Já existe uma rota registrada entre {normalized_source} e {normalized_sink}: {duplicate_route_id}")
    next_route_id = _next_route_identifier(route_rows)
    new_row = {
        "route_id": next_route_id,
        "source": normalized_source,
        "sink": normalized_sink,
        "mandatory": 0,
        "route_group": "optional",
        "q_min_delivered_lpm": 10.0,
        "measurement_required": 0,
        "dose_min_l": 0.0,
        "dose_error_max_pct": 0.0,
        "cleaning_required": 1,
        "allow_series_pumps": 1,
        "weight": 5.0,
        "notes": f"Rota criada no canvas: {normalized_source} -> {normalized_sink}",
    }
    return [*route_rows, new_row], next_route_id


def apply_route_intent_from_edge_context(
    route_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
    candidate_links_rows: list[dict[str, Any]] | None,
    intent: str,
) -> tuple[list[dict[str, Any]], str]:
    selected_id = _default_edge_studio_selection(candidate_links_rows or [], preferred_link_id=selected_link_id)
    edge_row = next(
        (
            dict(row)
            for row in (candidate_links_rows or [])
            if str(row.get("link_id") or "").strip() == selected_id
        ),
        None,
    )
    route_ids = _route_ids_for_edge_context(route_rows, edge_row=edge_row)
    if not route_ids:
        raise ValueError("Este trecho ainda não possui rota registrada. Crie a rota primeiro no canvas.")
    return apply_route_studio_edit(
        route_rows,
        selected_route_id=route_ids[0],
        intent=intent,
        measurement_required=bool(
            next(
                (
                    route.get("measurement_required")
                    for route in route_rows
                    if str(route.get("route_id") or "").strip() == route_ids[0]
                ),
                False,
            )
        ),
        dose_min_l=next(
            (
                route.get("dose_min_l")
                for route in route_rows
                if str(route.get("route_id") or "").strip() == route_ids[0]
            ),
            0.0,
        ),
        q_min_delivered_lpm=next(
            (
                route.get("q_min_delivered_lpm")
                for route in route_rows
                if str(route.get("route_id") or "").strip() == route_ids[0]
            ),
            0.0,
        ),
        notes=next(
            (
                route.get("notes")
                for route in route_rows
                if str(route.get("route_id") or "").strip() == route_ids[0]
            ),
            "",
        ),
    )


def _primary_route_projection_rows(
    nodes_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    node_lookup = {
        str(row.get("node_id", "")).strip(): dict(row)
        for row in _visible_studio_nodes(nodes_rows)
        if str(row.get("node_id", "")).strip()
    }
    projected_rows: list[dict[str, Any]] = []
    for route in route_rows or []:
        source = str(route.get("source", "")).strip()
        sink = str(route.get("sink", "")).strip()
        route_id = str(route.get("route_id", "")).strip()
        if not route_id or source not in node_lookup or sink not in node_lookup or source == sink:
            continue
        projected_rows.append(
            {
                "projection_id": f"route:{route_id}",
                "route_id": route_id,
                "source": source,
                "target": sink,
                "label": str(route.get("notes", "")).strip() or f"{_studio_node_business_label(node_lookup[source])} -> {_studio_node_business_label(node_lookup[sink])}",
                "route_group": str(route.get("route_group", "")).strip() or "core",
                "intent": _route_intent_value(route),
                "mandatory": bool(route.get("mandatory")),
                "measurement_required": _coerce_truthy(route.get("measurement_required")),
                "q_min_delivered_lpm": float(route.get("q_min_delivered_lpm") or 0.0),
                "notes": str(route.get("notes", "")).strip(),
            }
        )
    return projected_rows


def _studio_edge_business_label(
    row: dict[str, Any] | None,
    node_lookup: dict[str, dict[str, Any]],
) -> str:
    if not row:
        return "-"
    notes = str(row.get("notes", "")).strip()
    if notes:
        return notes
    source = _studio_node_business_label(node_lookup.get(str(row.get("from_node", "")).strip()))
    target = _studio_node_business_label(node_lookup.get(str(row.get("to_node", "")).strip()))
    if source != "-" and target != "-":
        return f"{source} -> {target}"
    family_hint = str(row.get("family_hint", "")).strip()
    if family_hint:
        return family_hint.split(",")[0].strip() or "Conexão do cenário"
    return _studio_edge_role_label(row)


def build_studio_business_flow_summary(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]] | None,
    focus_node_ids: set[str] | None = None,
) -> dict[str, Any]:
    visible_nodes = _visible_studio_nodes(nodes_rows)
    node_lookup = {
        str(row.get("node_id", "")).strip(): dict(row)
        for row in visible_nodes
        if str(row.get("node_id", "")).strip()
    }
    relation_map: dict[tuple[str, str], dict[str, Any]] = {}

    def register_relation(
        source: str,
        target: str,
        *,
        route_id: str = "",
        mandatory: bool = False,
    ) -> None:
        source = str(source).strip()
        target = str(target).strip()
        if source not in node_lookup or target not in node_lookup or source == target:
            return
        relation = relation_map.setdefault(
            (source, target),
            {
                "source": source,
                "target": target,
                "route_ids": [],
                "mandatory": False,
            },
        )
        if route_id and route_id not in relation["route_ids"]:
            relation["route_ids"].append(route_id)
        relation["mandatory"] = relation["mandatory"] or mandatory

    for row in _visible_studio_edges(nodes_rows, candidate_links_rows):
        register_relation(
            str(row.get("from_node", "")).strip(),
            str(row.get("to_node", "")).strip(),
        )
    for route in _primary_route_projection_rows(nodes_rows, route_rows):
        register_relation(
            str(route.get("source", "")).strip(),
            str(route.get("target", "")).strip(),
            route_id=str(route.get("route_id", "")).strip(),
            mandatory=bool(route.get("mandatory")),
        )

    inbound_by_node: dict[str, set[str]] = {node_id: set() for node_id in node_lookup}
    outbound_by_node: dict[str, set[str]] = {node_id: set() for node_id in node_lookup}
    connection_lines: list[str] = []
    for relation in relation_map.values():
        source = relation["source"]
        target = relation["target"]
        inbound_by_node[target].add(source)
        outbound_by_node[source].add(target)
        source_label = _studio_node_business_label(node_lookup.get(source))
        target_label = _studio_node_business_label(node_lookup.get(target))
        qualifiers: list[str] = []
        if relation["mandatory"]:
            qualifiers.append("rota obrigatória")
        if relation["route_ids"]:
            qualifiers.append("rotas " + ", ".join(relation["route_ids"][:2]))
        qualifier_text = f" ({', '.join(qualifiers)})" if qualifiers else ""
        connection_lines.append(f"{source_label} supre {target_label}{qualifier_text}.")

    normalized_focus_node_ids = {
        str(node_id).strip()
        for node_id in (focus_node_ids or set())
        if str(node_id).strip() in node_lookup
    }
    focus_labels = [_studio_node_business_label(node_lookup.get(node_id)) for node_id in sorted(normalized_focus_node_ids)]
    supplied_by_labels = sorted(
        {
            _studio_node_business_label(node_lookup.get(source))
            for node_id in normalized_focus_node_ids
            for source in inbound_by_node.get(node_id, set())
            if source not in normalized_focus_node_ids
        }
    )
    supplies_labels = sorted(
        {
            _studio_node_business_label(node_lookup.get(target))
            for node_id in normalized_focus_node_ids
            for target in outbound_by_node.get(node_id, set())
            if target not in normalized_focus_node_ids
        }
    )
    focus_connection_lines = [
        line
        for relation, line in zip(relation_map.values(), connection_lines)
        if relation["source"] in normalized_focus_node_ids or relation["target"] in normalized_focus_node_ids
    ]
    source_labels = sorted(
        _studio_node_business_label(node_lookup.get(node_id))
        for node_id in node_lookup
        if outbound_by_node.get(node_id) and not inbound_by_node.get(node_id)
    )
    sink_labels = sorted(
        _studio_node_business_label(node_lookup.get(node_id))
        for node_id in node_lookup
        if inbound_by_node.get(node_id) and not outbound_by_node.get(node_id)
    )
    orphan_labels = sorted(
        _studio_node_business_label(node_lookup.get(node_id))
        for node_id in node_lookup
        if not inbound_by_node.get(node_id) and not outbound_by_node.get(node_id)
    )
    if normalized_focus_node_ids:
        focus_display = _humanize_label_list(focus_labels)
        if supplied_by_labels and supplies_labels:
            headline = f"{focus_display} é suprido por {_humanize_label_list(supplied_by_labels)} e supre {_humanize_label_list(supplies_labels)}."
        elif supplied_by_labels:
            headline = f"{focus_display} é suprido por {_humanize_label_list(supplied_by_labels)}."
        elif supplies_labels:
            headline = f"{focus_display} supre {_humanize_label_list(supplies_labels)}."
        else:
            headline = f"{focus_display} ainda não participa de um trecho visível de suprimento."
        scope_label = focus_display
    else:
        if source_labels and sink_labels:
            headline = f"O fluxo principal visível parte de {_humanize_label_list(source_labels)} e atende {_humanize_label_list(sink_labels)}."
        elif connection_lines:
            headline = "A camada principal já mostra quem supre e quem é suprido no cenário."
        else:
            headline = "A camada principal ainda não mostra relações de suprimento entre entidades de negócio."
        scope_label = "Cenário inteiro"
    return {
        "scope_label": scope_label,
        "headline": headline,
        "supplied_by_label": _humanize_label_list(supplied_by_labels) or "Ainda não recebe suprimento visível.",
        "supplies_label": _humanize_label_list(supplies_labels) or "Ainda não abastece outra entidade visível.",
        "connection_lines": focus_connection_lines or connection_lines,
        "source_labels": source_labels,
        "sink_labels": sink_labels,
        "orphan_labels": orphan_labels,
    }


def build_studio_readiness_summary(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    node_ids = {str(row.get("node_id", "")).strip() for row in nodes_rows if str(row.get("node_id", "")).strip()}
    inbound_by_node = {node_id: 0 for node_id in node_ids}
    outbound_by_node = {node_id: 0 for node_id in node_ids}
    blockers: list[str] = []
    warnings: list[str] = []
    dosing_without_measurement: list[str] = []
    for row in candidate_links_rows:
        source = str(row.get("from_node", "")).strip()
        target = str(row.get("to_node", "")).strip()
        if source:
            outbound_by_node[source] = outbound_by_node.get(source, 0) + 1
        if target:
            inbound_by_node[target] = inbound_by_node.get(target, 0) + 1
        if target == "W":
            blockers.append(f"{row.get('link_id')} entra em W")
        if source == "S":
            blockers.append(f"{row.get('link_id')} sai de S")
    mandatory_routes = [row for row in route_rows if _coerce_truthy(row.get("mandatory"))]
    desirable_routes = [row for row in route_rows if _route_intent_value(row) == "desirable"]
    optional_routes = [row for row in route_rows if _route_intent_value(row) == "optional"]
    for route in route_rows:
        route_id = str(route.get("route_id", "")).strip() or "ROUTE"
        source = str(route.get("source", "")).strip()
        sink = str(route.get("sink", "")).strip()
        if source and source not in node_ids:
            blockers.append(f"{route_id} referencia source inexistente: {source}")
        if sink and sink not in node_ids:
            blockers.append(f"{route_id} referencia sink inexistente: {sink}")
        if source and outbound_by_node.get(source, 0) == 0:
            warnings.append(f"{route_id} ainda nao tem saida conectada a partir de {source}")
        if sink and inbound_by_node.get(sink, 0) == 0:
            warnings.append(f"{route_id} ainda nao tem entrada conectada em {sink}")
        dose_min = float(route.get("dose_min_l") or 0.0)
        if dose_min > 0 and not _coerce_truthy(route.get("measurement_required")):
            dosing_without_measurement.append(route_id)
    if dosing_without_measurement:
        blockers.append("Rotas com dosagem sem medicao direta: " + ", ".join(sorted(dosing_without_measurement)))
    orphan_nodes = sorted(
        node_id
        for node_id in node_ids
        if inbound_by_node.get(node_id, 0) == 0 and outbound_by_node.get(node_id, 0) == 0
    )
    if orphan_nodes:
        warnings.append("Nos sem conexao no grafo visivel: " + ", ".join(orphan_nodes[:6]))
    visible_business_nodes = _visible_studio_nodes(nodes_rows)
    projected_business_routes = _primary_route_projection_rows(nodes_rows, route_rows)
    status = "ready" if not blockers and node_ids and candidate_links_rows and mandatory_routes else "needs_attention"
    if not node_ids:
        readiness_headline = "Comece montando o cenário no Studio antes de abrir a fila."
        readiness_stage = "Montar a base do cenário"
        primary_action = "Adicionar entidades de negócio no canvas para começar a leitura operacional."
        next_steps = [
            "Adicione as entidades principais do circuito antes de pensar em Runs.",
            "Depois conecte o grafo visível e só então revise a trilha técnica.",
        ]
    elif not candidate_links_rows:
        readiness_headline = "O cenário já tem entidades, mas ainda não tem fluxo suficiente para seguir para Runs."
        readiness_stage = "Conectar o grafo principal"
        primary_action = "Criar conexões de negócio entre as entidades já posicionadas no canvas."
        next_steps = [
            "Conecte o grafo principal antes de enfileirar uma nova run.",
            "Revise avisos de conectividade só depois que o fluxo principal estiver montado.",
        ]
    elif not mandatory_routes:
        readiness_headline = "Falta definir pelo menos uma rota obrigatória antes de comparar candidatos."
        readiness_stage = "Definir a meta operacional"
        primary_action = "Registrar as rotas obrigatórias que a execução precisa atender."
        next_steps = [
            "Defina as rotas obrigatórias antes de abrir Runs.",
            "Use Auditoria apenas se precisar reconciliar a estrutura canônica dessa definição.",
        ]
    elif blockers:
        readiness_headline = "Ainda há bloqueios estruturais impedindo a passagem segura para Runs."
        readiness_stage = "Remover bloqueios"
        primary_action = "Corrigir regras estruturais e rotas inválidas antes de enfileirar uma nova run."
        next_steps = [
            "Feche os bloqueios estruturais antes de enfileirar uma nova run.",
            "Salve e reabra o bundle canônico quando a revisão estiver pronta.",
        ]
    elif warnings:
        readiness_headline = "O cenário já pode avançar, mas ainda vale fechar avisos antes de rodar."
        readiness_stage = "Lapidar antes da fila"
        primary_action = "Revisar avisos de conectividade para reduzir retrabalho em Runs."
        next_steps = [
            "Revise avisos de conectividade e siga para Runs quando a leitura estiver clara.",
            "Salve e reabra o bundle canônico quando a revisão estiver pronta.",
        ]
    else:
        readiness_headline = "Cenário pronto para seguir para Runs."
        readiness_stage = "Liberar a fila"
        primary_action = "Abrir Runs para enfileirar o cenário ou revisar a última execução."
        next_steps = [
            "Siga para Runs para enfileirar ou revisar a fila local.",
            "Salve e reabra o bundle canônico quando a revisão estiver pronta.",
        ]
    return {
        "status": status,
        "node_count": len(node_ids),
        "edge_count": len(candidate_links_rows),
        "business_node_count": len(visible_business_nodes),
        "business_edge_count": len(projected_business_routes) or len(_visible_studio_edges(nodes_rows, candidate_links_rows)),
        "hidden_internal_node_count": max(len(nodes_rows) - len(visible_business_nodes), 0),
        "mandatory_route_count": len(mandatory_routes),
        "desirable_route_count": len(desirable_routes),
        "optional_route_count": len(optional_routes),
        "measurement_route_count": sum(1 for row in route_rows if _coerce_truthy(row.get("measurement_required"))),
        "blocker_count": len(list(dict.fromkeys(blockers))),
        "warning_count": len(list(dict.fromkeys(warnings))),
        "readiness_stage": readiness_stage,
        "readiness_headline": readiness_headline,
        "primary_action": primary_action,
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "next_steps": next_steps,
    }


def render_studio_readiness_panel(summary: dict[str, Any]) -> Any:
    status = str(summary.get("status") or "needs_attention")
    background, color = _status_tone(status)
    blocker_count = int(summary.get("blocker_count", 0) or 0)
    warning_count = int(summary.get("warning_count", 0) or 0)
    next_step = str((summary.get("next_steps") or ["Feche a leitura principal do Studio antes de seguir."])[0])
    if summary.get("blockers"):
        primary_blocker = _humanize_readiness_issue(list(summary.get("blockers", []))[0])
    elif summary.get("warnings"):
        primary_blocker = _humanize_readiness_issue(list(summary.get("warnings", []))[0])
    else:
        primary_blocker = "Nenhum bloqueio ou aviso domina a passagem atual para Runs."
    if status == "ready":
        readiness_state_label = "Pronto para Runs"
        dominant_cta = html.Button("Ir para Runs", id="studio-open-runs-button", style=UI_BUTTON_STYLE)
        secondary_cta = html.Button("Abrir ajustes do Studio", id="studio-readiness-open-workbench-button", style=UI_BUTTON_STYLE)
    elif blocker_count > 0:
        readiness_state_label = "Bloqueado no Studio"
        dominant_cta = html.Button("Corrigir no canvas", id="studio-readiness-open-workbench-button", style=UI_BUTTON_STYLE)
        secondary_cta = html.Button("Abrir Runs com bloqueios", id="studio-open-runs-button", style=UI_BUTTON_STYLE)
    else:
        readiness_state_label = "Exige atenção"
        dominant_cta = html.Button("Revisar no canvas", id="studio-readiness-open-workbench-button", style=UI_BUTTON_STYLE)
        secondary_cta = html.Button("Abrir Runs quando o cenário estiver pronto", id="studio-open-runs-button", style=UI_BUTTON_STYLE)
    if blocker_count > 0:
        runs_button_label = "Abrir Runs com bloqueios"
    elif status != "ready":
        runs_button_label = "Abrir Runs quando o cenário estiver pronto"
    else:
        runs_button_label = "Abrir Runs"
    return html.Div(
        children=[
            html.Div("Readiness do cenário", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 14px", "flexWrap": "wrap"}, children=[html.Span(_humanize_readiness_status(status), style={"padding": "6px 10px", "borderRadius": "999px", "background": background, "color": color, "fontWeight": 700}), html.Span(str(summary.get("readiness_headline") or ("Pronto para rodar" if status == "ready" else "Ainda exige atencao estrutural")), style={"fontWeight": 700, "lineHeight": "1.5"})]),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Estado dominante", readiness_state_label),
                    _guidance_card("Objetivo desta área", "Confirmar se o cenário já pode sair do Studio sem depender da trilha técnica."),
                    _guidance_card("Próxima ação", str(summary.get("primary_action") or "Revise a camada principal antes de abrir Runs.")),
                    _guidance_card("Bloqueio principal", primary_blocker),
                ],
            ),
            html.Div(
                style={**UI_ACTION_ROW_STYLE, "marginTop": "0", "marginBottom": "12px"},
                children=[
                    dominant_cta,
                    secondary_cta,
                    _button_link("Abrir Auditoria", "?tab=audit", "studio-readiness-open-audit-link"),
                ],
            ),
            html.H4("Fluxo principal", style={"marginBottom": "6px"}),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Agora no Studio", str(summary.get("readiness_stage") or "Revisar readiness")),
                    _guidance_card("Sinal de passagem", str(summary.get("readiness_headline") or "Sem headline de readiness.")),
                    _guidance_card("Destino seguinte", next_step),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Entidades visíveis", summary.get("business_node_count", 0)),
                    _metric_card("Fluxos projetados", summary.get("business_edge_count", 0), "Leitura primária do circuito de negócio."),
                    _metric_card("Internos ocultos", summary.get("hidden_internal_node_count", 0), "Hubs e nós técnicos fora do canvas principal."),
                    _metric_card("Rotas obrigatorias", summary.get("mandatory_route_count", 0)),
                    _metric_card("Bloqueios", summary.get("blocker_count", 0), "Impedem seguir direto para Runs."),
                    _metric_card("Avisos", warning_count, "Podem pedir revisão antes do enfileiramento."),
                ],
            ),
            html.H4("Passagem para Runs", style={"marginBottom": "6px"}),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "12px"},
                children=[
                    html.Div(str(summary.get("readiness_stage") or "Preparar a passagem"), style={"fontWeight": 700, "lineHeight": "1.5"}),
                    html.Div("Quando a camada principal estiver clara, siga para Runs para enfileirar ou revisar a fila. Se ainda houver bloqueios, termine a revisão no Studio antes de abrir uma nova rodada.", style={"lineHeight": "1.6", "marginTop": "6px"}),
                    html.Div(runs_button_label, style={"lineHeight": "1.6", "marginTop": "10px", "fontWeight": 700}),
                ],
            ),
            html.H4("Bloqueios", style={"marginBottom": "6px"}),
            _bullet_list([_humanize_readiness_issue(item) for item in list(summary.get("blockers", []))], "Nenhum bloqueio estrutural detectado."),
            html.H4("Avisos", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list([_humanize_readiness_issue(item) for item in list(summary.get("warnings", []))], "Sem aviso relevante neste momento."),
            html.H4("Proximos passos", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list(list(summary.get("next_steps", [])), "Sem proximo passo registrado."),
        ],
    )


def _studio_workspace_focus_summary(
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    route_rows: list[dict[str, Any]] | None,
    studio_summary: dict[str, Any],
) -> dict[str, str]:
    route_rows = route_rows or []
    if edge_summary.get("selected_link_id"):
        from_label = str(edge_summary.get("from_label") or edge_summary.get("selected_edge", {}).get("from_node") or "-")
        to_label = str(edge_summary.get("to_label") or edge_summary.get("selected_edge", {}).get("to_node") or "-")
        to_node = str(edge_summary.get("selected_edge", {}).get("to_node") or "").strip()
        from_node = str(edge_summary.get("selected_edge", {}).get("from_node") or "").strip()
        label = str(edge_summary.get("business_label") or edge_summary.get("selected_link_id") or "Conexão em foco")
        if to_node == "W":
            recommended_action = "Remova ou redirecione esta conexão: W não deve receber rotas entrando na superfície principal."
        elif from_node == "S":
            recommended_action = "Remova ou redirecione esta conexão: S não deve iniciar fluxo na superfície principal."
        else:
            recommended_action = f"Confira comprimento, direção e famílias sugeridas da conexão {edge_summary.get('selected_link_id') or label}."
        return {
            "label": label,
            "headline": f"Conexão em foco: {from_label} -> {to_label}.",
            "recommended_action": recommended_action,
        }
    if node_summary.get("selected_node_id"):
        label = str(node_summary.get("business_label") or node_summary.get("selected_node_id") or "Entidade em foco")
        blocker_count = int(studio_summary.get("blocker_count", 0) or 0)
        connected_routes = [
            row
            for row in route_rows
            if str(row.get("source") or "").strip() == str(node_summary.get("selected_node_id") or "").strip()
            or str(row.get("sink") or "").strip() == str(node_summary.get("selected_node_id") or "").strip()
        ]
        if blocker_count:
            recommended_action = "Use este foco para fechar o principal bloqueio estrutural antes de liberar a passagem para Runs."
        elif connected_routes:
            recommended_action = f"Confirme o papel de {label} nas rotas obrigatórias antes de seguir para Runs."
        else:
            recommended_action = f"Ajuste posição, rótulo e papel de {label} direto no canvas antes de avançar."
        return {
            "label": label,
            "headline": f"Entidade em foco: {label}.",
            "recommended_action": recommended_action,
        }
    return {
        "label": "Sem foco ativo",
        "headline": "Selecione uma entidade ou conexão do grafo para abrir o contexto principal do Studio.",
        "recommended_action": "Clique no canvas para abrir um foco de edição antes de tentar liberar a passagem para Runs.",
    }


def _edge_reverse_impact_text(before_summary: dict[str, Any], after_summary: dict[str, Any]) -> str:
    before_blockers = int(before_summary.get("blocker_count", 0) or 0)
    after_blockers = int(after_summary.get("blocker_count", 0) or 0)
    before_status = str(before_summary.get("status") or "").strip()
    after_status = str(after_summary.get("status") or "").strip()
    if after_blockers < before_blockers:
        return "A inversão reduz os bloqueios de readiness do cenário."
    if after_blockers > before_blockers:
        return "A inversão aumenta os bloqueios de readiness do cenário."
    if after_status == "ready" and before_status != "ready":
        return "A inversão libera a passagem para Runs."
    if after_status == "ready":
        return "A inversão mantém o cenário pronto para Runs."
    return str(after_summary.get("readiness_headline") or "A inversão mantém a leitura atual da readiness.")


def _build_studio_edge_reverse_preview(
    edge_summary: dict[str, Any],
    studio_summary: dict[str, Any],
    route_rows: list[dict[str, Any]] | None,
    nodes_rows: list[dict[str, Any]] | None = None,
    candidate_links_rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    route_rows = route_rows or []
    nodes_rows = nodes_rows or []
    candidate_links_rows = candidate_links_rows or []
    selected_edge = edge_summary.get("selected_edge") or {}
    selected_link_id = str(edge_summary.get("selected_link_id") or selected_edge.get("link_id") or "").strip()
    if not selected_edge or not selected_link_id:
        return {
            "current_flow": "Selecione uma conexão no canvas para abrir o trecho de suprimento desta edição.",
            "reverse_preview": "Sem conexão em foco para inverter agora.",
            "current_effect": "Sem conexão em foco: primeiro selecione um trecho do grafo principal.",
            "reverse_impact": "O impacto da inversão aparece aqui assim que uma conexão visível for selecionada.",
            "route_scope": "Nenhuma rota em foco neste momento.",
        }

    from_node_id = str(selected_edge.get("from_node") or "").strip()
    to_node_id = str(selected_edge.get("to_node") or "").strip()
    from_label = str(edge_summary.get("from_label") or from_node_id or "-")
    to_label = str(edge_summary.get("to_label") or to_node_id or "-")
    focus_node_ids = {node_id for node_id in (from_node_id, to_node_id) if node_id}
    prioritized_routes = [
        route
        for route in route_rows
        if str(route.get("source") or "").strip() in focus_node_ids or str(route.get("sink") or "").strip() in focus_node_ids
    ]
    focused_dosing_routes = [
        route
        for route in prioritized_routes
        if float(route.get("dose_min_l") or 0.0) > 0
    ]
    local_violations: list[str] = []
    if to_node_id == "W":
        local_violations.append("A conexão em foco entra em W; ajuste a direção antes de continuar.")
    if from_node_id == "S":
        local_violations.append("A conexão em foco sai de S; corrija a direção para manter a regra estrutural.")
    for route in prioritized_routes:
        route_id = str(route.get("route_id") or "ROTA")
        if str(route.get("sink") or "").strip() == "W":
            local_violations.append(f"{route_id} tenta terminar em W; essa rota precisa ser redirecionada.")
        if str(route.get("source") or "").strip() == "S":
            local_violations.append(f"{route_id} tenta sair de S; essa rota precisa ser revista.")
        if float(route.get("dose_min_l") or 0.0) > 0 and not _coerce_truthy(route.get("measurement_required")):
            local_violations.append(f"{route_id} usa dosagem sem medição direta compatível.")

    if local_violations:
        current_effect = local_violations[0]
    elif focused_dosing_routes:
        current_effect = "Há rotas com dosagem ligadas a este trecho; confirme medição direta antes de seguir para Runs."
    elif int(studio_summary.get("blocker_count", 0) or 0) > 0:
        current_effect = "Este trecho convive com outros bloqueios estruturais no cenário e merece revisão antes da fila."
    else:
        current_effect = "Este trecho não aciona bloqueio estrutural imediato na readiness."

    route_scope = (
        f"Este trecho toca {len(prioritized_routes)} rota(s) em foco."
        if prioritized_routes
        else "Nenhuma rota obrigatória ou de dosagem está ligada a este trecho agora."
    )
    reverse_preview = f"Se inverter agora, {to_label} passa a suprir {from_label}."
    reverse_impact = "O impacto da inversão ainda depende de dados completos do cenário."
    if nodes_rows and candidate_links_rows:
        try:
            reversed_links, _ = reverse_edge_studio_selection(
                candidate_links_rows,
                selected_link_id=selected_link_id,
                nodes_rows=nodes_rows,
            )
            before_summary = build_studio_readiness_summary(nodes_rows, candidate_links_rows, route_rows)
            after_summary = build_studio_readiness_summary(nodes_rows, reversed_links, route_rows)
            reverse_impact = _edge_reverse_impact_text(before_summary, after_summary)
        except ValueError as exc:
            reverse_impact = str(exc)

    return {
        "current_flow": f"{from_label} supre {to_label}.",
        "reverse_preview": reverse_preview,
        "current_effect": current_effect,
        "reverse_impact": reverse_impact,
        "route_scope": route_scope,
    }


def _reverse_edge_with_feedback(
    candidate_links_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
    nodes_rows: list[dict[str, Any]] | None,
    route_rows: list[dict[str, Any]] | None,
    message_prefix: str,
    edge_component_rules_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None, str]:
    route_rows = route_rows or []
    before_summary = build_studio_readiness_summary(nodes_rows or [], candidate_links_rows, route_rows)
    updated_links, next_edge_selection = reverse_edge_studio_selection(
        candidate_links_rows,
        selected_link_id=selected_link_id,
        nodes_rows=nodes_rows or [],
        edge_component_rules_rows=edge_component_rules_rows or [],
    )
    after_summary = build_studio_readiness_summary(nodes_rows or [], updated_links, route_rows)
    node_lookup = {
        str(row.get("node_id", "")).strip(): dict(row)
        for row in _visible_studio_nodes(nodes_rows or [])
        if str(row.get("node_id", "")).strip()
    }
    reversed_row = next(
        (
            row
            for row in updated_links
            if str(row.get("link_id", "")).strip() == str(next_edge_selection or selected_link_id or "").strip()
        ),
        {},
    )
    flow_line = _studio_edge_business_label(reversed_row, node_lookup)
    impact = _edge_reverse_impact_text(before_summary, after_summary)
    return updated_links, next_edge_selection, f"{message_prefix} Agora {flow_line}. {impact}"


def _studio_workspace_quick_edit_cards(
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    studio_summary: dict[str, Any],
    route_rows: list[dict[str, Any]] | None,
    nodes_rows: list[dict[str, Any]] | None = None,
    candidate_links_rows: list[dict[str, Any]] | None = None,
) -> list[Any]:
    selected_node = node_summary.get("selected_node") or {}
    selected_edge_row = edge_summary.get("selected_edge") or {}
    selected_node_present = bool(str(node_summary.get("selected_node_id") or "").strip())
    selected_edge_present = bool(edge_summary.get("selected_edge"))
    reverse_preview = _build_studio_edge_reverse_preview(
        edge_summary,
        studio_summary,
        route_rows,
        nodes_rows=nodes_rows,
        candidate_links_rows=candidate_links_rows,
    )
    return [
        html.Div(
            style={**UI_MUTED_CARD_STYLE, "padding": "14px"},
            children=[
                html.Div("Entidade em foco", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                html.Div(
                    "Atualize o rótulo visível desta entidade sem sair da leitura principal do Studio."
                    if selected_node_present
                    else "Selecione um nó no canvas para liberar a edição direta do rótulo principal.",
                    style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"},
                ),
                _field_block(
                    "Rótulo visível",
                    dcc.Input(
                        id="studio-focus-node-label",
                        type="text",
                        value=str(selected_node.get("label") or node_summary.get("business_label") or ""),
                        disabled=not selected_node_present,
                        persistence=True,
                        persistence_type="session",
                        style={"width": "100%"},
                    ),
                ),
                html.Div(
                    style=UI_ACTION_ROW_STYLE,
                    children=[
                        html.Button(
                            "Aplicar rótulo direto no canvas",
                            id="studio-focus-node-apply-button",
                            style=UI_BUTTON_STYLE,
                            disabled=not selected_node_present,
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            style={**UI_MUTED_CARD_STYLE, "padding": "14px"},
            children=[
                html.Div("Conexão em foco", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                html.Div(
                    "Ajuste comprimento, famílias sugeridas ou direção sem abrir a bancada completa."
                    if selected_edge_present
                    else "Selecione uma conexão no canvas para liberar os ajustes rápidos deste trecho.",
                    style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"},
                ),
                html.Div(
                    style=UI_TWO_COLUMN_STYLE,
                    children=[
                        _field_block(
                            "Comprimento (m)",
                            dcc.Input(
                                id="studio-focus-edge-length-m",
                                type="number",
                                value=selected_edge_row.get("length_m"),
                                disabled=not selected_edge_present,
                                persistence=True,
                                persistence_type="session",
                                style={"width": "100%"},
                            ),
                        ),
                        _field_block(
                            "Famílias sugeridas",
                            dcc.Input(
                                id="studio-focus-edge-family-hint",
                                type="text",
                                value=str(selected_edge_row.get("family_hint") or ""),
                                disabled=not selected_edge_present,
                                persistence=True,
                                persistence_type="session",
                                style={"width": "100%"},
                            ),
                        ),
                    ],
                ),
                html.Div(
                    style=UI_ACTION_ROW_STYLE,
                    children=[
                        html.Button(
                            "Aplicar conexão",
                            id="studio-focus-edge-apply-button",
                            style=UI_BUTTON_STYLE,
                            disabled=not selected_edge_present,
                        ),
                        html.Button(
                            "Inverter direção",
                            id="studio-focus-edge-reverse-button",
                            style=UI_BUTTON_STYLE,
                            disabled=not selected_edge_present,
                        ),
                    ],
                ),
                html.Div(
                    id="studio-focus-edge-flow-preview",
                    style={**UI_THREE_COLUMN_STYLE, "marginTop": "12px"},
                    children=[
                        _guidance_card("Fluxo atual", reverse_preview["current_flow"]),
                        _guidance_card("Se inverter agora", reverse_preview["reverse_preview"]),
                        _guidance_card("Impacto previsto", reverse_preview["reverse_impact"]),
                        _guidance_card("Rotas tocadas", reverse_preview["route_scope"]),
                    ],
                ),
                html.Div(reverse_preview["current_effect"], style={"marginTop": "10px", "lineHeight": "1.6", "fontWeight": 700}),
            ],
        ),
    ]


def render_studio_route_editor_panel(
    route_rows: list[dict[str, Any]] | None,
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    studio_summary: dict[str, Any],
    route_draft_source_id: str | None = None,
) -> Any:
    focus_node_ids = {
        str(node_summary.get("selected_node_id") or "").strip(),
        str((edge_summary.get("selected_edge") or {}).get("from_node") or "").strip(),
        str((edge_summary.get("selected_edge") or {}).get("to_node") or "").strip(),
    }
    focus_node_ids = {node_id for node_id in focus_node_ids if node_id}
    route_options = _route_choice_options(route_rows, focus_node_ids=focus_node_ids)
    form_values = _route_studio_form_values(route_rows, focus_node_ids=focus_node_ids)
    focused_routes = _route_focus_rows(route_rows, focus_node_ids=focus_node_ids)
    selected_route_present = bool(form_values.get("route_id"))
    selected_edge = edge_summary.get("selected_edge") or {}
    selected_edge_present = bool(selected_edge)
    route_draft_source = str(route_draft_source_id or "").strip()
    selected_edge_flow = (
        f"{str(edge_summary.get('from_label') or '-')} supre {str(edge_summary.get('to_label') or '-')}"
        if selected_edge_present
        else "Selecione uma conexão no canvas para criar ou revisar a rota deste trecho."
    )
    top_route = focused_routes[0] if focused_routes else None
    if top_route is not None:
        route_scope_text = (
            f"O foco atual toca {len(focused_routes)} rota(s). Comece por {top_route.get('route_id')} e ajuste a intenção perto do canvas."
            if focus_node_ids
            else f"O cenário já tem {len(focused_routes)} rota(s). Ajuste a intenção das mais relevantes sem sair do primeiro fold."
        )
    else:
        route_scope_text = "Selecione um trecho do canvas para abrir as rotas ligadas a ele."
    highlighted_route_lines = []
    for route in focused_routes[:4]:
        route_id = str(route.get("route_id") or "ROTA")
        source = str(route.get("source") or "-").strip() or "-"
        sink = str(route.get("sink") or "-").strip() or "-"
        intent = _route_intent_label(_route_intent_value(route))
        notes = str(route.get("notes") or "").strip()
        highlight = f"{route_id}: {source} -> {sink} · {intent}"
        if notes:
            highlight += f" · {notes}"
        highlighted_route_lines.append(highlight)
    return html.Div(
        id="studio-route-editor-panel",
        style={**UI_MUTED_CARD_STYLE, "padding": "12px", "marginBottom": "12px"},
        children=[
            html.Div("Rotas que precisam de serviço", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(route_scope_text, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "10px", "marginTop": "10px"},
                children=[
                    html.Div("Trecho em foco", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(selected_edge_flow, style={"fontWeight": 700, "lineHeight": "1.45", "marginTop": "6px"}),
                    html.Div(
                        f"Origem de rota em preparo: {route_draft_source}. Selecione o destino no canvas para concluir."
                        if route_draft_source
                        else "Ainda não há uma origem de rota em preparo no canvas.",
                        style={"lineHeight": "1.45", "marginTop": "6px"},
                    ),
                    html.Div(
                        "Use a conexão selecionada para criar a rota deste trecho sem passar pelo workbench."
                        if selected_edge_present
                        else "A criação direta de rota fica disponível assim que uma conexão visível for selecionada.",
                        style={"lineHeight": "1.45", "marginTop": "6px"},
                    ),
                    html.Div(
                        style=UI_ACTION_ROW_STYLE,
                        children=[
                            html.Button(
                                "Criar rota deste trecho",
                                id="studio-route-create-from-edge-button",
                                style=UI_BUTTON_STYLE,
                                disabled=not selected_edge_present,
                            ),
                            html.Button(
                                "Obrigatória",
                                id="studio-route-intent-mandatory-button",
                                style=UI_BUTTON_STYLE,
                                disabled=not selected_route_present,
                            ),
                            html.Button(
                                "Desejável",
                                id="studio-route-intent-desirable-button",
                                style=UI_BUTTON_STYLE,
                                disabled=not selected_route_present,
                            ),
                            html.Button(
                                "Opcional",
                                id="studio-route-intent-optional-button",
                                style=UI_BUTTON_STYLE,
                                disabled=not selected_route_present,
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginTop": "10px"},
                children=[
                    html.Span("Obrigatória", style=_route_intent_badge_style("mandatory")),
                    html.Span("Desejável", style=_route_intent_badge_style("desirable")),
                    html.Span("Opcional", style=_route_intent_badge_style("optional")),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                children=[
                    _guidance_card("Readiness desta camada", str(studio_summary.get("readiness_stage") or "Revisar rotas")),
                    _guidance_card("Gate para Runs", "Feche primeiro as rotas obrigatórias e confirme medição direta quando houver dosagem."),
                ],
            ),
            _field_block(
                "Rota em foco",
                dcc.Dropdown(
                    id="studio-route-focus-dropdown",
                    options=route_options,
                    value=form_values.get("route_id"),
                    persistence=True,
                    persistence_type="session",
                    placeholder="Selecione uma rota ligada ao foco atual",
                ),
            ),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginTop": "8px"},
                children=[
                    _field_block(
                        "Intenção",
                        dcc.Dropdown(
                            id="studio-route-intent",
                            options=[
                                {"label": "Obrigatória", "value": "mandatory"},
                                {"label": "Desejável", "value": "desirable"},
                                {"label": "Opcional", "value": "optional"},
                            ],
                            value=form_values.get("intent"),
                            disabled=not selected_route_present,
                            persistence=True,
                            persistence_type="session",
                        ),
                    ),
                    _field_block(
                        "Vazão mínima (L/min)",
                        dcc.Input(
                            id="studio-route-q-min-lpm",
                            type="number",
                            value=form_values.get("q_min_delivered_lpm"),
                            disabled=not selected_route_present,
                            persistence=True,
                            persistence_type="session",
                            style={"width": "100%"},
                        ),
                    ),
                    _field_block(
                        "Dosagem mínima (L)",
                        dcc.Input(
                            id="studio-route-dose-min-l",
                            type="number",
                            value=form_values.get("dose_min_l"),
                            disabled=not selected_route_present,
                            persistence=True,
                            persistence_type="session",
                            style={"width": "100%"},
                        ),
                    ),
                ],
            ),
            _field_block(
                "Observação visível da rota",
                dcc.Input(
                    id="studio-route-notes",
                    type="text",
                    value=form_values.get("notes"),
                    disabled=not selected_route_present,
                    persistence=True,
                    persistence_type="session",
                    style={"width": "100%"},
                ),
            ),
            _field_block(
                "Medição direta",
                dcc.Checklist(
                    id="studio-route-measurement-required",
                    options=[{"label": "Exigir medição direta nesta rota", "value": "measurement_required"}],
                    value=form_values.get("measurement_required"),
                    persistence=True,
                    persistence_type="session",
                ),
            ),
            html.Div(
                style=UI_ACTION_ROW_STYLE,
                children=[
                    html.Button(
                        "Aplicar rota no foco",
                        id="studio-route-apply-button",
                        style=UI_BUTTON_STYLE,
                        disabled=not selected_route_present,
                    ),
                ],
            ),
            html.Details(
                id="studio-route-editor-details",
                style={**UI_MUTED_CARD_STYLE, "padding": "10px", "marginTop": "10px"},
                children=[
                    html.Summary("Ver rotas ligadas a este foco"),
                    _bullet_list(
                        highlighted_route_lines,
                        "Ainda não há rota ligada ao foco atual.",
                    ),
                ],
            ),
        ],
    )


def render_studio_workspace_panel(
    studio_summary: dict[str, Any],
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]] | None,
    studio_status_text: str | None,
    route_draft_source_id: str | None = None,
) -> Any:
    status = str(studio_summary.get("status") or "needs_attention")
    background, color = _status_tone(status)
    blocker_count = int(studio_summary.get("blocker_count", 0) or 0)
    warning_count = int(studio_summary.get("warning_count", 0) or 0)
    focus_summary = _studio_workspace_focus_summary(node_summary, edge_summary, route_rows, studio_summary)
    issues = [
        _humanize_readiness_issue(item)
        for item in [*(studio_summary.get("blockers") or []), *(studio_summary.get("warnings") or [])]
    ]
    business_flow = build_studio_business_flow_summary(
        nodes_rows,
        candidate_links_rows,
        route_rows,
        focus_node_ids={
            str(node_summary.get("selected_node_id") or "").strip(),
            str((edge_summary.get("selected_edge") or {}).get("from_node") or "").strip(),
            str((edge_summary.get("selected_edge") or {}).get("to_node") or "").strip(),
        },
    )
    top_issue = issues[0] if issues else "Nenhum bloqueio ou aviso domina a leitura atual do cenário."
    connection_lines = list(business_flow.get("connection_lines") or [])
    connection_preview = connection_lines[0] if connection_lines else "Ainda não há trecho de suprimento legível na camada principal."
    selected_node_present = bool(str(node_summary.get("selected_node_id") or "").strip())
    selected_edge_present = bool(edge_summary.get("selected_edge"))
    quick_edit_cards = _studio_workspace_quick_edit_cards(
        node_summary,
        edge_summary,
        studio_summary,
        route_rows,
        nodes_rows=nodes_rows,
        candidate_links_rows=candidate_links_rows,
    )
    route_editor_panel = render_studio_route_editor_panel(
        route_rows,
        node_summary,
        edge_summary,
        studio_summary,
        route_draft_source_id=route_draft_source_id,
    )
    runs_enabled = status == "ready"
    runs_button_label = "Ir para Runs" if runs_enabled else "Runs bloqueado neste estado"
    primary_actions: list[Any]
    if runs_enabled:
        primary_actions = [
            html.Button(runs_button_label, id="studio-workspace-open-runs-button", style=UI_BUTTON_STYLE, disabled=False),
            html.Button("Revisar no canvas", id="studio-workspace-open-workbench-button", style=UI_BUTTON_STYLE),
        ]
    else:
        primary_actions = [
            html.Button("Corrigir no canvas", id="studio-workspace-open-workbench-button", style=UI_BUTTON_STYLE),
            html.Button(runs_button_label, id="studio-workspace-open-runs-button", style=UI_BUTTON_STYLE, disabled=True),
        ]
    return html.Div(
        children=[
            html.Div("Leitura do cenário", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 12px", "flexWrap": "wrap"},
                children=[
                    html.Span(_humanize_readiness_status(status), style={"padding": "6px 10px", "borderRadius": "999px", "background": background, "color": color, "fontWeight": 700}),
                    html.Span(str(studio_summary.get("readiness_headline") or "Sem leitura principal do cenário."), style={"fontWeight": 700, "lineHeight": "1.5"}),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "marginBottom": "12px"},
                children=[
                    _guidance_card("Seleção atual", focus_summary["headline"]),
                    _guidance_card("Conectividade em foco", connection_preview),
                    _guidance_card("Readiness local", top_issue),
                    _guidance_card("Próxima ação", str(studio_summary.get("primary_action") or focus_summary["recommended_action"])),
                ],
            ),
            html.Div(
                style={**UI_COMPACT_BANNER_CARD_STYLE, "marginBottom": "12px"},
                children=[
                    html.Div("O que precisa de atenção agora", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(top_issue, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                    html.Div(focus_summary["recommended_action"], style={"lineHeight": "1.45", "marginTop": "8px"}),
                ],
            ),
            html.Div(
                id="studio-workspace-quick-edit-panel",
                style={**UI_MUTED_CARD_STYLE, "padding": "12px", "marginBottom": "12px"},
                children=[
                    html.Div("Ajustes locais do canvas", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(
                        "Use estes controles rápidos para ajustes rotineiros sem abrir a bancada avançada."
                        if selected_node_present or selected_edge_present
                        else "Selecione um nó ou uma conexão no canvas para destravar os ajustes rápidos locais.",
                        style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"},
                    ),
                    html.Div(style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"}, children=quick_edit_cards),
                    html.Div(
                        id="studio-workspace-local-actions-panel",
                        style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"},
                        children=[
                            html.Button("Mover à esquerda", id="studio-focus-move-left-button", style=UI_BUTTON_STYLE, disabled=not selected_node_present),
                            html.Button("Mover acima", id="studio-focus-move-up-button", style=UI_BUTTON_STYLE, disabled=not selected_node_present),
                            html.Button("Mover abaixo", id="studio-focus-move-down-button", style=UI_BUTTON_STYLE, disabled=not selected_node_present),
                            html.Button("Duplicar nó em foco", id="studio-focus-duplicate-node-button", style=UI_BUTTON_STYLE, disabled=not selected_node_present),
                            html.Button("Excluir conexão em foco", id="studio-focus-delete-edge-button", style=UI_BUTTON_STYLE, disabled=not selected_edge_present),
                            html.Button("Abrir bancada completa", id="studio-focus-open-workbench-button", style=UI_BUTTON_STYLE),
                        ],
                    ),
                ],
            ),
            route_editor_panel,
            html.Div(
                id="studio-business-flow-panel",
                style={**UI_MUTED_CARD_STYLE, "padding": "12px", "marginBottom": "12px"},
                children=[
                    html.Div("Quem supre quem na camada principal", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(str(business_flow.get("headline") or "Sem cadeia principal visível."), style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                    html.Div(
                        style={**UI_TWO_COLUMN_STYLE, "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "marginTop": "10px"},
                        children=[
                            _guidance_card("É suprido por", str(business_flow.get("supplied_by_label") or "Ainda não recebe suprimento visível.")),
                            _guidance_card("Supre", str(business_flow.get("supplies_label") or "Ainda não abastece outra entidade visível.")),
                        ],
                    ),
                    html.Details(
                        style={**UI_MUTED_CARD_STYLE, "padding": "10px", "marginTop": "10px"},
                        children=[
                            html.Summary("Ver trechos legíveis do fluxo"),
                            _bullet_list(
                                list(business_flow.get("connection_lines") or [])[:4],
                                "Ainda não há trecho de suprimento legível na camada principal.",
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Bloqueios", blocker_count, "Impedem liberar a passagem para Runs."),
                    _metric_card("Avisos", warning_count, "Pedem revisão antes de enfileirar."),
                    _metric_card("Rotas obrigatórias", studio_summary.get("mandatory_route_count", 0), "Base mínima da conectividade principal."),
                    _metric_card("Rotas desejáveis", studio_summary.get("desirable_route_count", 0), "Desejos explícitos sem virar hard constraint."),
                    _metric_card("Rotas opcionais", studio_summary.get("optional_route_count", 0), "Alternativas que não travam a saída para Runs."),
                ],
            ),
            html.Div(style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"}, children=[*primary_actions, _button_link("Abrir Auditoria", "?tab=audit", "studio-workspace-open-audit-link")]),
            html.Div(
                style={**UI_COMPACT_BANNER_CARD_STYLE, "marginTop": "12px"},
                children=[
                    html.Div("Sinal de saída desta área", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(str((studio_summary.get("next_steps") or ["Feche a leitura principal do Studio antes de sair."])[0]), style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                    render_status_banner(studio_status_text),
                ],
            ),
        ]
    )


def render_studio_command_center_panel(
    studio_summary: dict[str, Any],
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]] | None = None,
) -> Any:
    options = _business_node_choice_options(nodes_rows)
    quick_source, quick_target = _studio_quick_link_defaults(nodes_rows, node_summary, edge_summary)
    selected_node_label = str(node_summary.get("business_label") or "").strip()
    selected_edge_label = str(edge_summary.get("business_label") or "").strip()
    selected_focus = selected_edge_label or selected_node_label or "Nenhuma entidade selecionada"
    status = str(studio_summary.get("status") or "needs_attention")
    runs_ready = status == "ready"
    focus_hint = (
        f"A conexão em foco é {selected_edge_label}. Revise este trecho e use a criação rápida apenas para completar o fluxo principal."
        if selected_edge_label
        else (
            f"A entidade em foco é {selected_node_label}. Use a paleta para completar o fluxo a partir deste ponto."
            if selected_node_label
            else "Selecione uma entidade no canvas para que a criação e a conexão rápidas usem esse contexto."
        )
    )
    palette_buttons = [
        html.Button(
            preset["button_label"],
            id=f"studio-add-{preset_key}-node-button",
            style=UI_BUTTON_STYLE,
            title=preset["button_hint"],
        )
        for preset_key, preset in BUSINESS_NODE_PRESETS.items()
    ]
    route_rows = route_rows or []
    return html.Div(
        id="studio-command-center-panel",
        children=[
            html.Div("Command center do Studio", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div("Desenhe primeiro as rotas que precisam de serviço", style={"fontWeight": 700, "fontSize": "20px", "lineHeight": "1.25", "marginTop": "6px"}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "gridTemplateColumns": "repeat(2, minmax(0, 1fr))", "marginTop": "12px", "marginBottom": "12px"},
                children=[
                    _guidance_card("Foco atual", selected_focus),
                    _guidance_card("Passagem para Runs", "Liberada" if runs_ready else "Continue no Studio até fechar readiness e conectividade."),
                ],
            ),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginBottom": "12px"},
                children=[
                    html.Div("Intenção das rotas", style={"fontWeight": 700, "marginBottom": "8px"}),
                    html.Div("Obrigatória, desejável e opcional ficam na mesma superfície para evitar desvio prematuro ao workbench.", style={"lineHeight": "1.45", "marginBottom": "10px"}),
                    html.Div(
                        style={"display": "flex", "gap": "8px", "flexWrap": "wrap"},
                        children=[
                            html.Span(f"{studio_summary.get('mandatory_route_count', 0)} obrigatórias", style=_route_intent_badge_style("mandatory")),
                            html.Span(f"{studio_summary.get('desirable_route_count', 0)} desejáveis", style=_route_intent_badge_style("desirable")),
                            html.Span(f"{studio_summary.get('optional_route_count', 0)} opcionais", style=_route_intent_badge_style("optional")),
                        ],
                    ),
                    html.Div(
                        _route_choice_options(route_rows)[0]["label"] if _route_choice_options(route_rows) else "Ainda não há rota registrada para esta leitura.",
                        style={"marginTop": "10px", "lineHeight": "1.45"},
                    ),
                ],
            ),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginBottom": "12px"},
                children=[
                    html.Div("Adicionar entidades visíveis", style={"fontWeight": 700, "marginBottom": "8px"}),
                    html.Div("Crie só fontes, produtos, mistura, serviço e saída. Hubs internos continuam fora do canvas.", style={"lineHeight": "1.45", "marginBottom": "10px"}),
                    html.Div(style=UI_ACTION_ROW_STYLE, children=palette_buttons),
                ],
            ),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginBottom": "12px"},
                children=[
                    html.Div("Ligação rápida", style={"fontWeight": 700, "marginBottom": "8px"}),
                    html.Div(focus_hint, style={"lineHeight": "1.45", "marginBottom": "10px"}),
                    html.Div(
                        style=UI_THREE_COLUMN_STYLE,
                        children=[
                            _field_block(
                                "De",
                                dcc.Dropdown(
                                    id="studio-quick-link-source",
                                    options=options,
                                    value=quick_source,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ),
                            _field_block(
                                "Para",
                                dcc.Dropdown(
                                    id="studio-quick-link-target",
                                    options=options,
                                    value=quick_target,
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ),
                            _field_block(
                                "Tipo de conexão",
                                dcc.Dropdown(
                                    id="studio-quick-link-archetype",
                                    options=BUSINESS_EDGE_ARCHETYPE_OPTIONS,
                                    value="bus_segment",
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ),
                        ],
                    ),
                    html.Div(
                        style=UI_ACTION_ROW_STYLE,
                        children=[
                            html.Button("Criar conexão no canvas", id="studio-quick-link-create-button", style=UI_BUTTON_STYLE),
                            html.Button("Abrir workbench avançado", id="studio-command-open-workbench-button", style=UI_BUTTON_STYLE),
                        ],
                    ),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Entidades de negócio", studio_summary.get("business_node_count", 0), "Só o que o usuário precisa editar."),
                    _metric_card("Conexões visíveis", studio_summary.get("business_edge_count", 0), "Fluxo principal sem malha interna."),
                    _metric_card("Internos ocultos", studio_summary.get("hidden_internal_node_count", 0), "Nós derivados e hubs fora da superfície principal."),
                    _metric_card("Rotas declaradas", len(route_rows), "Trabalho principal desta etapa do Studio."),
                ],
            ),
        ],
    )


def build_studio_projection_summary(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    visible_nodes = _visible_studio_nodes(nodes_rows)
    node_lookup = {
        str(row.get("node_id", "")).strip(): dict(row)
        for row in visible_nodes
        if str(row.get("node_id", "")).strip()
    }
    projected_routes = _primary_route_projection_rows(nodes_rows, route_rows)
    invalid_routes: list[str] = []
    for route in route_rows:
        route_id = str(route.get("route_id", "")).strip() or "ROUTE"
        source = str(route.get("source", "")).strip()
        sink = str(route.get("sink", "")).strip()
        reasons: list[str] = []
        if source not in node_lookup:
            reasons.append(f"source {source or '-'} fora da camada principal")
        if sink not in node_lookup:
            reasons.append(f"sink {sink or '-'} fora da camada principal")
        if reasons:
            invalid_routes.append(f"{route_id}: " + "; ".join(reasons))
    covered_node_ids = {
        node_id
        for route in projected_routes
        for node_id in [str(route.get("source", "")).strip(), str(route.get("target", "")).strip()]
        if node_id
    }
    uncovered_nodes = sorted(
        _studio_node_business_label(node_lookup[node_id])
        for node_id in node_lookup
        if node_id not in covered_node_ids
    )
    if not route_rows or not projected_routes:
        status = "degraded"
        headline = "Projeção de negócio degradada"
        guidance = [
            "A camada principal manteve apenas as entidades de negócio.",
            "Abra a trilha técnica para revisar campos avançados ou a aba Auditoria enquanto os metadados de rota são completados.",
        ]
    elif invalid_routes or uncovered_nodes:
        status = "partial"
        headline = "Projeção de negócio parcial"
        guidance = [
            "A visualização principal cobre parte do cenário e esconde a malha interna por design.",
            "Use a trilha técnica apenas para entender as lacunas de metadata ou revisar a estrutura canônica.",
        ]
    else:
        status = "complete"
        headline = "Projeção de negócio completa"
        guidance = [
            "A camada principal já cobre o cenário com rotas legíveis de negócio.",
            "A trilha técnica permanece disponível apenas para aprofundamento ou edição estrutural avançada.",
        ]
    return {
        "status": status,
        "headline": headline,
        "projected_route_count": len(projected_routes),
        "route_metadata_count": len(route_rows),
        "business_node_count": len(visible_nodes),
        "covered_node_count": len(covered_node_ids),
        "uncovered_nodes": uncovered_nodes,
        "invalid_routes": invalid_routes,
        "guidance": guidance,
        "technical_trail_message": "Campos avançados do Studio e Auditoria guardam a estrutura técnica completa sem recolocar nós internos na superfície principal.",
    }


def render_studio_projection_panel(summary: dict[str, Any]) -> Any:
    status = str(summary.get("status") or "partial")
    background, color = _status_tone(
        "ready" if status == "complete" else ("needs_attention" if status == "partial" else "blocked")
    )
    return html.Div(
        children=[
            html.Div("Cobertura da projeção", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 14px", "flexWrap": "wrap"},
                children=[
                    html.Span(str(summary.get("headline") or "-"), style={"padding": "6px 10px", "borderRadius": "999px", "background": background, "color": color, "fontWeight": 700}),
                    html.Span(str(summary.get("technical_trail_message") or ""), style={"lineHeight": "1.5"}),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Objetivo desta área", "Mostrar somente a camada de negócio que sustenta a leitura principal do Studio."),
                    _guidance_card("Quando abrir Auditoria", "Aprofunde a trilha técnica apenas se a projeção principal não explicar uma lacuna estrutural."),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Rotas projetadas", summary.get("projected_route_count", 0)),
                    _metric_card("Rotas declaradas", summary.get("route_metadata_count", 0)),
                    _metric_card("Entidades cobertas", f"{summary.get('covered_node_count', 0)}/{summary.get('business_node_count', 0)}"),
                ],
            ),
            html.H4("Leitura desta camada", style={"marginBottom": "6px"}),
            _bullet_list([str(item) for item in summary.get("guidance", [])], "Sem orientação registrada."),
            html.H4("Lacunas visíveis", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list(
                (
                    [f"Entidades sem rota projetada: {', '.join(summary.get('uncovered_nodes', []))}"] if summary.get("uncovered_nodes") else []
                )
                + list(summary.get("invalid_routes", []))[:4],
                "Nenhuma lacuna relevante na projeção principal.",
            ),
            html.H4("Próximo passo", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(
                style=UI_ACTION_ROW_STYLE,
                children=[
                    html.Button("Abrir orientação técnica", id="studio-open-technical-guide-button", style=UI_BUTTON_STYLE),
                    html.Button("Ir para Auditoria", id="studio-open-audit-button", style=UI_BUTTON_STYLE),
                ],
            ),
        ],
    )


def render_studio_canvas_guidance_panel(
    summary: dict[str, Any],
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
) -> Any:
    selected_node_id = str(node_summary.get("selected_node_id") or "").strip()
    selected_edge_id = str(edge_summary.get("selected_link_id") or "").strip()
    selected_node_label = str(node_summary.get("business_label") or selected_node_id or "").strip()
    selected_edge_label = str(edge_summary.get("business_label") or selected_edge_id or "").strip()
    blocker_count = int(summary.get("blocker_count", 0) or 0)
    warning_count = int(summary.get("warning_count", 0) or 0)
    selected_edge = edge_summary.get("selected_edge") or {}
    if selected_edge_id and selected_edge_label:
        current_focus = f"Conexão em foco: {selected_edge_label}."
        canvas_action = "Revise a conexão selecionada, ajuste comprimento ou famílias e inverta a direção direto no primeiro fold quando isso destravar o fluxo."
        if str(selected_edge.get("to_node") or "").strip() == "W":
            local_blocker = "Bloqueio local: esta conexão ainda entra em W e precisa ter a direção corrigida neste foco."
        elif str(selected_edge.get("from_node") or "").strip() == "S":
            local_blocker = "Bloqueio local: esta conexão ainda sai de S e precisa ter a direção corrigida neste foco."
        elif blocker_count > 0:
            local_blocker = "Bloqueio local: use esta conexão para destravar a conectividade principal antes de abrir Runs."
        elif warning_count > 0:
            local_blocker = "Aviso local: feche esta revisão no canvas antes de avançar para Runs."
        else:
            local_blocker = "Nada neste foco impede Runs; use a conexão para confirmar fluxo, comprimento e famílias sugeridas."
        primary_button_label = "Abrir bancada desta conexão"
    elif selected_node_id and selected_node_label:
        current_focus = f"Entidade em foco: {selected_node_label}."
        canvas_action = "Use a entidade selecionada para reposicionar, revisar conectividade e validar o papel dela antes de abrir Runs."
        if blocker_count > 0:
            local_blocker = "Bloqueio local: este nó ajuda a localizar a próxima correção estrutural no grafo principal."
        elif warning_count > 0:
            local_blocker = "Aviso local: confirme as conexões deste nó antes de enfileirar uma nova run."
        else:
            local_blocker = "Este nó já pode ser usado como ponto de conferência final antes de abrir Runs."
        primary_button_label = "Abrir bancada desta entidade"
    else:
        current_focus = "Nenhum foco ativo no canvas."
        canvas_action = "Clique em uma entidade ou conexão do grafo para abrir o contexto principal desta revisão."
        local_blocker = "Sem foco local: selecione um trecho do grafo para destravar conectividade, completude e readiness a partir do canvas."
        primary_button_label = "Abrir bancada completa"
    runs_label = (
        "Ir para Runs"
        if str(summary.get("status") or "").strip().lower() == "ready"
        else "Ir para Runs quando o cenário estiver pronto"
    )
    return html.Div(
        style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginBottom": "14px"},
        children=[
            html.Div("Comece pelo canvas", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(current_focus, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginTop": "12px"},
                children=[
                    _guidance_card("Ação principal agora", canvas_action),
                    _guidance_card("Bloqueio ou liberação local", local_blocker),
                    _guidance_card(
                        "Gate para Runs",
                        str(summary.get("readiness_headline") or "Revise o readiness do cenário antes de abrir a fila."),
                    ),
                ],
            ),
            html.Div(
                style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"},
                children=[
                    html.Button(primary_button_label, id="studio-canvas-open-workbench-button", style=UI_BUTTON_STYLE),
                    html.Button("Abrir orientação deste foco", id="studio-canvas-open-technical-guide-button", style=UI_BUTTON_STYLE),
                    _button_link(runs_label, "?tab=runs", "studio-canvas-open-runs-link", primary=str(summary.get("status") or "").strip().lower() == "ready"),
                ],
            ),
        ],
    )


def render_studio_connectivity_panel(
    summary: dict[str, Any],
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    route_rows: list[dict[str, Any]] | None,
    nodes_rows: list[dict[str, Any]] | None = None,
    candidate_links_rows: list[dict[str, Any]] | None = None,
) -> Any:
    nodes_rows = nodes_rows or []
    candidate_links_rows = candidate_links_rows or []
    route_rows = route_rows or []
    focus_node_ids = {
        str(node_summary.get("selected_node_id") or "").strip(),
        str((edge_summary.get("selected_edge") or {}).get("from_node") or "").strip(),
        str((edge_summary.get("selected_edge") or {}).get("to_node") or "").strip(),
    }
    focus_node_ids = {node_id for node_id in focus_node_ids if node_id}
    prioritized_routes = [
        route
        for route in route_rows
        if str(route.get("source") or "").strip() in focus_node_ids or str(route.get("sink") or "").strip() in focus_node_ids
    ]
    local_rules: list[str] = []
    local_violations: list[str] = []
    global_highlights: list[str] = []
    selected_edge = edge_summary.get("selected_edge") or {}
    selected_node_present = bool(str(node_summary.get("selected_node_id") or "").strip())
    selected_edge_present = bool(selected_edge)
    edge_action_panel: Any = None
    if "W" in focus_node_ids:
        local_rules.append("W só pode iniciar fluxo; nenhuma conexão ou rota deve terminar neste ponto.")
    if "S" in focus_node_ids:
        local_rules.append("S é ponto terminal; nenhuma conexão ou rota deve sair deste ponto.")
    focused_dosing_routes = [
        route
        for route in prioritized_routes
        if float(route.get("dose_min_l") or 0.0) > 0
    ]
    if focused_dosing_routes:
        local_rules.append("Rotas com dosagem exigem medição direta antes de seguir para Runs.")
    if str(selected_edge.get("to_node") or "").strip() == "W":
        local_violations.append("A conexão em foco entra em W; ajuste a direção antes de continuar.")
    if str(selected_edge.get("from_node") or "").strip() == "S":
        local_violations.append("A conexão em foco sai de S; corrija a direção para manter a regra estrutural.")
    for route in prioritized_routes:
        route_id = str(route.get("route_id") or "ROTA")
        if str(route.get("sink") or "").strip() == "W":
            local_violations.append(f"{route_id} tenta terminar em W; essa rota precisa ser redirecionada.")
        if str(route.get("source") or "").strip() == "S":
            local_violations.append(f"{route_id} tenta sair de S; essa rota precisa ser revista.")
        if float(route.get("dose_min_l") or 0.0) > 0 and not _coerce_truthy(route.get("measurement_required")):
            local_violations.append(f"{route_id} usa dosagem sem medição direta compatível.")
    for blocker in list(summary.get("blockers", []))[:4]:
        blocker_text = str(blocker)
        if "entra em W" in blocker_text:
            global_highlights.append("Há conexões entrando em W no cenário; isso ainda bloqueia a passagem para Runs.")
        elif "sai de S" in blocker_text:
            global_highlights.append("Há conexões saindo de S no cenário; isso ainda bloqueia a passagem para Runs.")
        elif blocker_text.startswith("Rotas com dosagem sem medicao direta:"):
            route_ids = blocker_text.split(":", 1)[1].strip()
            global_highlights.append(f"Rotas com dosagem ainda sem medição direta: {route_ids}.")
        elif "referencia source inexistente" in blocker_text:
            global_highlights.append("Há rota apontando para uma origem que não está disponível no grafo principal.")
        elif "referencia sink inexistente" in blocker_text:
            global_highlights.append("Há rota apontando para um destino que não está disponível no grafo principal.")
        else:
            global_highlights.append(blocker_text)
    for warning in list(summary.get("warnings", []))[:2]:
        warning_text = str(warning)
        if warning_text.startswith("Nos sem conexao no grafo visivel:"):
            global_highlights.append("Ainda existem nós sem conexão no grafo visível; a readiness geral continua incompleta.")
        else:
            global_highlights.append(warning_text)
    route_lines = []
    for route in (prioritized_routes or route_rows)[:4]:
        route_id = str(route.get("route_id") or "ROTA")
        source = str(route.get("source") or "-")
        sink = str(route.get("sink") or "-")
        qualifiers = []
        if _coerce_truthy(route.get("mandatory")):
            qualifiers.append("obrigatória")
        if _coerce_truthy(route.get("measurement_required")):
            qualifiers.append("medição direta")
        qualifier_text = f" ({', '.join(qualifiers)})" if qualifiers else ""
        route_lines.append(f"{route_id}: {source} -> {sink}{qualifier_text}")
    if local_violations:
        primary_connectivity_action = local_violations[0]
    elif prioritized_routes and focused_dosing_routes:
        primary_connectivity_action = "Há rotas com dosagem neste foco. Confirme medição direta antes de seguir para Runs."
    elif prioritized_routes:
        primary_connectivity_action = "A seleção atual já mostra o trecho crítico do cenário. Revise conectividade e rotas obrigatórias neste foco."
    else:
        primary_connectivity_action = "Selecione um nó ou uma conexão no canvas para destravar a leitura local de conectividade."
    runs_gate_action = (
        "Não siga para Runs enquanto houver bloqueios estruturais ou rotas com dosagem sem medição direta."
        if int(summary.get("blocker_count", 0) or 0) > 0
        else str((summary.get("next_steps") or ["Com o cenário consistente, siga para Runs para enfileirar a próxima rodada."])[0])
    )
    if selected_edge_present:
        reverse_preview = _build_studio_edge_reverse_preview(
            edge_summary,
            summary,
            route_rows,
            nodes_rows=nodes_rows,
            candidate_links_rows=candidate_links_rows,
        )
        menu_actions = [
            "Abra o menu contextual desta conexão e use Inverter direção para corrigir o fluxo sem abrir o workbench.",
            "Use Remover conexão no mesmo menu apenas se este trecho não fizer mais parte do fluxo principal.",
        ]
        if prioritized_routes:
            menu_actions.insert(
                1,
                f"{reverse_preview['route_scope']} Revise a leitura de origem, destino e medição direta logo após a ação.",
            )
        edge_action_panel = html.Div(
            id="studio-connectivity-edge-action-panel",
            style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginTop": "12px", "marginBottom": "12px"},
            children=[
                html.Div("Trecho acionável no canvas", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                html.Div(reverse_preview["current_flow"], style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                html.Div(
                    style={**UI_THREE_COLUMN_STYLE, "marginTop": "12px"},
                    children=[
                        _guidance_card("Origem do trecho", str(edge_summary.get("from_label") or "-")),
                        _guidance_card("Destino do trecho", str(edge_summary.get("to_label") or "-")),
                        _guidance_card("Impacto agora", reverse_preview["current_effect"]),
                        _guidance_card("Se inverter no canvas", f"{reverse_preview['reverse_preview']} {reverse_preview['reverse_impact']}"),
                        _guidance_card("Rotas tocadas", reverse_preview["route_scope"]),
                    ],
                ),
                html.Div("Ações diretas no menu desta conexão", style={"fontWeight": 700, "marginTop": "12px", "marginBottom": "6px"}),
                _bullet_list(menu_actions, "Abra o menu contextual da conexão para agir diretamente no canvas."),
            ],
        )
    return html.Div(
        children=[
            html.H3("Conectividade do grafo", style={"marginTop": 0}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("O que destrava o cenário", primary_connectivity_action),
                    _guidance_card("Antes de abrir Runs", runs_gate_action),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Bloqueios", summary.get("blocker_count", 0)),
                    _metric_card("Avisos", summary.get("warning_count", 0)),
                    _metric_card("Rotas obrigatórias", summary.get("mandatory_route_count", 0)),
                    _metric_card("Medição direta", summary.get("measurement_route_count", 0)),
                ],
            ),
            edge_action_panel,
            html.Div(
                "Prioridade da seleção atual"
                if prioritized_routes
                else ("Seleção atual ainda não abriu um trecho crítico" if selected_node_present or selected_edge_present else "Prioridade geral do cenário"),
                style={"marginTop": "10px", "fontWeight": 700, "lineHeight": "1.5"},
            ),
            html.H4("Seleção atual", style={"marginBottom": "6px"}),
            _bullet_list(
                list(dict.fromkeys(local_violations + local_rules))[:4],
                "Selecione um nó ou uma conexão no canvas para abrir regras locais e bloqueios diretamente neste painel."
                if not prioritized_routes and not selected_node_present and not selected_edge_present
                else "Nenhuma regra crítica acionada para a seleção atual.",
            ),
            html.H4("Cenário inteiro", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list(
                list(dict.fromkeys(global_highlights))[:4],
                "Nenhum bloqueio sistêmico impede a readiness neste momento.",
            ),
            html.H4("Rotas em foco", style={"marginBottom": "6px"}),
            _bullet_list(route_lines, "Sem rotas registradas para esta leitura."),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list(list(summary.get("next_steps", []))[:2], "Sem próximo passo registrado."),
        ],
    )


def render_studio_focus_panel(
    node_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]] | None,
    readiness_summary: dict[str, Any] | None = None,
    status_text: str | None = None,
) -> Any:
    route_rows = route_rows or []
    readiness_summary = readiness_summary or {}
    selected_node_id = str(node_summary.get("selected_node_id") or "-")
    selected_edge = edge_summary.get("selected_edge") or {}
    selected_edge_id = str(edge_summary.get("selected_link_id") or "-")
    focus_node_ids = {
        selected_node_id if selected_node_id not in {"", "-"} else "",
        str(selected_edge.get("from_node") or "").strip(),
        str(selected_edge.get("to_node") or "").strip(),
    }
    focus_node_ids = {node_id for node_id in focus_node_ids if node_id}
    business_flow = build_studio_business_flow_summary(
        nodes_rows,
        candidate_links_rows,
        route_rows,
        focus_node_ids=focus_node_ids,
    )
    relevant_routes = [
        route
        for route in route_rows
        if focus_node_ids
        and ({str(route.get("source") or "").strip(), str(route.get("sink") or "").strip()} & focus_node_ids)
    ]
    focus_rules: list[str] = []
    selected_node_present = selected_node_id not in {"", "-"}
    selected_edge_present = bool(selected_edge)
    mandatory_route_count = sum(1 for route in relevant_routes if _coerce_truthy(route.get("mandatory")))
    dosing_route_count = sum(1 for route in relevant_routes if float(route.get("dose_min_l") or 0.0) > 0)
    measurement_route_count = sum(1 for route in relevant_routes if _coerce_truthy(route.get("measurement_required")))
    blocker_count = int(readiness_summary.get("blocker_count", 0) or 0)
    warning_count = int(readiness_summary.get("warning_count", 0) or 0)
    if selected_node_id == "W" or str(selected_edge.get("to_node") or "").strip() == "W":
        focus_rules.append("Regra do foco: W não pode receber rotas entrando; use este ponto apenas como origem.")
    if selected_node_id == "S" or str(selected_edge.get("from_node") or "").strip() == "S":
        focus_rules.append("Regra do foco: S não pode originar rotas; use este ponto apenas como destino final.")
    if any(float(route.get("dose_min_l") or 0.0) > 0 for route in relevant_routes):
        focus_rules.append("Regra do foco: rotas com dosagem exigem medição direta compatível.")
    if mandatory_route_count:
        focus_rules.append(f"Regra do foco: {mandatory_route_count} rota(s) obrigatória(s) passam por esta leitura e precisam permanecer legíveis no canvas.")
    edge_breaks_direction_rule = str(selected_edge.get("to_node") or "").strip() == "W" or str(selected_edge.get("from_node") or "").strip() == "S"
    dosing_without_measurement = any(
        float(route.get("dose_min_l") or 0.0) > 0 and not _coerce_truthy(route.get("measurement_required"))
        for route in relevant_routes
    )
    if edge_breaks_direction_rule and selected_edge_present:
        recommended_action_text = "A conexão em foco viola uma regra estrutural do Studio. Remova essa conexão inválida para liberar a revisão do cenário."
        recommended_action_button = html.Button(
            "Remover conexão inválida",
            id="studio-focus-recommended-delete-edge-button",
            style=UI_BUTTON_STYLE,
            disabled=False,
        )
    elif dosing_without_measurement:
        recommended_action_text = "A rota em foco depende de medição direta e exige revisão detalhada. Abra a bancada completa para corrigir a estrutura sem mascarar a regra."
        recommended_action_button = html.Button(
            "Abrir bancada completa",
            id="studio-focus-recommended-open-workbench-button",
            style=UI_BUTTON_STYLE,
        )
    elif selected_edge_present:
        recommended_action_text = "A conexão em foco já concentra a leitura deste trecho. Revise o fluxo no canvas e abra a bancada completa apenas se precisar ajustar comprimento, famílias ou direção."
        recommended_action_button = html.Button(
            "Abrir bancada completa",
            id="studio-focus-recommended-open-workbench-button",
            style=UI_BUTTON_STYLE,
        )
    elif selected_node_present:
        recommended_action_text = "O foco atual permite ajuste rápido de posição no canvas. Reposicione o nó sem sair da primeira dobra e abra a bancada completa só se precisar aprofundar."
        recommended_action_button = html.Button(
            "Mover à direita",
            id="studio-focus-recommended-move-right-button",
            style=UI_BUTTON_STYLE,
            disabled=False,
        )
    else:
        recommended_action_text = "Selecione um nó ou uma conexão no canvas para destravar as ações rápidas deste foco."
        recommended_action_button = html.Button(
            "Abrir bancada completa",
            id="studio-focus-recommended-open-workbench-button",
            style=UI_BUTTON_STYLE,
        )
    focus_objective = (
        "Usar a seleção atual para validar conectividade, regras obrigatórias e readiness sem sair do canvas."
        if selected_node_present or selected_edge_present
        else "Começar pela seleção no canvas para abrir o contexto principal do cenário."
    )
    runs_gate_text = (
        str(readiness_summary.get("primary_action") or "Corrija bloqueios estruturais antes de abrir uma nova run.")
        if blocker_count > 0
        else (
            str((readiness_summary.get("next_steps") or ["Feche os avisos principais e então siga para Runs."])[0])
            if warning_count > 0
            else str(readiness_summary.get("readiness_headline") or "Com o cenário pronto, siga para Runs.")
        )
    )
    readiness_context = []
    if edge_breaks_direction_rule:
        readiness_context.append("Este foco ainda bloqueia a passagem para Runs até a direção da conexão ser corrigida.")
    if dosing_without_measurement:
        readiness_context.append("Há dosagem sem medição direta neste foco; a run oficial não deve seguir enquanto essa regra não estiver fechada.")
    if blocker_count > 0 and not readiness_context:
        readiness_context.append(f"O cenário ainda tem {blocker_count} bloqueio(s) antes de Runs, mesmo que este foco não concentre todos eles.")
    if warning_count > 0 and not readiness_context:
        readiness_context.append(f"O cenário ainda carrega {warning_count} aviso(s); revise este foco antes de enfileirar.")
    if not readiness_context:
        readiness_context.append("Nada neste foco impede a passagem para Runs neste momento.")
    node_next_action = (
        f"Revise as rotas ligadas a {selected_node_id} antes de ajustar posição ou nome."
        if relevant_routes
        else "Use a bancada de edição apenas depois de confirmar se este nó precisa participar de uma rota obrigatória."
    )
    edge_next_action = (
        f"Confira comprimento e famílias sugeridas para a conexão {selected_edge_id}."
        if selected_edge
        else "Selecione uma conexão no canvas para revisar impacto de fluxo e famílias sugeridas."
    )
    if edge_breaks_direction_rule and selected_edge_present:
        selection_state_label = "Conexão em foco"
        selection_state_headline = "A conexão selecionada ainda trava o cenário."
    elif selected_edge_present:
        selection_state_label = "Conexão em foco"
        selection_state_headline = "A conexão selecionada concentra o próximo ajuste do fluxo."
    elif selected_node_present:
        selection_state_label = "Nó em foco"
        selection_state_headline = f"{node_summary.get('business_label') or selected_node_id} já orienta a próxima revisão no canvas."
    else:
        selection_state_label = "Sem seleção"
        selection_state_headline = "Selecione um nó ou uma conexão para abrir o contexto principal do Studio."
    support_items = [
        f"Nó em foco: {node_summary.get('role_label') or '-'} na superfície principal."
        if selected_node_present
        else "Nenhum nó em foco no momento.",
        f"Conexão em foco: {edge_summary.get('from_label') or '-'} -> {edge_summary.get('to_label') or '-'}."
        if selected_edge
        else "Nenhuma conexão em foco no momento.",
        f"Rotas deste foco: {mandatory_route_count} obrigatória(s), {dosing_route_count} com dosagem, {measurement_route_count} com medição direta."
        if relevant_routes
        else "Sem rota ligada a este foco neste momento.",
    ]
    context_highlights = list(
        dict.fromkeys(
            [focus_objective]
            + focus_rules[:2]
            + readiness_context[:2]
        )
    )
    next_steps = list(
        dict.fromkeys(
            [recommended_action_text]
            + ([edge_next_action] if selected_edge_present else [node_next_action])
            + ([] if blocker_count > 0 else [runs_gate_text])
        )
    )
    readiness_note = (
        "Este foco ainda convive com bloqueios antes de Runs."
        if blocker_count > 0
        else ("Este foco ainda pede revisão antes de seguir para Runs." if warning_count > 0 else "Nada neste foco impede a passagem para Runs.")
    )
    readiness_background, readiness_color = _status_tone(readiness_summary.get("status") or "needs_attention")
    selected_node = node_summary.get("selected_node") or {}
    selected_edge_row = edge_summary.get("selected_edge") or {}
    return html.Div(
        children=[
            html.H3("Foco do canvas", style={"marginTop": 0}),
            html.Div(id="studio-status-banner", children=render_status_banner(status_text or "")),
            html.Div(selection_state_label, style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d", "marginTop": "8px"}),
            html.Div(selection_state_headline, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "marginTop": "10px", "flexWrap": "wrap"},
                children=[
                    html.Span(
                        _humanize_readiness_status(readiness_summary.get("status") or "needs_attention"),
                        style={"padding": "6px 10px", "borderRadius": "999px", "background": readiness_background, "color": readiness_color, "fontWeight": 700},
                    ),
                    html.Span(readiness_note, style={"lineHeight": "1.5", "fontWeight": 700}),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px", "marginBottom": "12px"},
                children=[
                    _guidance_card("Problema ou oportunidade", context_highlights[0] if context_highlights else focus_objective),
                    _guidance_card("Próxima ação", recommended_action_text),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Nó em foco", node_summary.get("business_label") or "-"),
                    _metric_card("Conexão em foco", edge_summary.get("business_label") or "-"),
                    _metric_card("Rotas ligadas ao nó", len(relevant_routes)),
                    _metric_card("Readiness", _humanize_readiness_status(readiness_summary.get("status") or "needs_attention")),
                ],
            ),
            html.H4("Relações de negócio deste foco", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginTop": "8px"},
                children=[
                    html.Div(str(business_flow.get("headline") or "Sem relação de negócio legível neste foco."), style={"fontWeight": 700, "lineHeight": "1.6"}),
                    html.Div(
                        style={**UI_THREE_COLUMN_STYLE, "marginTop": "12px"},
                        children=[
                            _guidance_card("É suprido por", str(business_flow.get("supplied_by_label") or "Ainda não recebe suprimento visível.")),
                            _guidance_card("Supre", str(business_flow.get("supplies_label") or "Ainda não abastece outra entidade visível.")),
                            _guidance_card(
                                "Órfãos visíveis",
                                _humanize_label_list(list(business_flow.get("orphan_labels") or [])[:3]) or "Nenhum nó órfão domina a leitura principal.",
                            ),
                        ],
                    ),
                    html.Div("Trechos ligados a este foco", style={"fontWeight": 700, "marginTop": "12px", "marginBottom": "6px"}),
                    _bullet_list(
                        list(business_flow.get("connection_lines") or [])[:4],
                        "Ainda não há trecho legível de suprimento neste foco.",
                    ),
                ],
            ),
            html.H4("Edição direta deste foco", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginTop": "8px"},
                children=[
                    html.Div("Controles rápidos já estão no primeiro fold do Studio.", style={"fontWeight": 700, "lineHeight": "1.5"}),
                    html.Div(
                        "Use o painel local ao lado do canvas para editar rótulo, comprimento, famílias, direção e movimentos comuns sem abrir a bancada avançada.",
                        style={"lineHeight": "1.6", "marginTop": "8px"},
                    ),
                ],
            ),
            html.H4("Por que este foco importa", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list(support_items + context_highlights[1:], "Sem foco atual registrado."),
            html.H4("Ações rápidas deste foco", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "14px", "marginTop": "8px"},
                children=[
                    html.Div("Ação sugerida agora", style={"fontWeight": 700, "marginBottom": "6px"}),
                    html.P(recommended_action_text, style={"marginTop": 0, "lineHeight": "1.6"}),
                    html.Div(style=UI_ACTION_ROW_STYLE, children=[recommended_action_button]),
                ],
            ),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            _bullet_list(next_steps, "Sem próxima ação registrada."),
        ],
    )


def render_studio_selection_panel(summary: dict[str, Any], selection_type: str) -> Any:
    key = "selected_node" if selection_type == "node" else "selected_edge"
    selected = summary.get(key) or {}
    primary_label = str(summary.get("business_label") or "-")
    role_label = str(summary.get("role_label") or ("Entidade" if selection_type == "node" else "Conexão"))
    surface_tone = "Interno oculto" if summary.get("is_internal") else "Superfície principal"
    if not selected:
        selection_label = "entidade" if selection_type == "node" else "conexão"
        empty_state_text = (
            "Selecione um nó no canvas para preparar edição de posição, rótulo e papel operacional desta entidade."
            if selection_type == "node"
            else "Selecione uma conexão no canvas para revisar fluxo, famílias sugeridas e impacto estrutural."
        )
        return html.Div(
            children=[
                html.H4("Seleção ativa", style={"margin": 0}),
                html.Div(f"Nenhuma {selection_label} em foco.", style={"marginTop": "6px", "lineHeight": "1.6"}),
                html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
                html.Div(
                    empty_state_text,
                    style={"lineHeight": "1.6", "fontWeight": 700},
                ),
            ]
        )
    preview: list[str]
    if selection_type == "node":
        preview = [
            f"Posição: x={selected.get('x_m')} m, y={selected.get('y_m')} m",
            str(selected.get("notes", "")).strip(),
        ]
    else:
        from_label = str(summary.get("from_label") or selected.get("from_node") or "-")
        to_label = str(summary.get("to_label") or selected.get("to_node") or "-")
        preview = [
            f"Fluxo principal: {from_label} -> {to_label}",
            f"Comprimento: {selected.get('length_m')} m" if selected.get("length_m") not in (None, "") else "",
            f"Famílias: {selected.get('family_hint')}" if selected.get("family_hint") not in (None, "") else "",
            str(selected.get("notes", "")).strip(),
        ]
    return html.Div(
        children=[
            html.H4("Seleção ativa", style={"margin": 0}),
            html.Div(primary_label, style={"fontSize": "22px", "fontWeight": 700, "marginTop": "6px"}),
            html.Div(
                style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginTop": "8px"},
                children=[html.Span(role_label, style=UI_PILL_STYLE), html.Span(surface_tone, style=UI_PILL_STYLE)],
            ),
            html.Div(
                "Use este resumo para preparar a edição do nó sem tirar o canvas do centro."
                if selection_type == "node"
                else "Use este resumo para preparar a revisão desta conexão antes de abrir campos avançados.",
                style={"marginTop": "10px", "lineHeight": "1.6", "fontWeight": 700},
            ),
            html.Ul(
                [html.Li(item) for item in preview if item],
                style={"margin": "10px 0 0 18px", "lineHeight": "1.5"},
            ),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(
                "Ajuste posição, rótulo e papel deste nó somente depois de confirmar se ele participa da rota que você está revisando."
                if selection_type == "node"
                else "Revise direção, comprimento e famílias sugeridas desta conexão antes de abrir os campos avançados.",
                style={"lineHeight": "1.6", "fontWeight": 700},
            ),
        ]
    )


def render_run_jobs_overview_panel(summary: dict[str, Any]) -> Any:
    status_counts = summary.get("status_counts", {}) if isinstance(summary, dict) else {}
    run_count = int(summary.get("run_count", 0) or 0) if isinstance(summary, dict) else 0
    next_queued_run_id = summary.get("next_queued_run_id") if isinstance(summary, dict) else None
    active_run_ids = list(summary.get("active_run_ids", [])) if isinstance(summary, dict) else []
    queued_run_ids = list(summary.get("queued_run_ids", [])) if isinstance(summary, dict) else []
    latest_run_id = summary.get("latest_run_id") if isinstance(summary, dict) else None
    latest_updated_at = summary.get("latest_updated_at") if isinstance(summary, dict) else None
    failed_count = int(status_counts.get("failed", 0) or 0)
    completed_count = int(status_counts.get("completed", 0) or 0)
    queue_state = _humanize_run_status(summary.get("queue_state", "idle")) if isinstance(summary, dict) else "Sem leitura"
    if active_run_ids:
        queue_headline = "Execução em andamento"
        queue_guidance = f"Há run em andamento agora ({active_run_ids[0]}). Acompanhe essa execução antes de decidir se vale abrir outra rodada."
    elif next_queued_run_id:
        queue_headline = "Fila pronta para a próxima rodada"
        queue_guidance = f"Há uma run pronta na fila: {next_queued_run_id}. Revise a run em foco ou execute o próximo job."
    elif failed_count and not completed_count:
        queue_headline = "Histórico ainda exige revisão"
        queue_guidance = "A fila não tem pendências, mas as últimas execuções falharam. Revise a run em foco antes de reenfileirar."
    elif run_count:
        queue_headline = "Histórico recente disponível"
        queue_guidance = "A fila está sem pendências no momento. Use a run em foco para revisar o último estado antes de decidir o próximo passo."
    else:
        queue_headline = "Nenhuma execução registrada"
        queue_guidance = "Nenhuma run registrada ainda. Enfileire o cenário atual para iniciar a trilha operacional."
    return html.Div(
        children=[
            html.H3("Resumo da fila", style={"marginTop": 0}),
            html.Div(queue_headline, style={"fontWeight": 700, "lineHeight": "1.5", "marginBottom": "10px"}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Objetivo desta área", "Entender o que já rodou, o que ainda está na fila e qual run merece sua atenção agora."),
                    _guidance_card("Próxima ação", queue_guidance),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Runs", summary.get("run_count", 0), "Total observavel na fila local."),
                    _metric_card("Estado da fila", queue_state, "fila serial local"),
                    _metric_card("Em execução", len(active_run_ids)),
                    _metric_card("Na fila", len(queued_run_ids)),
                    _metric_card("Concluídas", completed_count),
                    _metric_card("Falhas", failed_count),
                    _metric_card("Próxima run", summary.get("next_queued_run_id") or "-", "Entrada seguinte da fila"),
                ],
            ),
            html.Details(
                id="run-jobs-overview-history-details",
                style={**UI_MUTED_CARD_STYLE, "marginTop": "14px"},
                children=[
                    html.Summary("Leitura operacional detalhada"),
                    html.Div(
                        id="run-jobs-overview-history-block",
                        children=[
                            html.H4("Fila agora", style={"marginBottom": "6px", "marginTop": "12px"}),
                            _bullet_list(
                                [
                                    f"Em execução: {', '.join(active_run_ids[:2])}" if active_run_ids else "",
                                    f"Próxima a rodar: {next_queued_run_id}" if next_queued_run_id else "",
                                ],
                                "Sem run ativa ou aguardando nesta leitura.",
                            ),
                            html.H4("Histórico recente", style={"marginBottom": "6px", "marginTop": "14px"}),
                            _bullet_list(
                                [
                                    f"Última run conhecida: {latest_run_id}" if latest_run_id else "",
                                    f"Última atualização observada: {latest_updated_at}" if latest_updated_at else "",
                                    f"Runs terminais registradas: {len(summary.get('terminal_run_ids', []))}" if isinstance(summary, dict) else "",
                                ],
                                "Ainda não há histórico recente para leitura.",
                            ),
                            html.H4("Status por quantidade", style={"marginBottom": "6px", "marginTop": "14px"}),
                            _bullet_list(
                                [f"{_humanize_run_status(status)}: {count}" for status, count in status_counts.items()],
                                "Ainda não há histórico suficiente para distribuir a fila por status.",
                            ),
                            html.H4("Contexto operacional", style={"marginBottom": "6px", "marginTop": "14px"}),
                            _bullet_list(
                                [f"Worker local: {summary.get('worker_mode') or '-'}"],
                                "Sem contexto operacional adicional.",
                            ),
                        ],
                    ),
                ],
            ),
        ]
    )


def _runs_primary_state(
    studio_summary: dict[str, Any],
    run_summary: dict[str, Any],
    execution_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    studio_status = str(studio_summary.get("status") or "needs_attention")
    run_count = int(run_summary.get("run_count", 0) or 0) if isinstance(run_summary, dict) else 0
    next_queued_run_id = run_summary.get("next_queued_run_id") if isinstance(run_summary, dict) else None
    queue_state = _humanize_run_status((run_summary or {}).get("queue_state", "idle")) if isinstance(run_summary, dict) else "Sem leitura"
    active_run_ids = list((run_summary or {}).get("active_run_ids", [])) if isinstance(run_summary, dict) else []
    failed_count = int((run_summary or {}).get("status_counts", {}).get("failed", 0) or 0) if isinstance(run_summary, dict) else 0
    execution_summary = execution_summary or {}
    execution_error = str(execution_summary.get("error") or "").strip()
    decision_available = bool(execution_summary.get("selected_candidate_id") and not execution_error)
    if studio_status != "ready":
        readiness_note = "O Studio ainda sinaliza bloqueios ou avisos relevantes para o enfileiramento."
        flow_state = "Aguardando readiness do Studio"
        headline = str(studio_summary.get("readiness_headline") or readiness_note)
        next_action = "Volte ao Studio para corrigir conectividade, regras obrigatórias e medição direta antes de abrir uma nova run."
        decision_gate = "A passagem para Decisão continua secundária até o Studio liberar o gate principal de readiness."
        decision_button_label = "Decisão ainda secundária"
        decision_enabled = False
    elif active_run_ids:
        readiness_note = "O cenário já passou pelo gate principal de prontidão do Studio."
        flow_state = "Execução em andamento"
        headline = f"Há uma run em andamento agora ({active_run_ids[0]})."
        next_action = "Acompanhe a run em foco antes de abrir uma nova rodada ou esperar uma decisão utilizável."
        decision_gate = "A execução atual ainda não consolidou um resultado utilizável para a Decisão."
        decision_button_label = "Aguardar execução atual"
        decision_enabled = False
    elif next_queued_run_id and not decision_available:
        readiness_note = "O cenário já passou pelo gate principal de prontidão do Studio."
        flow_state = "Fila pronta"
        headline = f"Há uma run pronta na fila ({next_queued_run_id})."
        next_action = "Revise a fila e execute apenas a próxima rodada necessária antes de abrir Decisão."
        decision_gate = "Ainda falta um resultado utilizável; execute ou revise a próxima run antes de avançar."
        decision_button_label = "Gerar resultado utilizável"
        decision_enabled = False
    elif execution_error:
        readiness_note = "O cenário já passou pelo gate principal de prontidão do Studio."
        flow_state = "Resultado bloqueado"
        headline = "A última execução terminou com bloqueio operacional."
        next_action = "Corrija o bloqueio operacional antes de confiar em qualquer leitura de ranking ou candidato oficial."
        decision_gate = "A Decisão permanece bloqueada enquanto o resumo executivo carregar erro crítico."
        decision_button_label = "Decisão bloqueada nesta execução"
        decision_enabled = False
    elif decision_available:
        readiness_note = "O cenário já passou pelo gate principal de prontidão do Studio."
        flow_state = "Decisão disponível"
        headline = "A última execução já gerou contexto suficiente para entrar em Decisão."
        next_action = "Abra a Decisão para confirmar winner, runner-up e sinais de risco antes de oficializar."
        decision_gate = "Já existe um resultado utilizável; a passagem para Decisão está liberada."
        decision_button_label = "Ir para Decisão"
        decision_enabled = True
    elif run_count:
        readiness_note = "O cenário já passou pelo gate principal de prontidão do Studio."
        flow_state = "Sem resultado utilizável"
        headline = "Há histórico de runs, mas ainda sem resultado utilizável para decisão."
        next_action = "Revise a última execução ou reexecute o pipeline até obter um candidato oficial comparável."
        decision_gate = "A Decisão segue secundária até existir winner legível sem bloqueio crítico."
        decision_button_label = "Gerar resultado utilizável"
        decision_enabled = False
    else:
        readiness_note = "O cenário já passou pelo gate principal de prontidão do Studio."
        flow_state = "Sem runs"
        headline = "Ainda não há execução registrada para abrir leitura operacional útil."
        next_action = "Enfileire o cenário atual antes de esperar fila, execução ativa ou Decisão disponível."
        decision_gate = "A passagem para Decisão ainda depende da primeira execução utilizável."
        decision_button_label = "Enfileirar antes da Decisão"
        decision_enabled = False
    return {
        "studio_status": studio_status,
        "run_count": run_count,
        "next_queued_run_id": next_queued_run_id,
        "queue_state": queue_state,
        "active_run_ids": active_run_ids,
        "failed_count": failed_count,
        "readiness_note": readiness_note,
        "flow_state": flow_state,
        "headline": headline,
        "next_action": next_action,
        "decision_gate": decision_gate,
        "decision_button_label": decision_button_label,
        "decision_enabled": decision_enabled,
    }


def render_runs_workspace_panel(
    studio_summary: dict[str, Any],
    run_summary: dict[str, Any],
    execution_summary: dict[str, Any] | None = None,
) -> Any:
    state = _runs_primary_state(studio_summary, run_summary, execution_summary)
    active_run_ids = list(state["active_run_ids"])
    next_queued_run_id = state["next_queued_run_id"]
    latest_run_id = run_summary.get("latest_run_id") if isinstance(run_summary, dict) else None
    queued_count = len(list((run_summary or {}).get("queued_run_ids", []))) if isinstance(run_summary, dict) else 0
    if active_run_ids:
        queue_focus = f"Execução em foco: {active_run_ids[0]}."
    elif next_queued_run_id:
        queue_focus = f"Próxima run pronta: {next_queued_run_id}."
    elif latest_run_id:
        queue_focus = f"Última run observada: {latest_run_id}."
    else:
        queue_focus = "Nenhuma run registrada ainda."
    if state["decision_enabled"]:
        decision_cta: Any = html.Button("Ir para Decisão", id="runs-workspace-open-decision-button", style=UI_BUTTON_STYLE, disabled=False)
    else:
        decision_cta = html.Button(state["decision_button_label"], id="runs-workspace-open-decision-button", style=UI_BUTTON_STYLE, disabled=True)
    return html.Div(
        children=[
            html.Div("Leitura operacional de Runs", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 12px", "flexWrap": "wrap"},
                children=[
                    html.Span(state["flow_state"], style=UI_PILL_STYLE),
                    html.Span(state["headline"], style={"fontWeight": 700, "lineHeight": "1.5"}),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("O que esta área resolve", "Transformar readiness do Studio em fila, execução e próxima ação legíveis, sem depender de logs brutos."),
                    _guidance_card("Estado atual", state["headline"]),
                    _guidance_card("Gate do cenário", str(studio_summary.get("readiness_headline") or state["readiness_note"])),
                    _guidance_card("Fila agora", queue_focus),
                    _guidance_card("Próxima ação", state["next_action"]),
                ],
            ),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "12px", "marginBottom": "12px"},
                children=[
                    html.Div("O que move a jornada agora", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(state["decision_gate"], style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                    html.Div(queue_focus, style={"lineHeight": "1.6", "marginTop": "10px"}),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Estado dominante", state["flow_state"]),
                    _metric_card("Runs locais", state["run_count"]),
                    _metric_card("Na fila", queued_count),
                    _metric_card("Em execução", len(active_run_ids)),
                    _metric_card("Falhas recentes", state["failed_count"]),
                    _metric_card("Próxima run", next_queued_run_id or "-"),
                ],
            ),
            html.Div(
                style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"},
                children=[
                    _button_link("Voltar ao Studio", "?tab=studio", "runs-workspace-open-studio-link"),
                    decision_cta,
                    _button_link("Abrir Auditoria", "?tab=audit", "runs-workspace-open-audit-link"),
                ],
            ),
        ]
    )


def render_runs_flow_panel(
    studio_summary: dict[str, Any],
    run_summary: dict[str, Any],
    execution_summary: dict[str, Any] | None = None,
) -> Any:
    state = _runs_primary_state(studio_summary, run_summary, execution_summary)
    return html.Div(
        children=[
            _screen_opening_panel(
                "Camada detalhada de Runs",
                state["headline"],
                "Transformar readiness do Studio em uma leitura clara de fila, execução e próximo passo.",
                state["next_action"],
                [
                    ("Estado dominante", state["flow_state"]),
                    ("Estado do cenário", str(studio_summary.get("readiness_headline") or state["readiness_note"])),
                    ("Entrada da Decisão", state["decision_gate"]),
                ],
                [
                    _button_link("Voltar ao Studio", "?tab=studio", "runs-flow-open-studio-link"),
                    html.Button(state["decision_button_label"], id="runs-flow-open-decision-button", style=UI_BUTTON_STYLE, disabled=not state["decision_enabled"]),
                ],
            ),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginTop": "14px"},
                children=[
                    _metric_card("Estado dominante", state["flow_state"], state["next_action"]),
                    _metric_card("Readiness", _humanize_readiness_status(state["studio_status"]), state["readiness_note"]),
                    _metric_card("Bloqueios", studio_summary.get("blocker_count", 0)),
                    _metric_card("Avisos", studio_summary.get("warning_count", 0)),
                    _metric_card("Runs locais", state["run_count"]),
                    _metric_card("Próxima run", state["next_queued_run_id"] or "-"),
                    _metric_card("Estado da fila", state["queue_state"]),
                    _metric_card("Falhas recentes", state["failed_count"]),
                ],
            ),
        ]
    )


def render_run_job_detail_panel(detail: dict[str, Any]) -> Any:
    if not detail or not detail.get("selected_run_id"):
        return _guided_empty_state(
            "Run em foco",
            "Ainda não existe uma run em foco para leitura operacional.",
            "Selecione uma run da fila ou enfileire o cenário atual para abrir este espaço com contexto real.",
        )
    status = str(detail.get("status") or "unknown")
    gate_valid = detail.get("official_gate_valid")
    if gate_valid is True:
        gate_label = "Julia oficial validado"
    elif gate_valid is False:
        gate_label = "Julia oficial bloqueado"
    else:
        gate_label = "Gate oficial não informado"
    if status == "queued":
        next_action = "Execute o próximo job quando o cenário estiver pronto, ou cancele a fila se a preparação ainda estiver incompleta."
    elif status == "preparing":
        next_action = "A run já saiu da fila e está preparando artefatos. Aguarde essa etapa antes de avaliar resultado."
    elif status == "running":
        next_action = "Acompanhe a execução em foco e evite abrir uma nova run até este job concluir."
    elif status == "exporting":
        next_action = "A run já concluiu o cálculo principal e está finalizando artefatos. Aguarde a consolidação antes de abrir Decisão."
    elif status == "completed":
        next_action = "Leia o resumo executivo e siga para Decisão se a run já gerou um candidato oficial confiável."
    elif status in {"failed", "canceled"}:
        next_action = "Revise o bundle e o status técnico antes de reexecutar esta run."
    else:
        next_action = "Confirme o estado desta run antes de decidir entre executar, cancelar ou reprocessar."
    return html.Div(
        children=[
            html.H3("Run em foco", style={"marginTop": 0}),
            html.Div(str(detail.get("selected_run_id")), style={"fontSize": "22px", "fontWeight": 700}),
            html.Div(
                style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginTop": "8px"},
                children=[
                    html.Span(_humanize_run_status(status), style=UI_PILL_STYLE),
                    html.Span(str(detail.get("requested_execution_mode") or detail.get("execution_mode") or "n/a"), style=UI_PILL_STYLE),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Gate oficial", gate_label),
                    _metric_card("Duração (s)", detail.get("duration_s") or "-"),
                    _metric_card("Modo da rodada", detail.get("policy_mode") or "-"),
                ],
            ),
            html.H4("Leitura operacional", style={"marginBottom": "6px"}),
            _label_value_list(
                [
                    ("Bundle de origem", detail.get("source_bundle_root")),
                    ("Engine utilizado", detail.get("engine_used")),
                    ("Execução pedida", detail.get("requested_execution_mode") or detail.get("execution_mode")),
                ]
            ),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(next_action, style={"lineHeight": "1.6", "fontWeight": 700}),
        ]
    )


def render_execution_summary_panel(summary: dict[str, Any]) -> Any:
    if not summary:
        return _guided_empty_state(
            "Resumo executivo",
            "Ainda não há resultado executivo suficiente para abrir a leitura principal deste espaço.",
            "Execute uma run em Runs para gerar candidato oficial, viabilidade e bundle analisado.",
        )
    error = str(summary.get("error") or "").strip()
    has_selected_candidate = bool(summary.get("selected_candidate_id"))
    can_open_decision = bool(has_selected_candidate and not error)
    if error:
        state_label = "Resultado bloqueado"
        headline = "Última execução exige revisão"
        next_action = "Corrija o bloqueio operacional antes de confiar em qualquer leitura de ranking ou candidato oficial."
    elif has_selected_candidate:
        state_label = "Decisão disponível"
        headline = "Última execução disponível para decisão"
        next_action = "Revise o candidato oficial e siga para a comparação lado a lado quando precisar confirmar a escolha."
    else:
        state_label = "Sem resultado utilizável"
        headline = "Ainda sem candidato oficial"
        next_action = "Reexecute o pipeline quando o cenário estiver pronto para gerar uma leitura comparável."
    decision_button_label = "Abrir Decisão desta execução" if can_open_decision else "Decisão indisponível nesta execução"
    return html.Div(
        children=[
            html.H3("Resumo executivo", style={"marginTop": 0}),
            html.Div(headline, style={"fontWeight": 700, "lineHeight": "1.5", "marginBottom": "10px"}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Estado dominante", state_label),
                    _guidance_card("Objetivo desta área", "Mostrar se a última execução já gerou contexto suficiente para entrar em Decisão."),
                    _guidance_card("Próxima ação", next_action),
                ],
            ),
            html.Div(style=UI_THREE_COLUMN_STYLE, children=[_metric_card("Candidatos", summary.get("candidate_count", 0)), _metric_card("Viáveis", summary.get("feasible_count", 0)), _metric_card("Selecionado", summary.get("selected_candidate_id") or "-", str(summary.get("default_profile_id") or ""))]),
            html.Details(
                id="execution-summary-context-details",
                style={**UI_MUTED_CARD_STYLE, "marginTop": "14px"},
                children=[
                    html.Summary("Contexto técnico secundário desta execução"),
                    html.Div(
                        id="execution-summary-context-list",
                        children=_label_value_list(
                            [
                                ("Bundle analisado", summary.get("scenario_bundle_root")),
                                ("Perfil padrão", summary.get("default_profile_id")),
                                ("Erro operacional", error or "sem bloqueio crítico"),
                            ]
                        ),
                    ),
                ],
            ),
            html.Div(
                style=UI_ACTION_ROW_STYLE,
                children=[html.Button(decision_button_label, id="execution-open-decision-button", style=UI_BUTTON_STYLE, disabled=not can_open_decision)],
            ),
        ]
    )


def render_bundle_io_panel(summary: dict[str, Any]) -> Any:
    status = str(summary.get("status") or "idle")
    if status == "error":
        next_action = "Corrija o bloqueio de persistência antes de confiar neste bundle como fonte canônica."
        state_text = "A trilha canônica precisa de correção antes de seguir."
    else:
        next_action = "Use este espaço quando precisar salvar, reabrir ou reconciliar o bundle canônico fora do fluxo principal."
        state_text = "Bundle canônico pronto para auditoria e persistência."
    return html.Div(
        children=[
            html.Div(style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginBottom": "8px"}, children=[html.Span(_humanize_audit_status(status), style=UI_PILL_STYLE), html.Span(str(summary.get("bundle_version") or "-"), style=UI_PILL_STYLE)]),
            html.Div("Estado atual", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(state_text, style={"lineHeight": "1.6", "fontWeight": 700, "margin": "6px 0 8px"}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Objetivo desta área", "Guardar a trilha canônica e a persistência do cenário sem recolocar isso na superfície principal."),
                    _guidance_card("Estado do bundle", state_text),
                    _guidance_card("Próxima ação", next_action),
                ],
            ),
            html.Details(
                id="bundle-io-address-details",
                style={**UI_MUTED_CARD_STYLE, "marginTop": "14px"},
                children=[
                    html.Summary("Endereços canônicos e manifesto"),
                    html.Div(
                        id="bundle-io-address-list",
                        children=[
                            html.Div(f"Raiz canonica: {summary.get('canonical_scenario_root') or '-'}", style={"lineHeight": "1.6"}),
                            html.Div(f"Manifesto: {summary.get('bundle_manifest') or '-'}", style={"lineHeight": "1.6"}),
                        ],
                    ),
                ],
            ),
        ]
    )


def render_audit_workspace_panel(
    bundle_summary: dict[str, Any],
    execution_summary: dict[str, Any] | None = None,
) -> Any:
    execution_summary = execution_summary or {}
    status = str(bundle_summary.get("status") or "idle")
    bundle_state = _humanize_audit_status(status)
    decision_available = bool(execution_summary.get("selected_candidate_id") and not str(execution_summary.get("error") or "").strip())
    if status == "error":
        headline = "A trilha canônica exige correção antes de sustentar persistência ou reconciliação."
        next_action = "Corrija o bloqueio do bundle antes de usar Auditoria como fonte confiável de explicabilidade."
    else:
        headline = "Auditoria permanece disponível como trilha avançada, sem competir com Studio, Runs ou Decisão."
        next_action = "Entre aqui apenas quando a leitura principal não bastar para reconciliar bundle, YAMLs ou contrato técnico."
    primary_return_label = "Voltar para Decisão" if decision_available else "Voltar para Runs"
    primary_return_href = "?tab=decision" if decision_available else "?tab=runs"
    return html.Div(
        children=[
            html.Div("Trilha avançada", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 12px", "flexWrap": "wrap"},
                children=[
                    html.Span(bundle_state, style=UI_PILL_STYLE),
                    html.Span(headline, style={"fontWeight": 700, "lineHeight": "1.5"}),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("O que esta área resolve", "Reconciliar bundle, persistência e evidência técnica sem competir com Studio, Runs ou Decisão."),
                    _guidance_card("Estado atual", headline),
                    _guidance_card("Quando entrar aqui", "Quando bundle canônico, YAMLs, persistência ou tabelas completas forem necessários para reconciliar a trilha técnica."),
                    _guidance_card("Quando não entrar aqui", "Quando a próxima ação ainda for preparar o cenário, revisar a fila ou comparar winner e runner-up."),
                    _guidance_card("Próxima ação", next_action),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Estado do bundle", bundle_state),
                    _metric_card("Versão do bundle", bundle_summary.get("bundle_version") or "-"),
                    _metric_card("Manifesto", "Disponível" if bundle_summary.get("bundle_manifest") else "Sem manifesto"),
                    _metric_card("Resultado executivo", execution_summary.get("selected_candidate_id") or "Sem candidato"),
                ],
            ),
            html.Div(
                style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"},
                children=[
                    _button_link(primary_return_label, primary_return_href, "audit-workspace-return-primary-link"),
                    _button_link("Voltar ao Studio", "?tab=studio", "audit-workspace-open-studio-link"),
                ],
            ),
        ]
    )


def render_catalog_state_panel(summary: dict[str, Any]) -> Any:
    visible_family_summary = summary.get("visible_family_summary") or []
    visible_candidate_count = int(summary.get("visible_candidate_count", 0) or 0)
    top_family = visible_family_summary[0]["topology_family"] if visible_family_summary else "-"
    if visible_candidate_count == 0:
        return _guided_empty_state(
            "Leitura atual da decisão",
            "Nenhum candidato ficou visível com os filtros e o perfil atuais.",
            "Revise filtros, fallback e viabilidade antes de concluir que ainda não há leitura comparável.",
        )
    return html.Div(
        children=[
            html.H3("Leitura atual da decisão", style={"marginTop": 0}),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Objetivo desta área", "Mostrar quantos candidatos seguem visíveis e quem lidera a leitura atual."),
                    _guidance_card("Próxima ação", "Ajuste filtros e pesos só o suficiente para manter um conjunto comparável antes de aprofundar o candidato em foco."),
                ],
            ),
            html.Div(style=UI_THREE_COLUMN_STYLE, children=[_metric_card("Visiveis", visible_candidate_count), _metric_card("Selecionado", summary.get("selected_candidate_id") or "-"), _metric_card("Familia lider", top_family)]),
            html.Div(f"Topo visivel: {summary.get('top_visible_candidate_id') or '-'}", style={"marginTop": "10px"}),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(
                "Ajuste filtros e pesos só o suficiente para manter um conjunto comparável antes de aprofundar o candidato em foco.",
                style={"lineHeight": "1.6", "fontWeight": 700},
            ),
        ]
    )


def render_candidate_summary_panel(summary: dict[str, Any]) -> Any:
    if not summary:
        return _guided_empty_state(
            "Candidato em foco",
            "Ainda não há candidato visível para leitura neste espaço.",
            "Volte para Runs ou alivie os filtros da Decisão para recuperar um candidato comparável.",
        )
    total_cost = round(float(summary.get("install_cost") or 0.0) + float(summary.get("fallback_cost") or 0.0), 3)
    feasibility_label = "Viável" if summary.get("feasible") else "Inviável"
    infeasibility_reason = str(summary.get("infeasibility_reason") or "").strip()
    if infeasibility_reason:
        primary_blocker = f"Inviável agora: {_humanize_infeasibility_reason(infeasibility_reason)}."
        next_action = "Use o runner-up e os sinais de risco para decidir se vale revisar o cenário antes de oficializar."
    elif summary.get("critical_routes"):
        top_route = list(summary.get("critical_routes", []))[0]
        route_id = str(top_route.get("route_id") or "-")
        route_reason = _humanize_route_issue(top_route.get("reason"))
        primary_blocker = f"Rota crítica {route_id}: {route_reason}."
        next_action = "Confirme se a rota crítica ainda sustenta a escolha antes de exportar o candidato."
    elif int(summary.get("fallback_component_count") or 0) > 0:
        primary_blocker = "A alternativa continua viável, mas depende de fallback para fechar a composição."
        next_action = "Compare com o runner-up antes de oficializar uma alternativa dependente de fallback."
    else:
        primary_blocker = "Nenhum bloqueio principal domina a leitura deste candidato."
        next_action = "Use o circuito primário e o contraste com o runner-up para confirmar a escolha final."
    return html.Div(
        children=[
            html.H3("Candidato em foco", style={"marginTop": 0}),
            html.Div(str(summary.get("candidate_id") or "-"), style={"fontSize": "22px", "fontWeight": 700}),
            html.Div(style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginTop": "8px"}, children=[html.Span(str(summary.get("topology_family") or "-"), style=UI_PILL_STYLE), html.Span(feasibility_label, style=UI_PILL_STYLE)]),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px", "marginTop": "12px"},
                children=[
                    _guidance_card("Bloqueio principal", primary_blocker),
                    _guidance_card("Próxima ação", next_action),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Custo total", total_cost),
                    _metric_card("Score", summary.get("score_final") or "-"),
                    _metric_card("Fallbacks", summary.get("fallback_component_count") or 0),
                ],
            ),
            html.H4("Leitura operacional", style={"marginBottom": "6px"}),
            _label_value_list(
                [
                    ("Engine de avaliação", summary.get("engine_used")),
                    ("Motivo de inviabilidade", _humanize_infeasibility_reason(summary.get("infeasibility_reason"))),
                ]
            ),
        ]
    )


def render_decision_workspace_panel(summary: dict[str, Any], catalog_summary: dict[str, Any]) -> Any:
    decision_state = _decision_primary_state(summary)
    candidate_id = str(summary.get("candidate_id") or "").strip()
    runner_up_id = str(summary.get("runner_up_candidate_id") or "").strip()
    decision_status = str(summary.get("decision_status") or ("technical_tie" if summary.get("technical_tie") else "winner_clear"))
    visible_candidate_count = int(catalog_summary.get("visible_candidate_count", 0) or 0) if isinstance(catalog_summary, dict) else 0
    if not candidate_id:
        state_background, state_color = _status_tone("needs_attention")
        signal_text = "Ainda não existe winner legível; a prioridade continua sendo recuperar uma execução comparável em Runs."
        runs_label = "Voltar para Runs"
        audit_primary = False
    elif decision_status == "technical_tie":
        state_background, state_color = _status_tone("technical_tie")
        signal_text = "Technical tie explícito: mantenha winner e runner-up visíveis antes de qualquer oficialização."
        runs_label = "Revisar Runs"
        audit_primary = True
    elif summary.get("feasible") is False:
        state_background, state_color = _status_tone("blocked")
        signal_text = f"Winner ainda bloqueado por {_humanize_infeasibility_reason(summary.get('infeasibility_reason'))}."
        runs_label = "Revisar Runs"
        audit_primary = False
    else:
        state_background, state_color = _status_tone("ready")
        signal_text = "Winner e runner-up já aparecem com leitura utilizável; aprofunde Auditoria só se precisar reconciliar a trilha técnica."
        runs_label = "Voltar para Runs"
        audit_primary = True
    return html.Div(
        children=[
            html.Div("Leitura principal da decisão", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "margin": "8px 0 12px", "flexWrap": "wrap"},
                children=[
                    html.Span(decision_state["state_label"], style={"padding": "6px 10px", "borderRadius": "999px", "background": state_background, "color": state_color, "fontWeight": 700}),
                    html.Span(decision_state["headline"], style={"fontWeight": 700, "lineHeight": "1.5"}),
                ],
            ),
            html.Div(
                style={**UI_TWO_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("O que esta área resolve", "Transformar a última execução utilizável em leitura comparável entre winner, runner-up e risco principal."),
                    _guidance_card("Estado atual", decision_state["headline"]),
                    _guidance_card("Winner atual", candidate_id or "Ainda sem winner oficial legível"),
                    _guidance_card("Runner-up", runner_up_id or "Ainda sem runner-up comparável"),
                    _guidance_card("Próxima ação", decision_state["next_action"]),
                ],
            ),
            html.Div(
                style={**UI_MUTED_CARD_STYLE, "padding": "12px", "marginBottom": "12px"},
                children=[
                    html.Div("O que esta decisão pede agora", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                    html.Div(signal_text, style={"fontWeight": 700, "lineHeight": "1.5", "marginTop": "6px"}),
                    html.Div(decision_state["contrast_state"], style={"lineHeight": "1.6", "marginTop": "10px"}),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Estado dominante", decision_state["state_label"]),
                    _metric_card("Candidatos visíveis", visible_candidate_count),
                    _metric_card("Technical tie", "Explícito" if decision_status == "technical_tie" else "Não ativo"),
                    _metric_card("Winner", candidate_id or "-"),
                    _metric_card("Runner-up", runner_up_id or "-"),
                    _metric_card("Família líder", summary.get("topology_family") or catalog_summary.get("top_visible_family") or "-"),
                ],
            ),
            html.Div(
                style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"},
                children=[
                    _button_link(runs_label, "?tab=runs", "decision-workspace-open-runs-link"),
                    _button_link("Abrir Auditoria", "?tab=audit", "decision-workspace-open-audit-link", primary=audit_primary),
                ],
            ),
        ]
    )


def render_decision_flow_panel(summary: dict[str, Any]) -> Any:
    decision_state = _decision_primary_state(summary)
    candidate_id = str(summary.get("candidate_id") or "").strip()
    runner_up_id = str(summary.get("runner_up_candidate_id") or "").strip()
    decision_status = str(summary.get("decision_status") or ("technical_tie" if summary.get("technical_tie") else "winner_clear"))
    feasible_is_false = summary.get("feasible") is False
    score_margin_delta = _coerce_float_or_none(summary.get("score_margin_delta"))
    winner_penalties = list(summary.get("winner_penalties", []))
    critical_routes = list(summary.get("critical_routes", []))
    if not candidate_id:
        signal_title = "Sem decisão utilizável"
        signal_text = "Ainda não existe run comparável suficiente para mostrar winner, runner-up e technical tie com honestidade."
    elif decision_status == "technical_tie":
        signal_title = "Empate técnico ativo"
        signal_text = "Winner e runner-up seguem próximos o suficiente para exigir leitura humana assistida antes da oficialização."
    elif feasible_is_false:
        signal_title = "Winner ainda bloqueado"
        signal_text = f"A leitura principal ainda carrega inviabilidade: {_humanize_infeasibility_reason(summary.get('infeasibility_reason'))}."
    elif critical_routes:
        top_route = critical_routes[0]
        signal_title = "Risco principal"
        signal_text = f"Rota crítica {top_route.get('route_id') or '-'}: {_humanize_route_issue(top_route.get('reason'))}."
    elif winner_penalties:
        signal_title = "Risco principal"
        signal_text = f"A escolha oficial ainda carrega penalidade relevante: {winner_penalties[0]}."
    elif score_margin_delta is not None and score_margin_delta <= 0.5:
        signal_title = "Contraste fraco"
        signal_text = "Winner e runner-up estão separados por margem curta; confirme o contraste antes de oficializar."
    else:
        signal_title = "Contraste suficiente"
        signal_text = "Winner e runner-up já aparecem com separação legível para a decisão assistida."
    runs_cta_label = "Voltar para Runs"
    runs_primary = False
    audit_primary = True
    if not candidate_id or feasible_is_false:
        runs_cta_label = "Revisar Runs" if candidate_id else "Voltar para Runs"
        runs_primary = True
        audit_primary = False
    return html.Div(
        children=[
            _screen_opening_panel(
                "Passagem Runs -> Decisão",
                decision_state["headline"],
                "Explicar se a execução atual já pode ser lida como decisão ou se ainda falta contexto.",
                decision_state["next_action"],
                [
                    ("Estado dominante", decision_state["state_label"]),
                    ("Winner atual", candidate_id or "Ainda sem candidato oficial legível."),
                    ("Saída do fluxo", decision_state["next_action"]),
                ],
                [
                    _button_link(runs_cta_label, "?tab=runs", "decision-flow-open-runs-link", primary=runs_primary),
                    _button_link("Abrir Auditoria", "?tab=audit", "decision-flow-open-audit-link", primary=audit_primary),
                ],
            ),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginTop": "14px"},
                children=[
                    _guidance_card(
                        "Winner oficial",
                        (
                            f"{decision_state['winner_guidance']} Família principal: {summary.get('topology_family') or '-'}."
                            if candidate_id
                            else decision_state["winner_guidance"]
                        ),
                    ),
                    _guidance_card(
                        "Runner-up de referência",
                        (
                            f"{decision_state['runner_up_guidance']} Família comparável: {summary.get('runner_up_topology_family') or '-'}."
                            if runner_up_id
                            else decision_state["runner_up_guidance"]
                        ),
                    ),
                    _guidance_card("Estado da decisão", f"{signal_title}. {signal_text}"),
                ],
            ),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginTop": "14px"},
                children=[
                    _metric_card("Winner", candidate_id or "-"),
                    _metric_card("Runner-up", runner_up_id or "-"),
                    _metric_card("Leitura atual", decision_state["state_label"] if candidate_id or summary else _humanize_decision_status(decision_status)),
                ],
            ),
        ],
    )


def render_decision_summary_panel(summary: dict[str, Any]) -> Any:
    candidate_id = str(summary.get("candidate_id") or "").strip()
    if not summary or not candidate_id:
        return _guided_empty_state(
            "Winner oficial",
            "Ainda não existe decisão utilizável para oficializar um winner nesta leitura.",
            "Revise a última execução em Runs e retorne quando houver resultado comparável.",
        )
    decision_state = _decision_primary_state(summary)
    decision_status = str(summary.get("decision_status") or ("technical_tie" if summary.get("technical_tie") else "winner_clear"))
    decision_label = decision_state["state_label"]
    feasibility_label = "Inviável" if summary.get("feasible") is False else "Viável"
    score_margin_delta = _coerce_float_or_none(summary.get("score_margin_delta"))
    if decision_status == "technical_tie":
        priority_signal = "Empate técnico ativo; não oficialize sem manter o runner-up visível."
    elif not summary.get("feasible"):
        priority_signal = f"O winner ainda está bloqueado por {_humanize_infeasibility_reason(summary.get('infeasibility_reason'))}."
    elif summary.get("critical_routes"):
        top_route = list(summary.get("critical_routes", []))[0]
        priority_signal = f"Rota crítica {top_route.get('route_id') or '-'} segue pedindo revisão antes da exportação."
    elif summary.get("winner_penalties"):
        priority_signal = f"Há penalidade relevante no winner: {list(summary.get('winner_penalties', []))[0]}."
    elif score_margin_delta is not None and score_margin_delta <= 0.5:
        priority_signal = "A margem para o runner-up ainda é curta; trate esta escolha como contraste fraco."
    else:
        priority_signal = "O winner abriu contraste suficiente para orientar a decisão assistida."
    winner_reason = str(summary.get("winner_reason_summary") or "Sem justificativa resumida.")
    if summary.get("feasible") is False:
        winner_reason = f"{winner_reason} Bloqueio atual: {_humanize_infeasibility_reason(summary.get('infeasibility_reason'))}."
    return html.Div(
        children=[
            html.H3("Winner oficial", style={"marginTop": 0}),
            html.Div(
                style={**UI_THREE_COLUMN_STYLE, "marginBottom": "12px"},
                children=[
                    _guidance_card("Status da decisão", decision_label),
                    _guidance_card("Por que esta leitura lidera", winner_reason if winner_reason != "Sem justificativa resumida." else priority_signal),
                    _guidance_card("Próxima ação", decision_state["next_action"]),
                ],
            ),
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "10px", "flexWrap": "wrap"},
                children=[
                    html.Div(candidate_id or "-", style={"fontSize": "28px", "fontWeight": 700}),
                    html.Span(decision_label, style=UI_PILL_STYLE),
                    html.Span(feasibility_label, style=UI_PILL_STYLE),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Família oficial", summary.get("topology_family") or "-"),
                    _metric_card("Score final", summary.get("score_final") or "-"),
                    _metric_card("Custo oficial", summary.get("total_cost") or summary.get("winner_total_cost") or "-"),
                    _metric_card("Fallbacks", summary.get("fallback_component_count") or 0),
                ],
            ),
            html.Div(
                decision_state["contrast_state"],
                style={"marginTop": "12px", "fontWeight": 700, "lineHeight": "1.5"},
            ),
            html.P(winner_reason, style={"lineHeight": "1.6"}),
            html.H4("Próxima ação", style={"marginBottom": "6px"}),
            html.Div(
                decision_state["next_action"],
                style={"lineHeight": "1.6", "fontWeight": 700},
            ),
        ]
    )


def render_decision_contrast_panel(summary: dict[str, Any]) -> Any:
    candidate_id = str(summary.get("candidate_id") or "").strip()
    runner_up_id = str(summary.get("runner_up_candidate_id") or "").strip()
    if not summary or not candidate_id:
        return _guided_empty_state(
            "Runner-up e contraste",
            "Ainda não existe decisão utilizável para abrir a comparação principal.",
            "Recupere uma execução comparável em Runs antes de fechar a leitura entre winner e runner-up.",
        )
    if not runner_up_id:
        return _guided_empty_state(
            "Runner-up e contraste",
            "A leitura atual já mostra um winner, mas ainda não existe runner-up comparável para sustentar o contraste principal.",
            "Relaxe filtros ou recupere uma execução com contraste suficiente antes de oficializar a escolha.",
        )
    decision_status = str(summary.get("decision_status") or ("technical_tie" if summary.get("technical_tie") else "winner_clear"))
    runner_up_cost = summary.get("runner_up_total_cost")
    winner_cost = summary.get("total_cost") or summary.get("winner_total_cost")
    cost_delta = (
        round(float(winner_cost) - float(runner_up_cost), 3)
        if winner_cost not in (None, "") and runner_up_cost not in (None, "")
        else "-"
    )
    difference_lines = [str(item.get("summary")) for item in summary.get("key_factors", []) if item.get("summary")]
    if summary.get("runner_up_total_cost") not in (None, ""):
        difference_lines.insert(0, f"Custo oficial vs runner-up: {winner_cost} vs {summary.get('runner_up_total_cost')}.")
    contrast_summary = (
        "Winner e runner-up seguem tecnicamente empatados; a escolha final pede leitura humana assistida."
        if decision_status == "technical_tie"
        else "O runner-up segue como melhor alternativa comparável, mas abaixo da escolha oficial no ranking."
    )
    return html.Div(
        children=[
            html.H3("Runner-up e contraste", style={"marginTop": 0}),
            html.Div(runner_up_id or "-", style={"fontSize": "24px", "fontWeight": 700}),
            html.Div(
                style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginTop": "8px"},
                children=[
                    html.Span(str(summary.get("runner_up_topology_family") or "-"), style=UI_PILL_STYLE),
                    html.Span("Empate técnico" if decision_status == "technical_tie" else "Alternativa próxima", style=UI_PILL_STYLE),
                ],
            ),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Margem de score", summary.get("score_margin_delta") or "-"),
                    _metric_card("Score runner-up", summary.get("runner_up_score_final") or "-"),
                    _metric_card("Delta de custo", cost_delta),
                ],
            ),
            html.Div(contrast_summary, style={"marginTop": "12px", "fontWeight": 700, "lineHeight": "1.5"}),
            html.H4("Diferenças relevantes", style={"marginBottom": "6px"}),
            _bullet_list(difference_lines[:4], "Sem diferença relevante registrada."),
        ]
    )


def render_decision_signal_panel(summary: dict[str, Any]) -> Any:
    if not summary:
        return _guided_empty_state(
            "Sinais para decisão humana",
            "Ainda não há sinais consolidados para suportar a leitura de risco desta decisão.",
            "Abra uma execução válida ou um candidato em foco para revelar penalidades, rotas críticas e fallback.",
        )
    signal_lines: list[str] = []
    infeasibility_reason = str(summary.get("infeasibility_reason") or "").strip()
    if infeasibility_reason:
        signal_lines.append(f"A escolha oficial ficou inviável porque {_humanize_infeasibility_reason(infeasibility_reason)}.")
    else:
        signal_lines.append("A escolha oficial segue viável na leitura atual do ranking.")
    for penalty in list(summary.get("winner_penalties", []))[:2]:
        signal_lines.append(f"Atenção: {penalty}.")
    for route in list(summary.get("critical_routes", []))[:2]:
        route_id = str(route.get("route_id") or "-")
        reason = _humanize_route_issue(route.get("reason"))
        signal_lines.append(f"Rota crítica {route_id}: {reason}.")
    return html.Div(
        children=[
            html.H3("Sinais para decisão humana", style={"marginTop": 0}),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Rotas críticas", len(summary.get("critical_routes", []) or [])),
                    _metric_card("Penalidades", len(summary.get("winner_penalties", []) or [])),
                    _metric_card("Fallbacks", summary.get("fallback_component_count") or 0),
                ],
            ),
            html.H4("Leitura rápida", style={"marginBottom": "6px"}),
            _bullet_list(signal_lines, "Sem sinal adicional para esta decisão."),
        ]
    )


def render_candidate_breakdown_panel(summary: dict[str, Any]) -> Any:
    if not summary:
        return _guided_empty_state(
            "Justificativa detalhada",
            "Ainda não existe breakdown suficiente para explicar um candidato neste espaço.",
            "Selecione um candidato visível ou volte à comparação para abrir o racional completo.",
        )
    total_cost = round(float(summary.get("install_cost") or 0.0), 3)
    if (summary.get("constraint_failure_count") or 0) > 0:
        next_action = "Há falhas de restrição. Releia as regras disparadas antes de confirmar este candidato."
    elif (summary.get("fallback_component_count") or 0) > 0:
        next_action = "O candidato depende de fallback. Compare com o runner-up antes de oficializar a escolha."
    else:
        next_action = "O breakdown está limpo. Use a comparação e o circuito para confirmar a decisão final."
    return html.Div(
        children=[
            html.H3("Justificativa detalhada", style={"marginTop": 0}),
            html.Div(f"Candidato: {summary.get('candidate_id') or '-'}", style={"fontWeight": 700}),
            html.Div(
                style=UI_THREE_COLUMN_STYLE,
                children=[
                    _metric_card("Custo instalado", total_cost),
                    _metric_card("Falhas de restrição", summary.get("constraint_failure_count") or 0),
                    _metric_card("Fallbacks", summary.get("fallback_component_count") or 0),
                ],
            ),
            html.H4("Leitura de qualidade", style={"marginBottom": "6px"}),
            _label_value_list(
                [
                    ("Qualidade bruta", summary.get("quality_score_raw")),
                    ("Resiliência", summary.get("resilience_score")),
                    ("Operabilidade", summary.get("operability_score")),
                    ("Cleaning", summary.get("cleaning_score")),
                ]
            ),
            html.H4("Regras e flags", style={"marginBottom": "6px"}),
            _bullet_list([str(item) for item in summary.get("rules_triggered", [])], "Sem regra destacada."),
            html.H4("Próxima ação", style={"marginBottom": "6px", "marginTop": "14px"}),
            html.Div(next_action, style={"lineHeight": "1.6", "fontWeight": 700}),
        ]
    )


def build_app(
    scenario_dir: str | Path = "data/decision_platform/maquete_v2",
    *,
    run_queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT,
    bootstrap_pipeline: bool = True,
) -> Dash:
    scenario_dir = _normalize_scenario_dir(scenario_dir)
    run_queue_root = Path(run_queue_root).expanduser().resolve(strict=False)
    bundle = load_scenario_bundle(scenario_dir)
    result, pipeline_error = _resolve_initial_pipeline_state(
        scenario_dir,
        bootstrap_pipeline=bootstrap_pipeline,
    )
    authoring_payload = bundle_authoring_payload(bundle)
    initial_execution_summary = _build_execution_summary(result, pipeline_error)
    profile_id = bundle.scenario_settings["ranking"]["default_profile"]
    family_options = _family_dropdown_options(bundle)
    initial_state = build_catalog_view_state(
        result,
        profile_id=profile_id,
        current_selected_id=result.get("selected_candidate_id") if result else None,
    )
    candidate_details = build_candidate_detail(result, initial_state["selected_candidate_id"]) if result else {}
    initial_catalog_summary = _build_catalog_state_summary(
        profile_id=profile_id,
        selected_candidate_id=initial_state["selected_candidate_id"],
        ranked_records=initial_state["ranked_records"],
        filters={},
        aggregate_summary=result.get("summary", {}) if result else {},
    )
    initial_official_summary = build_official_candidate_summary(
        result,
        profile_id=profile_id,
        candidate_id=None,
    )
    initial_comparison_records = build_comparison_records(
        result,
        initial_state["comparison_ids"],
        profile_id=profile_id,
        active_selected_id=initial_state["selected_candidate_id"],
    )
    initial_node_studio_selected_id = _default_primary_node_studio_selection(
        authoring_payload["nodes_rows"],
        authoring_payload["candidate_links_rows"],
    )
    initial_node_studio_elements = build_primary_node_studio_elements(
        authoring_payload["nodes_rows"],
        authoring_payload["candidate_links_rows"],
        authoring_payload["route_rows"],
    )
    initial_edge_studio_selected_id = _default_primary_edge_studio_selection(
        authoring_payload["nodes_rows"],
        authoring_payload["candidate_links_rows"],
    )
    initial_node_studio_summary = json.dumps(
        _build_node_studio_summary(authoring_payload["nodes_rows"], initial_node_studio_selected_id),
        indent=2,
        ensure_ascii=False,
    )
    initial_node_studio_form = _node_studio_form_values(authoring_payload["nodes_rows"], initial_node_studio_selected_id)
    initial_edge_studio_summary = json.dumps(
        _build_edge_studio_summary(
            authoring_payload["nodes_rows"],
            authoring_payload["candidate_links_rows"],
            initial_edge_studio_selected_id,
        ),
        indent=2,
        ensure_ascii=False,
    )
    initial_edge_studio_form = _edge_studio_form_values(
        authoring_payload["candidate_links_rows"],
        initial_edge_studio_selected_id,
    )
    initial_run_jobs_snapshot = build_run_jobs_snapshot(run_queue_root)
    initial_run_jobs_summary = _serialize_json(initial_run_jobs_snapshot["summary"])
    initial_run_job_options = initial_run_jobs_snapshot["options"]
    initial_run_job_selected_id = initial_run_jobs_snapshot["selected_run_id"]
    initial_run_job_detail = _serialize_json(initial_run_jobs_snapshot["selected_run_detail"])
    initial_bundle_output_dir = str(Path(scenario_dir).parent / f"{Path(scenario_dir).name}_saved")
    initial_bundle_io_summary = json.dumps(
        {
            "source_scenario_dir": str(Path(scenario_dir)),
            "requested_scenario_dir": str(Path(scenario_dir)),
            "canonical_scenario_root": str(bundle.base_dir),
            "requested_dir_matches_bundle_root": str(Path(scenario_dir)) == str(bundle.base_dir),
            "bundle_manifest": str(bundle.bundle_manifest_path) if bundle.bundle_manifest_path else None,
            "bundle_version": bundle.bundle_version,
            "bundle_files": {
                logical_name: str(path.relative_to(bundle.base_dir))
                for logical_name, path in bundle.resolved_files.items()
            },
            "status": "idle",
        },
        indent=2,
        ensure_ascii=False,
    )

    initial_studio_readiness = build_studio_readiness_summary(
        authoring_payload["nodes_rows"],
        authoring_payload["candidate_links_rows"],
        authoring_payload["route_rows"],
    )
    initial_studio_projection = build_studio_projection_summary(
        authoring_payload["nodes_rows"],
        authoring_payload["candidate_links_rows"],
        authoring_payload["route_rows"],
    )

    app = Dash(__name__)
    app.layout = html.Div(
        style=UI_PAGE_STYLE,
        children=[
            dcc.Location(id="ui-location", refresh=False),
            dcc.Store(id="scenario-dir", data=str(Path(scenario_dir))),
            dcc.Store(id="run-queue-root", data=str(run_queue_root)),
            dcc.Store(id="node-studio-selected-id", data=initial_node_studio_selected_id),
            dcc.Store(id="edge-studio-selected-id", data=initial_edge_studio_selected_id),
            dcc.Store(id="studio-route-draft-source-id", data=""),
            dcc.Store(id="studio-status-message", data=""),
            html.Div(
                style=UI_SHELL_STYLE,
                children=[
                    html.Div(
                        style=UI_HERO_STYLE,
                        children=[
                            html.Div("Decision Platform", style={"fontSize": "13px", "letterSpacing": "0.14em", "textTransform": "uppercase", "opacity": 0.78}),
                            html.H1("Studio, runs e decisão numa jornada única", style={"margin": "6px 0 8px", "fontSize": "30px", "lineHeight": "1.05"}),
                            html.P(
                                "A interface principal foi reorganizada para deixar explícito quando editar o cenário, quando acompanhar a fila, quando decidir entre alternativas e quando abrir a trilha técnica.",
                                style={"maxWidth": "860px", "fontSize": "14px", "lineHeight": "1.45", "margin": "0 0 12px"},
                            ),
                            html.Div(
                                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(180px, 1fr))", "gap": "10px"},
                                children=[
                                    _journey_step_card("1", "Studio", "Preparar o cenário com readiness e menos ruído."),
                                    _journey_step_card("2", "Runs", "Ler fila e status sem depender de logs."),
                                    _journey_step_card("3", "Decisão", "Comparar winner, runner-up e technical tie."),
                                    _journey_step_card("4", "Auditoria", "Abrir a trilha técnica apenas quando precisar aprofundar."),
                                ],
                            ),
                            html.Div(
                                style={**UI_ACTION_ROW_STYLE, "marginTop": "12px"},
                                children=[
                                    _hero_navigation_link("Abrir Studio", "?tab=studio", "hero-open-studio-link"),
                                    _hero_navigation_link("Abrir Runs", "?tab=runs", "hero-open-runs-link"),
                                    _hero_navigation_link("Abrir Decisão", "?tab=decision", "hero-open-decision-link"),
                                    _hero_navigation_link("Abrir Auditoria", "?tab=audit", "hero-open-audit-link"),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        id="product-journey-panel",
                        children=render_product_journey_panel(
                            "studio",
                            initial_studio_readiness,
                            initial_run_jobs_snapshot["summary"],
                            initial_official_summary,
                        ),
                        style=UI_JOURNEY_PANEL_STYLE,
                    ),
                    html.Div(
                        id="product-space-banner",
                        children=render_product_space_banner(
                            "studio",
                            initial_studio_readiness,
                            initial_run_jobs_snapshot["summary"],
                            initial_official_summary,
                        ),
                        style=UI_PERSISTENT_BANNER_STYLE,
                    ),
                    dcc.Tabs(
                        id="primary-navigation-tabs",
                        value="studio",
                        colors={"border": "transparent", "primary": "#103b35", "background": "transparent"},
                        children=[
                    dcc.Tab(
                        label="Studio",
                        value="studio",
                        children=[
                            html.Div(
                                style={**UI_COMPACT_BANNER_CARD_STYLE, "marginBottom": "14px"},
                                children=[
                                    html.Div("Studio", style={"fontSize": "12px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#47665d"}),
                                    html.Div("Desenhe primeiro as rotas de negócio e ajuste a intenção perto do canvas.", style={"fontWeight": 700, "fontSize": "22px", "lineHeight": "1.25", "marginTop": "6px"}),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "gridTemplateColumns": "minmax(0, 1fr) minmax(280px, 360px)", "marginTop": "10px"},
                                        children=[
                                            html.Div("A superfície principal mantém rotas, entidades e conexões de negócio. Hubs internos, contratos crus e JSON ficam fora da primeira dobra.", style={"lineHeight": "1.45"}),
                                            html.Div(
                                                style={**UI_MUTED_CARD_STYLE, "padding": "10px"},
                                                children=[
                                                    html.Div("Prioridade agora", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                                                    html.Div("Defina as rotas a servir, ajuste intenção e conectividade no canvas e use a bancada avançada só quando a ação direta não bastar.", style={"fontWeight": 700, "lineHeight": "1.45", "marginTop": "6px"}),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Div(
                                style=UI_STUDIO_MAIN_GRID_STYLE,
                                children=[
                                    html.Div(
                                        style=UI_STUDIO_CANVAS_CARD_STYLE,
                                        children=[
                                            html.Div(
                                                style={"display": "flex", "justifyContent": "space-between", "gap": "12px", "alignItems": "flex-start", "flexWrap": "wrap"},
                                                children=[
                                                    html.Div(
                                                        children=[
                                                            html.H3("Rotas de negócio no canvas", style={"margin": "0 0 4px"}),
                                                            html.Div("Use esta área para enxergar quem supre quem, desenhar os trechos principais e revisar a intenção das rotas.", style={"lineHeight": "1.45", "color": "#496158"}),
                                                        ]
                                                    ),
                                                    html.Div(
                                                        style={**UI_MUTED_CARD_STYLE, "padding": "10px", "minWidth": "240px"},
                                                        children=[
                                                            html.Div("Visibilidade principal", style={"fontSize": "11px", "textTransform": "uppercase", "letterSpacing": "0.12em", "color": "#5b756d"}),
                                                            html.Div("Somente entidades, conexões e projeções de rota de negócio aparecem aqui.", style={"fontWeight": 700, "lineHeight": "1.45", "marginTop": "6px"}),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="studio-canvas-guidance-panel",
                                                children=render_studio_canvas_guidance_panel(
                                                    initial_studio_readiness,
                                                    _safe_json_loads(initial_node_studio_summary),
                                                    _safe_json_loads(initial_edge_studio_summary),
                                                ),
                                            ),
                                            cyto.Cytoscape(
                                                id="node-studio-cytoscape",
                                                elements=initial_node_studio_elements,
                                                layout={"name": "preset"},
                                                style={"width": "100%", "height": "720px"},
                                                contextMenu=STUDIO_CONTEXT_MENU,
                                                stylesheet=_build_node_studio_stylesheet(
                                                    initial_node_studio_selected_id,
                                                    initial_edge_studio_selected_id,
                                                ),
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        style=UI_STUDIO_SIDEBAR_STYLE,
                                        children=[
                                            html.Div(
                                                id="studio-command-center-shell",
                                                style=UI_CARD_STYLE,
                                                children=render_studio_command_center_panel(
                                                    initial_studio_readiness,
                                                    _safe_json_loads(initial_node_studio_summary),
                                                    _safe_json_loads(initial_edge_studio_summary),
                                                    authoring_payload["nodes_rows"],
                                                    authoring_payload["candidate_links_rows"],
                                                    authoring_payload["route_rows"],
                                                ),
                                            ),
                                            html.Div(
                                                id="studio-workspace-panel",
                                                children=render_studio_workspace_panel(
                                                    initial_studio_readiness,
                                                    _safe_json_loads(initial_node_studio_summary),
                                                    _safe_json_loads(initial_edge_studio_summary),
                                                    authoring_payload["nodes_rows"],
                                                    authoring_payload["candidate_links_rows"],
                                                    authoring_payload["route_rows"],
                                                    "",
                                                    "",
                                                ),
                                                style=UI_CARD_STYLE,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="studio-context-detailed-panels",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Contexto completo do Studio"),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Div(id="studio-readiness-panel", children=render_studio_readiness_panel(initial_studio_readiness), style=UI_CARD_STYLE),
                                            html.Div(id="studio-projection-coverage-panel", children=render_studio_projection_panel(initial_studio_projection), style=UI_CARD_STYLE),
                                        ],
                                    ),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Div(
                                                id="studio-focus-panel",
                                                children=render_studio_focus_panel(
                                                    _safe_json_loads(initial_node_studio_summary),
                                                    _safe_json_loads(initial_edge_studio_summary),
                                                    authoring_payload["nodes_rows"],
                                                    authoring_payload["candidate_links_rows"],
                                                    authoring_payload["route_rows"],
                                                    initial_studio_readiness,
                                                    "",
                                                ),
                                                style=UI_CARD_STYLE,
                                            ),
                                            html.Div(
                                                id="studio-connectivity-panel",
                                                children=render_studio_connectivity_panel(
                                                    initial_studio_readiness,
                                                    _safe_json_loads(initial_node_studio_summary),
                                                    _safe_json_loads(initial_edge_studio_summary),
                                                    authoring_payload["route_rows"],
                                                    authoring_payload["nodes_rows"],
                                                    authoring_payload["candidate_links_rows"],
                                                ),
                                                style=UI_CARD_STYLE,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="studio-editor-workbench",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Workbench avançado do Studio"),
                                    html.Div(
                                        style=UI_TWO_COLUMN_STYLE,
                                        children=[
                                            html.Div(
                                                id="node-studio-business-editor",
                                                style=UI_CARD_STYLE,
                                                children=[
                                                    html.Div(id="node-studio-summary-panel", children=render_studio_selection_panel(_safe_json_loads(initial_node_studio_summary), "node")),
                                                    html.H3("Entidade do cenário", style={"marginTop": 0}),
                                                    html.P(
                                                        "Edite o nome exibido e a posição da entidade no grafo principal. IDs, tipo técnico e flags ficam em campos avançados.",
                                                        style={"marginTop": 0, "lineHeight": "1.6"},
                                                    ),
                                                    _field_block("Rótulo visível", dcc.Input(id="node-studio-label", type="text", value=initial_node_studio_form["label"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    html.Div(
                                                        style=UI_TWO_COLUMN_STYLE,
                                                        children=[
                                                            _field_block("Posição X (m)", dcc.Input(id="node-studio-x-m", type="number", value=initial_node_studio_form["x_m"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Posição Y (m)", dcc.Input(id="node-studio-y-m", type="number", value=initial_node_studio_form["y_m"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                        ],
                                                    ),
                                                    html.Div(style=UI_ACTION_ROW_STYLE, children=[html.Button("Aplicar propriedades do nó", id="node-studio-apply-button", style=UI_BUTTON_STYLE), html.Button("Criar nó", id="node-studio-create-button", style=UI_BUTTON_STYLE), html.Button("Duplicar nó", id="node-studio-duplicate-button", style=UI_BUTTON_STYLE), html.Button("Excluir nó selecionado", id="node-studio-delete-button", style=UI_BUTTON_STYLE)]),
                                                    html.Div(
                                                        style=UI_TWO_COLUMN_STYLE,
                                                        children=[
                                                            _field_block("Mover", dcc.Dropdown(id="node-studio-move-direction", options=[{"label": "Esquerda", "value": "left"}, {"label": "Direita", "value": "right"}, {"label": "Cima", "value": "up"}, {"label": "Baixo", "value": "down"}], value="right", persistence=True, persistence_type="session")),
                                                            _field_block("Passo", dcc.Input(id="node-studio-move-step", type="number", value=0.02, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                        ],
                                                    ),
                                                    html.Button("Mover nó", id="node-studio-move-button", style=UI_BUTTON_STYLE),
                                                    html.Details(
                                                        style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"},
                                                        children=[
                                                            html.Summary("Campos técnicos do nó"),
                                                            _field_block("Node ID contratual", dcc.Input(id="node-studio-node-id", type="text", value=initial_node_studio_form["node_id"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Tipo técnico", dcc.Input(id="node-studio-node-type", type="text", value=initial_node_studio_form["node_type"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Permitir entrada", dcc.Checklist(id="node-studio-allow-inbound", options=[{"label": "allow_inbound", "value": "allow_inbound"}], value=initial_node_studio_form["allow_inbound"], persistence=True, persistence_type="session")),
                                                            _field_block("Permitir saída", dcc.Checklist(id="node-studio-allow-outbound", options=[{"label": "allow_outbound", "value": "allow_outbound"}], value=initial_node_studio_form["allow_outbound"], persistence=True, persistence_type="session")),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            html.Div(
                                                id="edge-studio-business-editor",
                                                style=UI_CARD_STYLE,
                                                children=[
                                                    html.Div(id="edge-studio-summary-panel", children=render_studio_selection_panel(_safe_json_loads(initial_edge_studio_summary), "edge")),
                                                    html.H3("Conexão do cenário", style={"marginTop": 0}),
                                                    html.P(
                                                        "Mantenha a edição principal focada na leitura do fluxo. Origem, destino e contratos técnicos ficam em campos avançados.",
                                                        style={"marginTop": 0, "lineHeight": "1.6"},
                                                    ),
                                                    _field_block("Comprimento (m)", dcc.Input(id="edge-studio-length-m", type="number", value=initial_edge_studio_form["length_m"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    _field_block("Famílias sugeridas", dcc.Input(id="edge-studio-family-hint", type="text", value=initial_edge_studio_form["family_hint"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    html.Div(style=UI_ACTION_ROW_STYLE, children=[html.Button("Aplicar propriedades da aresta", id="edge-studio-apply-button", style=UI_BUTTON_STYLE), html.Button("Criar aresta", id="edge-studio-create-button", style=UI_BUTTON_STYLE), html.Button("Excluir aresta selecionada", id="edge-studio-delete-button", style=UI_BUTTON_STYLE)]),
                                                    html.Details(
                                                        style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"},
                                                        children=[
                                                            html.Summary("Campos técnicos da conexão"),
                                                            _field_block("Link ID contratual", dcc.Input(id="edge-studio-link-id", type="text", value=initial_edge_studio_form["link_id"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Origem técnica", dcc.Input(id="edge-studio-from-node", type="text", value=initial_edge_studio_form["from_node"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Destino técnico", dcc.Input(id="edge-studio-to-node", type="text", value=initial_edge_studio_form["to_node"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Archetype técnico", dcc.Input(id="edge-studio-archetype", type="text", value=initial_edge_studio_form["archetype"], persistence=True, persistence_type="session", style={"width": "100%"})),
                                                            _field_block("Bidirecional", dcc.Checklist(id="edge-studio-bidirectional", options=[{"label": "bidirectional", "value": "bidirectional"}], value=initial_edge_studio_form["bidirectional"], persistence=True, persistence_type="session")),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="studio-technical-guide",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Onde está a trilha técnica"),
                                    html.P(
                                        "A projeção principal mantém apenas entidades e fluxos de negócio. Campos contratuais, IDs e estrutura detalhada continuam disponíveis nos campos avançados do Studio e na aba Auditoria.",
                                        style={"lineHeight": "1.6"},
                                    ),
                                    html.Ul(
                                        [
                                            html.Li("Abra a bancada de edição do grafo quando precisar ajustar nome, posição ou famílias sugeridas."),
                                            html.Li("Use os campos técnicos do nó ou da conexão apenas quando precisar editar o bundle estrutural."),
                                            html.Li("Use a aba Auditoria para revisar tabelas canônicas, textos YAML e o bundle salvo."),
                                        ],
                                        style={"margin": "8px 0 0 18px", "lineHeight": "1.6"},
                                    ),
                                ],
                            ),
                            html.Details(
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Auditoria técnica do Studio"),
                                    html.Div(id="studio-status", style={"marginTop": "10px", "fontWeight": 600}),
                                    html.Pre(initial_node_studio_summary, id="node-studio-summary", style=UI_DEBUG_PRE_STYLE),
                                    html.Pre(initial_edge_studio_summary, id="edge-studio-summary", style=UI_DEBUG_PRE_STYLE),
                                ],
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Auditoria",
                        value="audit-hidden",
                        style={"display": "none"},
                        selected_style={"display": "none"},
                        children=[],
                    ),
                    dcc.Tab(
                        label="Runs",
                        value="runs",
                        children=[
                            _section_intro(
                                "Runs",
                                "A fila serial continua igual no backend, mas a leitura principal agora resume fila, run em foco e último estado executivo antes de abrir detalhes técnicos.",
                                state_hint="Camada principal: fila local, run em foco e último resumo executivo.",
                                action_hint="Escolha a próxima run, revise o estado atual e execute apenas o próximo passo necessário.",
                            ),
                            html.Div(
                                id="runs-workspace-panel",
                                children=render_runs_workspace_panel(
                                    initial_studio_readiness,
                                    initial_run_jobs_snapshot["summary"],
                                    _safe_json_loads(initial_execution_summary),
                                ),
                                style=UI_CARD_STYLE,
                            ),
                            html.Details(
                                id="runs-context-detailed-panels",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Contexto completo de Runs"),
                                    html.Div(
                                        id="runs-flow-panel",
                                        children=render_runs_flow_panel(
                                            initial_studio_readiness,
                                            initial_run_jobs_snapshot["summary"],
                                            _safe_json_loads(initial_execution_summary),
                                        ),
                                        style={**UI_CARD_STYLE, "marginTop": "12px"},
                                    ),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Div(id="run-jobs-overview-panel", children=render_run_jobs_overview_panel(initial_run_jobs_snapshot["summary"]), style=UI_CARD_STYLE),
                                            html.Div(id="execution-summary-panel", children=render_execution_summary_panel(_safe_json_loads(initial_execution_summary)), style=UI_MUTED_CARD_STYLE),
                                        ],
                                    ),
                                    html.Div(id="run-job-detail-panel", children=render_run_job_detail_panel(initial_run_jobs_snapshot["selected_run_detail"]), style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"}),
                                ],
                            ),
                            html.Details(
                                id="runs-operations-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Operações da fila"),
                                    html.Div(
                                        style={**UI_CARD_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.H3("Operações da fila", style={"marginTop": 0}),
                                            html.Div(style=UI_ACTION_ROW_STYLE, children=[html.Button("Enfileirar cenário atual", id="run-job-enqueue-button", style=UI_BUTTON_STYLE), html.Button("Executar próximo job", id="run-jobs-run-next-button", style=UI_BUTTON_STYLE), html.Button("Atualizar runs", id="run-jobs-refresh-button", style=UI_BUTTON_STYLE), html.Button("Cancelar run selecionada", id="run-job-cancel-button", style=UI_BUTTON_STYLE), html.Button("Reexecutar run selecionada", id="run-job-rerun-button", style=UI_BUTTON_STYLE), html.Button("Reexecutar pipeline", id="run-button", style=UI_BUTTON_STYLE)]),
                                            _field_block("Run selecionada", dcc.Dropdown(id="run-job-selected-id", options=initial_run_job_options, value=initial_run_job_selected_id, persistence=True, persistence_type="session")),
                                            html.Div(id="run-jobs-status-banner", children=render_status_banner(""), style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"}),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="runs-technical-audit-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Auditoria técnica de runs"),
                                    html.Pre("", id="run-jobs-status", style=UI_DEBUG_PRE_STYLE),
                                    html.Pre(initial_run_jobs_summary, id="run-jobs-summary", style=UI_DEBUG_PRE_STYLE),
                                    html.Pre(initial_run_job_detail, id="run-job-detail", style=UI_DEBUG_PRE_STYLE),
                                    html.Pre(initial_execution_summary, id="execution-summary", style=UI_DEBUG_PRE_STYLE),
                                ],
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Pipeline",
                        value="pipeline-hidden",
                        style={"display": "none"},
                        selected_style={"display": "none"},
                        children=[],
                    ),
                    dcc.Tab(
                        label="Decisão",
                        value="decision",
                        children=[
                            _section_intro(
                                "Decisão",
                                "A área principal agora reúne winner, runner-up, filtros, comparação aprofundada e o circuito do candidato em um único espaço de decisão humana assistida.",
                                state_hint="Camada principal: escolha oficial, comparação e circuito do candidato.",
                                action_hint="Confirme winner versus runner-up, leia o technical tie quando houver e só depois aprofunde o racional técnico.",
                            ),
                            html.Div(
                                id="decision-workspace-panel",
                                children=render_decision_workspace_panel(initial_official_summary, _safe_json_loads(initial_catalog_summary)),
                                style=UI_CARD_STYLE,
                            ),
                            html.Details(
                                id="decision-context-detailed-panels",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Contexto completo da decisão"),
                                    html.Div(id="decision-flow-panel", children=render_decision_flow_panel(initial_official_summary), style={**UI_CARD_STYLE, "marginTop": "12px"}),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Div(id="decision-summary-panel", children=render_decision_summary_panel(initial_official_summary), style=UI_CARD_STYLE),
                                            html.Div(id="decision-contrast-panel", children=render_decision_contrast_panel(initial_official_summary), style=UI_MUTED_CARD_STYLE),
                                        ],
                                    ),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Div(id="decision-signal-panel", children=render_decision_signal_panel(initial_official_summary), style=UI_CARD_STYLE),
                                            html.Div(id="catalog-state-summary-panel", children=render_catalog_state_panel(_safe_json_loads(initial_catalog_summary)), style=UI_MUTED_CARD_STYLE),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="decision-ranking-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Filtros, ranking e catálogo"),
                                    html.Div(
                                        style={**UI_CARD_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.H3("Filtros e ranking", style={"marginTop": 0}),
                                            html.Div(
                                                style=UI_THREE_COLUMN_STYLE,
                                                children=[
                                                    _field_block("Perfil", dcc.Dropdown(id="profile-dropdown", options=_profile_dropdown_options(bundle), value=profile_id, persistence=True, persistence_type="session")),
                                                    _field_block("Família", dcc.Dropdown(id="family-dropdown", options=family_options, value="ALL", persistence=True, persistence_type="session")),
                                                    _field_block("Fallback", dcc.Dropdown(id="fallback-filter-dropdown", options=[{"label": "Todos", "value": "ALL"}, {"label": "Sem fallback", "value": "NO_FALLBACK"}, {"label": "Com fallback", "value": "WITH_FALLBACK"}], value="ALL", persistence=True, persistence_type="session")),
                                                    _field_block("Motivo de inviabilidade", dcc.Dropdown(id="infeasibility-reason-dropdown", options=_infeasibility_reason_options(result), value="ALL", persistence=True, persistence_type="session")),
                                                    _field_block("Status", dcc.Checklist(id="feasible-only-checklist", options=[{"label": "Apenas viáveis", "value": "feasible_only"}], value=["feasible_only"] if bundle.scenario_settings["ranking"].get("keep_only_feasible", True) else [], persistence=True, persistence_type="session")),
                                                    _field_block("Top por família", dcc.Input(id="top-n-family-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                ],
                                            ),
                                            html.Div(
                                                style=UI_THREE_COLUMN_STYLE,
                                                children=[
                                                    _field_block("Custo máximo", dcc.Input(id="max-cost-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    _field_block("Qualidade mínima", dcc.Input(id="min-quality-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    _field_block("Vazão mínima", dcc.Input(id="min-flow-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    _field_block("Resiliência mínima", dcc.Input(id="min-resilience-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    _field_block("Cleaning mínimo", dcc.Input(id="min-cleaning-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    _field_block("Operabilidade mínima", dcc.Input(id="min-operability-input", type="number", value=None, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                ],
                                            ),
                                            html.Details(
                                                style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"},
                                                children=[
                                                    html.Summary("Ajustar pesos dinâmicos"),
                                                    _weight_inputs(bundle),
                                                ],
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        style={**UI_CARD_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.H3("Catálogo visível", style={"marginTop": 0}),
                                            _catalog_grid(initial_state["ranked_records"]),
                                            html.H3("Resumo por família"),
                                            _family_summary_grid(initial_state.get("family_summary_records", [])),
                                            html.Button("Exportar catálogo ranqueado", id="export-catalog-button", style=UI_BUTTON_STYLE),
                                            dcc.Download(id="catalog-download"),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="decision-comparison-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Comparação aprofundada"),
                                    _field_block("Comparar candidatos", dcc.Dropdown(id="compare-candidates-dropdown", options=initial_state["comparison_options"], value=initial_state["comparison_ids"], multi=True, persistence=True, persistence_type="session")),
                                    dcc.Graph(
                                        id="comparison-figure",
                                        figure=build_solution_comparison_figure(_lookup_candidates(result, initial_state["comparison_ids"]))
                                        if result
                                        else build_solution_comparison_figure([]),
                                    ),
                                    _comparison_grid(initial_comparison_records),
                                    html.Div(style=UI_ACTION_ROW_STYLE, children=[html.Button("Exportar comparação", id="export-comparison-button", style=UI_BUTTON_STYLE), dcc.Download(id="comparison-download"), html.Button("Exportar comparação JSON", id="export-comparison-json-button", style=UI_BUTTON_STYLE), dcc.Download(id="comparison-json-download")]),
                                ],
                            ),
                            html.Details(
                                id="decision-candidate-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Circuito do candidato em foco"),
                                    html.P(
                                        "Esta leitura mantem somente a camada primaria do circuito, com rotas de negocio e sem hubs internos como superficie principal.",
                                        style={"lineHeight": "1.6"},
                                    ),
                                    html.Div(
                                        style=UI_TWO_COLUMN_STYLE,
                                        children=[
                                            _field_block("Candidato", dcc.Dropdown(id="selected-candidate-dropdown", options=initial_state["selected_options"], value=initial_state["selected_candidate_id"], persistence=True, persistence_type="session")),
                                            _field_block("Rota destacada", dcc.Dropdown(id="route-highlight-dropdown", options=_route_dropdown_options(candidate_details.get("route_rows", [])), value=_default_route_highlight(candidate_details.get("route_rows", [])), persistence=True, persistence_type="session")),
                                        ],
                                    ),
                                    html.Div(id="selected-candidate-summary-panel", children=render_candidate_summary_panel(candidate_details.get("summary", {})), style=UI_CARD_STYLE),
                                    html.Button("Exportar candidato selecionado", id="export-selected-button", style=UI_BUTTON_STYLE),
                                    dcc.Download(id="selected-candidate-download"),
                                    cyto.Cytoscape(
                                        id="circuit-cytoscape",
                                        elements=candidate_details.get("cytoscape_elements", []),
                                        layout={"name": "preset"},
                                        style={"width": "100%", "height": "520px"},
                                        stylesheet=_build_cytoscape_stylesheet(
                                            candidate_details.get("route_highlights", {}),
                                            _default_route_highlight(candidate_details.get("route_rows", [])),
                                            candidate_details.get("critical_component_ids", []),
                                        ),
                                    ),
                                    _route_grid(candidate_details.get("route_rows", [])),
                                    html.Details(
                                        style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Summary("Resumo técnico do candidato"),
                                            html.Pre(
                                                json.dumps(candidate_details.get("summary", {}), indent=2, ensure_ascii=False),
                                                id="selected-candidate-summary",
                                                style=UI_DEBUG_PRE_STYLE,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="decision-justification-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Justificativa detalhada"),
                                    html.Div(id="decision-summary-panel-extended", children=render_decision_summary_panel(initial_official_summary), style=UI_CARD_STYLE),
                                    html.Div(id="candidate-breakdown-panel", children=render_candidate_breakdown_panel(candidate_details.get("breakdown", {})), style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"}),
                                    html.Details(
                                        style={**UI_MUTED_CARD_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Summary("JSON técnico da justificativa"),
                                            html.Pre(
                                                json.dumps(initial_official_summary, indent=2, ensure_ascii=False),
                                                id="official-candidate-summary",
                                                style=UI_DEBUG_PRE_STYLE,
                                            ),
                                            html.Pre(
                                                json.dumps(candidate_details.get("breakdown", {}), indent=2, ensure_ascii=False),
                                                id="candidate-breakdown",
                                                style=UI_DEBUG_PRE_STYLE,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="decision-technical-state-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Resumo técnico do estado de decisão"),
                                    html.Pre(initial_catalog_summary, id="catalog-state-summary", style=UI_DEBUG_PRE_STYLE),
                                ],
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Comparação avançada",
                        value="comparison-hidden",
                        style={"display": "none"},
                        selected_style={"display": "none"},
                        children=[],
                    ),
                    dcc.Tab(
                        label="Circuito candidato",
                        value="candidate-hidden",
                        style={"display": "none"},
                        selected_style={"display": "none"},
                        children=[],
                    ),
                    dcc.Tab(
                        label="Justificativa",
                        value="justification-hidden",
                        style={"display": "none"},
                        selected_style={"display": "none"},
                        children=[],
                    ),
                    dcc.Tab(
                        label="Auditoria",
                        value="audit",
                        children=[
                            _section_intro(
                                "Auditoria",
                                "Persistência do bundle, textos canônicos e tabelas completas continuam disponíveis, mas permanecem fora da superfície primária de edição, execução e decisão.",
                                state_hint="Camada principal: bundle canônico, YAMLs e tabelas completas.",
                                action_hint="Use esta área quando precisar reconciliar contrato, persistência ou estrutura técnica fora do fluxo principal.",
                            ),
                            html.Div(
                                id="audit-workspace-panel",
                                children=render_audit_workspace_panel(
                                    _safe_json_loads(initial_bundle_io_summary),
                                    _safe_json_loads(initial_execution_summary),
                                ),
                                style=UI_CARD_STYLE,
                            ),
                            html.Details(
                                id="audit-context-detailed-panels",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Bundle canônico e textos completos"),
                                    html.Div(
                                        style={**UI_TWO_COLUMN_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.Div(
                                                style=UI_CARD_STYLE,
                                                children=[
                                                    html.H3("Bundle salvo e reabertura", style={"marginTop": 0}),
                                                    html.Div(id="bundle-io-summary-panel", children=render_bundle_io_panel(_safe_json_loads(initial_bundle_io_summary))),
                                                    _field_block("Diretório do bundle salvo", dcc.Input(id="bundle-output-dir-input", type="text", value=initial_bundle_output_dir, persistence=True, persistence_type="session", style={"width": "100%"})),
                                                    html.Button("Salvar e reabrir bundle", id="save-reopen-bundle-button", style=UI_BUTTON_STYLE),
                                                ],
                                            ),
                                            html.Div(
                                                style=UI_MUTED_CARD_STYLE,
                                                children=[
                                                    html.H3("Textos canônicos", style={"marginTop": 0}),
                                                    html.H4("topology_rules.yaml"),
                                                    dcc.Textarea(
                                                        id="topology-rules-editor",
                                                        value=authoring_payload["topology_rules_text"],
                                                        style={"width": "100%", "height": "240px"},
                                                        persistence=True,
                                                        persistence_type="session",
                                                    ),
                                                    html.H4("scenario_settings.yaml"),
                                                    dcc.Textarea(
                                                        id="scenario-settings-editor",
                                                        value=authoring_payload["scenario_settings_text"],
                                                        style={"width": "100%", "height": "240px"},
                                                        persistence=True,
                                                        persistence_type="session",
                                                    ),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="audit-bundle-tables-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("Tabelas completas do bundle"),
                                    html.Div(
                                        style={**UI_CARD_STYLE, "marginTop": "12px"},
                                        children=[
                                            html.H3("Tabelas do bundle", style={"marginTop": 0}),
                                            html.H4("nodes.csv"),
                                            _table("nodes-grid", bundle.nodes, editable=True),
                                            html.H4("component_catalog.csv"),
                                            _table("components-grid", bundle.components, editable=True),
                                            html.H4("candidate_links.csv"),
                                            _table("candidate-links-grid", bundle.candidate_links, editable=True),
                                            html.H4("edge_component_rules.csv"),
                                            _table("edge-component-rules-grid", bundle.edge_component_rules, editable=True),
                                            html.H4("route_requirements.csv"),
                                            _table("routes-grid", bundle.route_requirements, editable=True),
                                            html.H4("layout_constraints.csv"),
                                            _table("layout-constraints-grid", bundle.layout_constraints, editable=True),
                                        ],
                                    ),
                                ],
                            ),
                            html.Details(
                                id="audit-json-details",
                                style=UI_MUTED_CARD_STYLE,
                                children=[
                                    html.Summary("JSON técnico do bundle"),
                                    html.Pre(initial_bundle_io_summary, id="bundle-io-summary", style=UI_DEBUG_PRE_STYLE),
                                ],
                            ),
                        ],
                    ),
                        ],
                    ),
                ],
            ),
        ],
    )

    @app.callback(
        Output("scenario-dir", "data"),
        Output("bundle-io-summary", "children"),
        Output("nodes-grid", "rowData"),
        Output("components-grid", "rowData"),
        Output("candidate-links-grid", "rowData"),
        Output("edge-component-rules-grid", "rowData"),
        Output("routes-grid", "rowData"),
        Output("layout-constraints-grid", "rowData"),
        Output("topology-rules-editor", "value"),
        Output("scenario-settings-editor", "value"),
        Output("execution-summary", "children", allow_duplicate=True),
        Input("save-reopen-bundle-button", "n_clicks"),
        State("scenario-dir", "data"),
        State("bundle-output-dir-input", "value"),
        State("nodes-grid", "rowData"),
        State("components-grid", "rowData"),
        State("candidate-links-grid", "rowData"),
        State("edge-component-rules-grid", "rowData"),
        State("routes-grid", "rowData"),
        State("layout-constraints-grid", "rowData"),
        State("topology-rules-editor", "value"),
        State("scenario-settings-editor", "value"),
        prevent_initial_call=True,
    )
    def _save_and_reopen_bundle(
        n_clicks: Any,
        current_scenario_dir: str,
        bundle_output_dir: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        components_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        edge_component_rules_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
        layout_constraints_rows: list[dict[str, Any]] | None,
        topology_rules_text: str | None,
        scenario_settings_text: str | None,
    ) -> tuple[
        str,
        str,
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        str,
        str,
        str,
    ]:
        if not n_clicks:
            payload = bundle_authoring_payload(load_scenario_bundle(current_scenario_dir))
            return (
                current_scenario_dir,
                initial_bundle_io_summary,
                payload["nodes_rows"],
                payload["components_rows"],
                payload["candidate_links_rows"],
                payload["edge_component_rules_rows"],
                payload["route_rows"],
                payload["layout_constraints_rows"],
                payload["topology_rules_text"],
                payload["scenario_settings_text"],
                initial_execution_summary,
            )
        target_dir = str(Path(bundle_output_dir).expanduser()) if str(bundle_output_dir or "").strip() else current_scenario_dir
        try:
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=current_scenario_dir,
                output_dir=target_dir,
                nodes_rows=nodes_rows,
                components_rows=components_rows,
                candidate_links_rows=candidate_links_rows,
                edge_component_rules_rows=edge_component_rules_rows,
                route_rows=route_rows,
                layout_constraints_rows=layout_constraints_rows,
                topology_rules_text=topology_rules_text,
                scenario_settings_text=scenario_settings_text,
            )
            payload = bundle_authoring_payload(saved["bundle"])
            return (
                saved["scenario_dir"],
                json.dumps(saved["bundle_io_summary"], indent=2, ensure_ascii=False),
                payload["nodes_rows"],
                payload["components_rows"],
                payload["candidate_links_rows"],
                payload["edge_component_rules_rows"],
                payload["route_rows"],
                payload["layout_constraints_rows"],
                payload["topology_rules_text"],
                payload["scenario_settings_text"],
                _build_execution_summary(saved["result"], saved["pipeline_error"]),
            )
        except Exception as exc:
            return (
                current_scenario_dir,
                json.dumps(
                    {
                        "status": "error",
                        "source_scenario_dir": current_scenario_dir,
                        "requested_output_dir": target_dir,
                        "error": str(exc),
                    },
                    indent=2,
                    ensure_ascii=False,
                ),
                nodes_rows or [],
                components_rows or [],
                candidate_links_rows or [],
                edge_component_rules_rows or [],
                route_rows or [],
                layout_constraints_rows or [],
                topology_rules_text or "",
                scenario_settings_text or "",
                _build_execution_summary(None, str(exc)),
            )

    @app.callback(
        Output("node-studio-cytoscape", "elements"),
        Output("node-studio-cytoscape", "stylesheet"),
        Output("node-studio-summary", "children"),
        Output("edge-studio-summary", "children"),
        Output("studio-status", "children"),
        Input("nodes-grid", "rowData"),
        Input("candidate-links-grid", "rowData"),
        Input("routes-grid", "rowData"),
        Input("node-studio-selected-id", "data"),
        Input("edge-studio-selected-id", "data"),
        Input("studio-status-message", "data"),
    )
    def _refresh_node_studio(
        nodes_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        selected_edge_id: str | None,
        studio_status_message: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str, str]:
        normalized_nodes = nodes_rows or []
        normalized_links = candidate_links_rows or []
        normalized_routes = route_rows or []
        selected_id = _default_primary_node_studio_selection(
            normalized_nodes,
            normalized_links,
            preferred_node_id=selected_node_id,
        )
        selected_link_id = _default_primary_edge_studio_selection(
            normalized_nodes,
            normalized_links,
            preferred_link_id=selected_edge_id,
        )
        return (
            build_primary_node_studio_elements(normalized_nodes, normalized_links, normalized_routes),
            _build_node_studio_stylesheet(selected_id, selected_link_id),
            json.dumps(_build_node_studio_summary(normalized_nodes, selected_id), indent=2, ensure_ascii=False),
            json.dumps(
                _build_edge_studio_summary(normalized_nodes, normalized_links, selected_link_id),
                indent=2,
                ensure_ascii=False,
            ),
            str(studio_status_message or ""),
        )

    @app.callback(
        Output("node-studio-selected-id", "data"),
        Output("node-studio-node-id", "value"),
        Output("node-studio-label", "value"),
        Output("node-studio-node-type", "value"),
        Output("node-studio-x-m", "value"),
        Output("node-studio-y-m", "value"),
        Output("node-studio-allow-inbound", "value"),
        Output("node-studio-allow-outbound", "value"),
        Input("nodes-grid", "rowData"),
        Input("node-studio-cytoscape", "tapNodeData"),
        State("node-studio-selected-id", "data"),
    )
    def _sync_node_studio_form(
        nodes_rows: list[dict[str, Any]] | None,
        tap_node_data: dict[str, Any] | None,
        current_selected_node_id: str | None,
    ) -> tuple[str | None, str, str, str, float | None, float | None, list[str], list[str]]:
        selected_id = current_selected_node_id
        if tap_node_data:
            selected_id = str(tap_node_data.get("id") or tap_node_data.get("node_id") or "").strip() or current_selected_node_id
        selected_id = _default_node_studio_selection(nodes_rows or [], preferred_node_id=selected_id)
        form_values = _node_studio_form_values(nodes_rows or [], selected_id)
        return (
            selected_id,
            form_values["node_id"],
            form_values["label"],
            form_values["node_type"],
            form_values["x_m"],
            form_values["y_m"],
            form_values["allow_inbound"],
            form_values["allow_outbound"],
        )

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-apply-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        State("node-studio-node-id", "value"),
        State("node-studio-label", "value"),
        State("node-studio-node-type", "value"),
        State("node-studio-x-m", "value"),
        State("node-studio-y-m", "value"),
        State("node-studio-allow-inbound", "value"),
        State("node-studio-allow-outbound", "value"),
        State("candidate-links-grid", "rowData"),
        State("routes-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _apply_node_studio_properties(
        n_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        node_id: str | None,
        label: str | None,
        node_type: str | None,
        x_m: Any,
        y_m: Any,
        allow_inbound: list[str] | None,
        allow_outbound: list[str] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return nodes_rows or [], selected_node_id, ""
        try:
            updated_rows, next_selected_id = apply_node_studio_edit(
                nodes_rows or [],
                selected_node_id=selected_node_id,
                node_id=node_id,
                label=label,
                node_type=node_type,
                x_m=x_m,
                y_m=y_m,
                allow_inbound="allow_inbound" in (allow_inbound or []),
                allow_outbound="allow_outbound" in (allow_outbound or []),
                candidate_links_rows=candidate_links_rows or [],
                route_rows=route_rows or [],
            )
        except ValueError as exc:
            return nodes_rows or [], selected_node_id, str(exc)
        return updated_rows, next_selected_id, ""

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-focus-node-apply-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        State("studio-focus-node-label", "value"),
        State("candidate-links-grid", "rowData"),
        State("routes-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _apply_focus_node_quick_edit(
        n_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        label: str | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return nodes_rows or [], selected_node_id, ""
        selected_id = _default_node_studio_selection(nodes_rows or [], preferred_node_id=selected_node_id)
        selected_row = next(
            (dict(row) for row in (nodes_rows or []) if str(row.get("node_id", "")).strip() == selected_id),
            None,
        )
        if selected_row is None:
            return nodes_rows or [], selected_node_id, "Selecione um nó antes de aplicar edição direta no foco."
        try:
            updated_rows, next_selected_id = apply_node_studio_edit(
                nodes_rows or [],
                selected_node_id=selected_id,
                node_id=str(selected_row.get("node_id") or selected_id),
                label=label,
                node_type=str(selected_row.get("node_type") or ""),
                x_m=selected_row.get("x_m"),
                y_m=selected_row.get("y_m"),
                allow_inbound=bool(selected_row.get("allow_inbound")),
                allow_outbound=bool(selected_row.get("allow_outbound")),
                candidate_links_rows=candidate_links_rows or [],
                route_rows=route_rows or [],
            )
        except ValueError as exc:
            return nodes_rows or [], selected_node_id, str(exc)
        return updated_rows, next_selected_id, "Rótulo da entidade atualizado direto no foco do canvas."

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-move-button", "n_clicks"),
        Input("studio-focus-recommended-move-right-button", "n_clicks_timestamp"),
        Input("studio-focus-move-left-button", "n_clicks_timestamp"),
        Input("studio-focus-move-right-button", "n_clicks_timestamp"),
        Input("studio-focus-move-up-button", "n_clicks_timestamp"),
        Input("studio-focus-move-down-button", "n_clicks_timestamp"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        State("node-studio-move-direction", "value"),
        State("node-studio-move-step", "value"),
        prevent_initial_call=True,
    )
    def _move_node_studio_selection(
        n_clicks: Any,
        recommended_move_right_ts: Any,
        move_left_ts: Any,
        move_right_ts: Any,
        move_up_ts: Any,
        move_down_ts: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        direction: str | None,
        step: Any,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        quick_move_timestamps = {
            "right": max(_timestamp_or_zero(recommended_move_right_ts), _timestamp_or_zero(move_right_ts)),
            "left": _timestamp_or_zero(move_left_ts),
            "up": _timestamp_or_zero(move_up_ts),
            "down": _timestamp_or_zero(move_down_ts),
        }
        quick_direction = max(quick_move_timestamps, key=quick_move_timestamps.get)
        resolved_direction = quick_direction if quick_move_timestamps[quick_direction] > 0 else direction
        if not n_clicks and not any(quick_move_timestamps.values()):
            return nodes_rows or [], selected_node_id, ""
        updated_rows, next_selected_id = move_node_studio_selection(
            nodes_rows or [],
            selected_node_id=selected_node_id,
            direction=resolved_direction,
            step=step,
        )
        return updated_rows, next_selected_id, ""

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-create-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _create_node_studio_entry(
        n_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return nodes_rows or [], selected_node_id, ""
        updated_rows, next_selected_id = create_node_studio_node(
            nodes_rows or [],
            selected_node_id=selected_node_id,
        )
        return updated_rows, next_selected_id, ""

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-add-source-node-button", "n_clicks"),
        Input("studio-add-product-node-button", "n_clicks"),
        Input("studio-add-mixer-node-button", "n_clicks"),
        Input("studio-add-service-node-button", "n_clicks"),
        Input("studio-add-outlet-node-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _create_business_node_from_palette(
        source_clicks: Any,
        product_clicks: Any,
        mixer_clicks: Any,
        service_clicks: Any,
        outlet_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        click_map = {
            "source": int(source_clicks or 0),
            "product": int(product_clicks or 0),
            "mixer": int(mixer_clicks or 0),
            "service": int(service_clicks or 0),
            "outlet": int(outlet_clicks or 0),
        }
        preset_key = max(click_map, key=click_map.get)
        if click_map[preset_key] <= 0:
            return nodes_rows or [], selected_node_id, ""
        updated_rows, next_selected_id = create_business_node_studio_node(
            nodes_rows or [],
            selected_node_id=selected_node_id,
            preset_key=preset_key,
        )
        status_message = f"{BUSINESS_NODE_PRESETS[preset_key]['button_label']} adicionada ao canvas principal."
        return updated_rows, next_selected_id, status_message

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-duplicate-button", "n_clicks"),
        Input("studio-focus-duplicate-node-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _duplicate_node_studio_entry(
        *callback_args: Any,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if len(callback_args) == 3:
            n_clicks, nodes_rows, selected_node_id = callback_args
            quick_duplicate_clicks = 0
        else:
            n_clicks, quick_duplicate_clicks, nodes_rows, selected_node_id = callback_args
        if not n_clicks and not quick_duplicate_clicks:
            return nodes_rows or [], selected_node_id, ""
        updated_rows, next_selected_id = duplicate_node_studio_selection(
            nodes_rows or [],
            selected_node_id=selected_node_id,
        )
        return updated_rows, next_selected_id, ""

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-delete-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        State("candidate-links-grid", "rowData"),
        State("routes-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _delete_node_studio_entry(
        n_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return nodes_rows or [], selected_node_id, ""
        try:
            updated_rows, next_selected_id = delete_node_studio_selection(
                nodes_rows or [],
                selected_node_id=selected_node_id,
                candidate_links_rows=candidate_links_rows or [],
                route_rows=route_rows or [],
            )
        except ValueError as exc:
            return nodes_rows or [], selected_node_id, str(exc)
        return updated_rows, next_selected_id, ""

    @app.callback(
        Output("edge-studio-selected-id", "data"),
        Output("edge-studio-link-id", "value"),
        Output("edge-studio-from-node", "value"),
        Output("edge-studio-to-node", "value"),
        Output("edge-studio-archetype", "value"),
        Output("edge-studio-length-m", "value"),
        Output("edge-studio-bidirectional", "value"),
        Output("edge-studio-family-hint", "value"),
        Input("candidate-links-grid", "rowData"),
        Input("node-studio-cytoscape", "tapEdgeData"),
        State("edge-studio-selected-id", "data"),
    )
    def _sync_edge_studio_form(
        candidate_links_rows: list[dict[str, Any]] | None,
        tap_edge_data: dict[str, Any] | None,
        current_selected_link_id: str | None,
    ) -> tuple[str | None, str, str, str, str, float | None, list[str], str]:
        selected_link_id = current_selected_link_id
        if tap_edge_data:
            projected_link_id = str(tap_edge_data.get("link_id") or "").strip()
            if projected_link_id:
                selected_link_id = projected_link_id
        selected_link_id = _default_edge_studio_selection(
            candidate_links_rows or [],
            preferred_link_id=selected_link_id,
        )
        form_values = _edge_studio_form_values(candidate_links_rows or [], selected_link_id)
        return (
            selected_link_id,
            form_values["link_id"],
            form_values["from_node"],
            form_values["to_node"],
            form_values["archetype"],
            form_values["length_m"],
            form_values["bidirectional"],
            form_values["family_hint"],
        )

    @app.callback(
        Output("studio-quick-link-source", "options"),
        Output("studio-quick-link-source", "value"),
        Output("studio-quick-link-target", "options"),
        Output("studio-quick-link-target", "value"),
        Input("nodes-grid", "rowData"),
        Input("node-studio-summary", "children"),
        Input("edge-studio-summary", "children"),
        State("studio-quick-link-source", "value"),
        State("studio-quick-link-target", "value"),
    )
    def _sync_quick_link_controls(
        nodes_rows: list[dict[str, Any]] | None,
        node_summary_text: str | None,
        edge_summary_text: str | None,
        current_source: str | None,
        current_target: str | None,
    ) -> tuple[list[dict[str, str]], str | None, list[dict[str, str]], str | None]:
        business_options = _business_node_choice_options(nodes_rows or [])
        option_values = [option["value"] for option in business_options]
        node_summary = _safe_json_loads(node_summary_text)
        edge_summary = _safe_json_loads(edge_summary_text)
        default_source, default_target = _studio_quick_link_defaults(nodes_rows or [], node_summary, edge_summary)
        source_value = current_source if current_source in option_values else default_source
        target_candidates = [option for option in business_options if option["value"] != source_value]
        target_values = [option["value"] for option in target_candidates]
        target_value = current_target if current_target in target_values else default_target
        if target_value == source_value:
            target_value = target_values[0] if target_values else None
        return business_options, source_value, target_candidates, target_value

    @app.callback(
        Output("studio-route-focus-dropdown", "options"),
        Output("studio-route-focus-dropdown", "value"),
        Output("studio-route-intent", "value"),
        Output("studio-route-q-min-lpm", "value"),
        Output("studio-route-dose-min-l", "value"),
        Output("studio-route-notes", "value"),
        Output("studio-route-measurement-required", "value"),
        Input("routes-grid", "rowData"),
        Input("node-studio-summary", "children"),
        Input("edge-studio-summary", "children"),
        State("studio-route-focus-dropdown", "value"),
    )
    def _sync_route_focus_controls(
        route_rows: list[dict[str, Any]] | None,
        node_summary_text: str | None,
        edge_summary_text: str | None,
        current_route_id: str | None,
    ) -> tuple[list[dict[str, str]], str | None, str | None, float | None, float | None, str, list[str]]:
        node_summary = _safe_json_loads(node_summary_text)
        edge_summary = _safe_json_loads(edge_summary_text)
        focus_node_ids = {
            str(node_summary.get("selected_node_id") or "").strip(),
            str((edge_summary.get("selected_edge") or {}).get("from_node") or "").strip(),
            str((edge_summary.get("selected_edge") or {}).get("to_node") or "").strip(),
        }
        focus_node_ids = {node_id for node_id in focus_node_ids if node_id}
        options = _route_choice_options(route_rows, focus_node_ids=focus_node_ids)
        selected_route_id = _default_route_focus_selection(
            route_rows,
            focus_node_ids=focus_node_ids,
            preferred_route_id=current_route_id,
        )
        form_values = _route_studio_form_values(
            route_rows,
            focus_node_ids=focus_node_ids,
            selected_route_id=selected_route_id,
        )
        return (
            options,
            selected_route_id,
            form_values.get("intent"),
            form_values.get("q_min_delivered_lpm"),
            form_values.get("dose_min_l"),
            str(form_values.get("notes") or ""),
            list(form_values.get("measurement_required") or []),
        )

    @app.callback(
        Output("routes-grid", "rowData", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-route-apply-button", "n_clicks"),
        State("routes-grid", "rowData"),
        State("studio-route-focus-dropdown", "value"),
        State("studio-route-intent", "value"),
        State("studio-route-measurement-required", "value"),
        State("studio-route-dose-min-l", "value"),
        State("studio-route-q-min-lpm", "value"),
        State("studio-route-notes", "value"),
        prevent_initial_call=True,
    )
    def _apply_route_focus_edit(
        n_clicks: Any,
        route_rows: list[dict[str, Any]] | None,
        selected_route_id: str | None,
        intent: str | None,
        measurement_required: list[str] | None,
        dose_min_l: Any,
        q_min_delivered_lpm: Any,
        notes: str | None,
    ) -> tuple[list[dict[str, Any]], str]:
        if not n_clicks:
            return route_rows or [], ""
        try:
            updated_rows, route_id = apply_route_studio_edit(
                route_rows or [],
                selected_route_id=selected_route_id,
                intent=intent,
                measurement_required="measurement_required" in (measurement_required or []),
                dose_min_l=dose_min_l,
                q_min_delivered_lpm=q_min_delivered_lpm,
                notes=notes,
            )
        except ValueError as exc:
            return route_rows or [], str(exc)
        return updated_rows, f"Rota {route_id} atualizada direto no foco do canvas."

    @app.callback(
        Output("routes-grid", "rowData", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-route-create-from-edge-button", "n_clicks"),
        Input("studio-route-intent-mandatory-button", "n_clicks"),
        Input("studio-route-intent-desirable-button", "n_clicks"),
        Input("studio-route-intent-optional-button", "n_clicks"),
        State("routes-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        State("candidate-links-grid", "rowData"),
        State("studio-route-focus-dropdown", "value"),
        prevent_initial_call=True,
    )
    def _apply_route_canvas_quick_actions(
        create_route_n_clicks: Any,
        mandatory_n_clicks: Any,
        desirable_n_clicks: Any,
        optional_n_clicks: Any,
        route_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_route_id: str | None,
    ) -> tuple[list[dict[str, Any]], str]:
        click_map = {
            "create": int(create_route_n_clicks or 0),
            "mandatory": int(mandatory_n_clicks or 0),
            "desirable": int(desirable_n_clicks or 0),
            "optional": int(optional_n_clicks or 0),
        }
        action = max(click_map, key=click_map.get)
        if click_map[action] <= 0:
            return route_rows or [], ""
        try:
            if action == "create":
                updated_rows, created_route_id = create_route_from_edge_studio_selection(
                    route_rows or [],
                    selected_link_id=selected_link_id,
                    candidate_links_rows=candidate_links_rows or [],
                )
                return updated_rows, f"Rota {created_route_id} criada direto do trecho selecionado."
            if selected_route_id:
                updated_rows, route_id = apply_route_studio_edit(
                    route_rows or [],
                    selected_route_id=selected_route_id,
                    intent=action,
                    measurement_required=bool(
                        next(
                            (
                                route.get("measurement_required")
                                for route in (route_rows or [])
                                if str(route.get("route_id") or "").strip() == str(selected_route_id or "").strip()
                            ),
                            False,
                        )
                    ),
                    dose_min_l=next(
                        (
                            route.get("dose_min_l")
                            for route in (route_rows or [])
                            if str(route.get("route_id") or "").strip() == str(selected_route_id or "").strip()
                        ),
                        0.0,
                    ),
                    q_min_delivered_lpm=next(
                        (
                            route.get("q_min_delivered_lpm")
                            for route in (route_rows or [])
                            if str(route.get("route_id") or "").strip() == str(selected_route_id or "").strip()
                        ),
                        0.0,
                    ),
                    notes=next(
                        (
                            route.get("notes")
                            for route in (route_rows or [])
                            if str(route.get("route_id") or "").strip() == str(selected_route_id or "").strip()
                        ),
                        "",
                    ),
                )
            else:
                updated_rows, route_id = apply_route_intent_from_edge_context(
                    route_rows or [],
                    selected_link_id=selected_link_id,
                    candidate_links_rows=candidate_links_rows or [],
                    intent=action,
                )
        except ValueError as exc:
            return route_rows or [], str(exc)
        return updated_rows, f"Rota {route_id} marcada como {_route_intent_label(action).lower()} direto no contexto do canvas."

    @app.callback(
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("edge-studio-apply-button", "n_clicks"),
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        State("edge-studio-link-id", "value"),
        State("edge-studio-from-node", "value"),
        State("edge-studio-to-node", "value"),
        State("edge-studio-archetype", "value"),
        State("edge-studio-length-m", "value"),
        State("edge-studio-bidirectional", "value"),
        State("edge-studio-family-hint", "value"),
        State("nodes-grid", "rowData"),
        State("edge-component-rules-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _apply_edge_studio_properties(
        n_clicks: Any,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
        link_id: str | None,
        from_node: str | None,
        to_node: str | None,
        archetype: str | None,
        length_m: Any,
        bidirectional: list[str] | None,
        family_hint: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        edge_component_rules_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        try:
            updated_rows, next_selected_link_id = apply_edge_studio_edit(
                candidate_links_rows or [],
                selected_link_id=selected_link_id,
                link_id=link_id,
                from_node=from_node,
                to_node=to_node,
                archetype=archetype,
                length_m=length_m,
                bidirectional="bidirectional" in (bidirectional or []),
                family_hint=family_hint,
                nodes_rows=nodes_rows or [],
                edge_component_rules_rows=edge_component_rules_rows or [],
            )
        except ValueError as exc:
            return candidate_links_rows or [], selected_link_id, str(exc)
        return updated_rows, next_selected_link_id, ""

    @app.callback(
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-focus-edge-apply-button", "n_clicks"),
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        State("studio-focus-edge-length-m", "value"),
        State("studio-focus-edge-family-hint", "value"),
        State("nodes-grid", "rowData"),
        State("edge-component-rules-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _apply_focus_edge_quick_edit(
        n_clicks: Any,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
        length_m: Any,
        family_hint: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        edge_component_rules_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        selected_id = _default_edge_studio_selection(candidate_links_rows or [], preferred_link_id=selected_link_id)
        selected_row = next(
            (dict(row) for row in (candidate_links_rows or []) if str(row.get("link_id", "")).strip() == selected_id),
            None,
        )
        if selected_row is None:
            return candidate_links_rows or [], selected_link_id, "Selecione uma conexão antes de aplicar edição direta no foco."
        try:
            updated_rows, next_selected_link_id = apply_edge_studio_edit(
                candidate_links_rows or [],
                selected_link_id=selected_id,
                link_id=str(selected_row.get("link_id") or selected_id),
                from_node=str(selected_row.get("from_node") or ""),
                to_node=str(selected_row.get("to_node") or ""),
                archetype=str(selected_row.get("archetype") or ""),
                length_m=length_m,
                bidirectional=bool(selected_row.get("bidirectional")),
                family_hint=family_hint,
                nodes_rows=nodes_rows or [],
                edge_component_rules_rows=edge_component_rules_rows or [],
            )
        except ValueError as exc:
            return candidate_links_rows or [], selected_link_id, str(exc)
        return updated_rows, next_selected_link_id, "Conexão ajustada direto no foco do canvas."

    @app.callback(
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-focus-edge-reverse-button", "n_clicks"),
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        State("nodes-grid", "rowData"),
        State("routes-grid", "rowData"),
        State("edge-component-rules-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _reverse_focus_edge_direction(
        n_clicks: Any,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
        edge_component_rules_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        selected_id = _default_edge_studio_selection(candidate_links_rows or [], preferred_link_id=selected_link_id)
        try:
            updated_rows, next_selected_link_id, status = _reverse_edge_with_feedback(
                candidate_links_rows or [],
                selected_link_id=selected_id,
                nodes_rows=nodes_rows or [],
                route_rows=route_rows or [],
                edge_component_rules_rows=edge_component_rules_rows or [],
                message_prefix="Conexão invertida direto no foco do canvas.",
            )
        except ValueError as exc:
            return candidate_links_rows or [], selected_link_id, str(exc)
        return updated_rows, next_selected_link_id, status

    @app.callback(
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("studio-quick-link-create-button", "n_clicks"),
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        State("studio-quick-link-source", "value"),
        State("studio-quick-link-target", "value"),
        State("studio-quick-link-archetype", "value"),
        State("nodes-grid", "rowData"),
        State("edge-component-rules-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _create_quick_business_link(
        n_clicks: Any,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
        source_node_id: str | None,
        target_node_id: str | None,
        archetype: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        edge_component_rules_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        try:
            updated_rows, next_selected_link_id = create_edge_studio_link(
                candidate_links_rows or [],
                selected_link_id=selected_link_id,
                from_node=source_node_id,
                to_node=target_node_id,
                archetype=archetype or "bus_segment",
                length_m=0.18,
                bidirectional=False,
                family_hint=EDGE_ARCHETYPE_LABELS.get(str(archetype or "bus_segment"), "Conexão do cenário"),
                nodes_rows=nodes_rows or [],
                edge_component_rules_rows=edge_component_rules_rows or [],
            )
        except ValueError as exc:
            return candidate_links_rows or [], selected_link_id, str(exc)
        return updated_rows, next_selected_link_id, "Conexão de negócio criada no canvas principal."

    @app.callback(
        Output("nodes-grid", "rowData", allow_duplicate=True),
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("routes-grid", "rowData", allow_duplicate=True),
        Output("node-studio-selected-id", "data", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Output("studio-editor-workbench", "open", allow_duplicate=True),
        Input("node-studio-cytoscape", "contextMenuData"),
        State("nodes-grid", "rowData"),
        State("candidate-links-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        State("edge-studio-selected-id", "data"),
        State("routes-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _apply_studio_context_menu(
        context_menu_data: dict[str, Any] | None,
        nodes_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        selected_link_id: str | None,
        route_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str | None, str | None, str, bool]:
        return apply_studio_context_menu_action(
            context_menu_data=context_menu_data,
            nodes_rows=nodes_rows or [],
            candidate_links_rows=candidate_links_rows or [],
            selected_node_id=selected_node_id,
            selected_link_id=selected_link_id,
            route_rows=route_rows or [],
        )

    @app.callback(
        Output("studio-route-draft-source-id", "data"),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-cytoscape", "contextMenuData"),
        State("node-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _start_route_draft_from_context_menu(
        context_menu_data: dict[str, Any] | None,
        selected_node_id: str | None,
    ) -> tuple[str, str]:
        payload = context_menu_data or {}
        if str(payload.get("menuItemId") or "").strip() != "start-route-from-node":
            return "", ""
        source_node_id = str(payload.get("elementId") or selected_node_id or "").strip()
        if not source_node_id:
            return "", "Selecione uma entidade antes de iniciar a criação da rota."
        return source_node_id, f"Origem da rota armada em {source_node_id}. Selecione o destino no canvas."

    @app.callback(
        Output("routes-grid", "rowData", allow_duplicate=True),
        Output("studio-route-draft-source-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("node-studio-cytoscape", "tapNodeData"),
        State("studio-route-draft-source-id", "data"),
        State("routes-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _complete_route_draft_on_canvas(
        tap_node_data: dict[str, Any] | None,
        route_draft_source_id: str | None,
        route_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str, str]:
        draft_source = str(route_draft_source_id or "").strip()
        target_node_id = str((tap_node_data or {}).get("id") or (tap_node_data or {}).get("node_id") or "").strip()
        if not draft_source or not target_node_id or target_node_id == draft_source:
            return route_rows or [], draft_source, ""
        try:
            updated_rows, created_route_id = create_route_between_business_nodes(
                route_rows or [],
                source_node_id=draft_source,
                sink_node_id=target_node_id,
            )
        except ValueError as exc:
            return route_rows or [], "", str(exc)
        return updated_rows, "", f"Rota {created_route_id} criada direto no canvas entre {draft_source} e {target_node_id}."

    @app.callback(
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("edge-studio-create-button", "n_clicks"),
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        State("edge-studio-from-node", "value"),
        State("edge-studio-to-node", "value"),
        State("edge-studio-archetype", "value"),
        State("edge-studio-length-m", "value"),
        State("edge-studio-bidirectional", "value"),
        State("edge-studio-family-hint", "value"),
        State("nodes-grid", "rowData"),
        State("edge-component-rules-grid", "rowData"),
        prevent_initial_call=True,
    )
    def _create_edge_studio_entry(
        n_clicks: Any,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
        from_node: str | None,
        to_node: str | None,
        archetype: str | None,
        length_m: Any,
        bidirectional: list[str] | None,
        family_hint: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        edge_component_rules_rows: list[dict[str, Any]] | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        try:
            updated_rows, next_selected_link_id = create_edge_studio_link(
                candidate_links_rows or [],
                selected_link_id=selected_link_id,
                from_node=from_node,
                to_node=to_node,
                archetype=archetype,
                length_m=length_m,
                bidirectional="bidirectional" in (bidirectional or []),
                family_hint=family_hint,
                nodes_rows=nodes_rows or [],
                edge_component_rules_rows=edge_component_rules_rows or [],
            )
        except ValueError as exc:
            return candidate_links_rows or [], selected_link_id, str(exc)
        return updated_rows, next_selected_link_id, ""

    @app.callback(
        Output("candidate-links-grid", "rowData", allow_duplicate=True),
        Output("edge-studio-selected-id", "data", allow_duplicate=True),
        Output("studio-status-message", "data", allow_duplicate=True),
        Input("edge-studio-delete-button", "n_clicks"),
        Input("studio-focus-recommended-delete-edge-button", "n_clicks"),
        Input("studio-focus-delete-edge-button", "n_clicks"),
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _delete_edge_studio_entry(
        *callback_args: Any,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if len(callback_args) == 3:
            n_clicks, candidate_links_rows, selected_link_id = callback_args
            recommended_delete_clicks = 0
            quick_delete_clicks = 0
        elif len(callback_args) == 4:
            n_clicks, recommended_delete_clicks, candidate_links_rows, selected_link_id = callback_args
            quick_delete_clicks = 0
        else:
            n_clicks, recommended_delete_clicks, quick_delete_clicks, candidate_links_rows, selected_link_id = callback_args
        if not n_clicks and not recommended_delete_clicks and not quick_delete_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        updated_rows, next_selected_link_id = delete_edge_studio_selection(
            candidate_links_rows or [],
            selected_link_id=selected_link_id,
        )
        return updated_rows, next_selected_link_id, ""

    @app.callback(
        Output("studio-editor-workbench", "open"),
        Input("studio-canvas-open-workbench-button", "n_clicks"),
        Input("studio-readiness-open-workbench-button", "n_clicks"),
        Input("studio-workspace-open-workbench-button", "n_clicks"),
        Input("studio-command-open-workbench-button", "n_clicks"),
        Input("studio-focus-recommended-open-workbench-button", "n_clicks"),
        Input("studio-focus-open-workbench-button", "n_clicks"),
        prevent_initial_call=True,
    )
    def _open_studio_editor_workbench(
        canvas_n_clicks: Any,
        readiness_n_clicks: Any,
        workspace_n_clicks: Any,
        command_center_n_clicks: Any = None,
        recommended_n_clicks: Any = None,
        n_clicks: Any = None,
    ) -> bool:
        return bool(
            canvas_n_clicks
            or readiness_n_clicks
            or workspace_n_clicks
            or command_center_n_clicks
            or recommended_n_clicks
            or n_clicks
        )

    @app.callback(
        Output("run-jobs-summary", "children", allow_duplicate=True),
        Output("run-job-selected-id", "options", allow_duplicate=True),
        Output("run-job-selected-id", "value", allow_duplicate=True),
        Output("run-job-detail", "children", allow_duplicate=True),
        Output("run-jobs-status", "children", allow_duplicate=True),
        Input("run-job-enqueue-button", "n_clicks"),
        State("scenario-dir", "data"),
        State("run-queue-root", "data"),
        prevent_initial_call=True,
    )
    def _enqueue_current_scenario_run_job(
        n_clicks: Any,
        current_scenario_dir: str,
        current_run_queue_root: str,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        status_message = ""
        preferred_run_id = None
        if n_clicks:
            try:
                current_bundle = load_scenario_bundle(current_scenario_dir)
                queued_job = create_run_job(
                    current_scenario_dir,
                    queue_root=current_run_queue_root,
                    allow_diagnostic_python_emulation=_requires_diagnostic_python_emulation(current_bundle),
                )
                preferred_run_id = queued_job["run_id"]
                status_message = (
                    f"run_job {queued_job['run_id']} enfileirada em modo "
                    f"{queued_job['requested_execution_mode']}"
                )
            except Exception as exc:
                status_message = str(exc)
        snapshot = build_run_jobs_snapshot(current_run_queue_root, preferred_run_id=preferred_run_id)
        return (
            _serialize_json(snapshot["summary"]),
            snapshot["options"],
            snapshot["selected_run_id"],
            _serialize_json(snapshot["selected_run_detail"]),
            status_message,
        )

    @app.callback(
        Output("run-jobs-summary", "children", allow_duplicate=True),
        Output("run-job-selected-id", "options", allow_duplicate=True),
        Output("run-job-selected-id", "value", allow_duplicate=True),
        Output("run-job-detail", "children", allow_duplicate=True),
        Output("run-jobs-status", "children", allow_duplicate=True),
        Input("run-jobs-run-next-button", "n_clicks"),
        State("run-job-selected-id", "value"),
        State("run-queue-root", "data"),
        prevent_initial_call=True,
    )
    def _run_next_serial_queue_job(
        n_clicks: Any,
        selected_run_id: str | None,
        current_run_queue_root: str,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        status_message = ""
        preferred_run_id = selected_run_id
        if n_clicks:
            try:
                executed_job = run_next_queued_job(queue_root=current_run_queue_root)
                if executed_job is None:
                    status_message = "Nenhum run_job em queued para execução."
                else:
                    preferred_run_id = executed_job["run_id"]
                    status_message = f"run_job {executed_job['run_id']} -> {executed_job['status']}"
            except Exception as exc:
                status_message = str(exc)
        snapshot = build_run_jobs_snapshot(current_run_queue_root, preferred_run_id=preferred_run_id)
        return (
            _serialize_json(snapshot["summary"]),
            snapshot["options"],
            snapshot["selected_run_id"],
            _serialize_json(snapshot["selected_run_detail"]),
            status_message,
        )

    @app.callback(
        Output("run-jobs-summary", "children"),
        Output("run-job-selected-id", "options"),
        Output("run-job-selected-id", "value"),
        Output("run-job-detail", "children"),
        Output("run-jobs-status", "children"),
        Input("run-jobs-refresh-button", "n_clicks"),
        State("run-job-selected-id", "value"),
        State("run-queue-root", "data"),
    )
    def _refresh_run_jobs_summary(
        n_clicks: Any,
        selected_run_id: str | None,
        current_run_queue_root: str,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        if not n_clicks:
            return (
                initial_run_jobs_summary,
                initial_run_job_options,
                initial_run_job_selected_id,
                initial_run_job_detail,
                "",
            )
        snapshot = build_run_jobs_snapshot(current_run_queue_root, preferred_run_id=selected_run_id)
        return (
            _serialize_json(snapshot["summary"]),
            snapshot["options"],
            snapshot["selected_run_id"],
            _serialize_json(snapshot["selected_run_detail"]),
            "",
        )

    @app.callback(
        Output("run-jobs-summary", "children", allow_duplicate=True),
        Output("run-job-selected-id", "options", allow_duplicate=True),
        Output("run-job-selected-id", "value", allow_duplicate=True),
        Output("run-job-detail", "children", allow_duplicate=True),
        Output("run-jobs-status", "children", allow_duplicate=True),
        Input("run-job-cancel-button", "n_clicks"),
        State("run-job-selected-id", "value"),
        State("run-queue-root", "data"),
        prevent_initial_call=True,
    )
    def _cancel_selected_run_job(
        n_clicks: Any,
        selected_run_id: str | None,
        current_run_queue_root: str,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        status_message = ""
        preferred_run_id = selected_run_id
        if n_clicks:
            if not selected_run_id:
                status_message = "Nenhuma run selecionada para cancelamento."
            else:
                try:
                    job = cancel_run_job(selected_run_id, queue_root=current_run_queue_root)
                    preferred_run_id = job["run_id"]
                    status_message = f"run_job {job['run_id']} -> {job['status']}"
                except Exception as exc:
                    status_message = str(exc)
        snapshot = build_run_jobs_snapshot(current_run_queue_root, preferred_run_id=preferred_run_id)
        return (
            _serialize_json(snapshot["summary"]),
            snapshot["options"],
            snapshot["selected_run_id"],
            _serialize_json(snapshot["selected_run_detail"]),
            status_message,
        )

    @app.callback(
        Output("run-jobs-summary", "children", allow_duplicate=True),
        Output("run-job-selected-id", "options", allow_duplicate=True),
        Output("run-job-selected-id", "value", allow_duplicate=True),
        Output("run-job-detail", "children", allow_duplicate=True),
        Output("run-jobs-status", "children", allow_duplicate=True),
        Input("run-job-rerun-button", "n_clicks"),
        State("run-job-selected-id", "value"),
        State("run-queue-root", "data"),
        prevent_initial_call=True,
    )
    def _rerun_selected_run_job(
        n_clicks: Any,
        selected_run_id: str | None,
        current_run_queue_root: str,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        status_message = ""
        preferred_run_id = selected_run_id
        if n_clicks:
            if not selected_run_id:
                status_message = "Nenhuma run selecionada para reexecução."
            else:
                try:
                    rerun_job = rerun_run_job(selected_run_id, queue_root=current_run_queue_root)
                    preferred_run_id = rerun_job["run_id"]
                    status_message = (
                        f"run_job {rerun_job['run_id']} enfileirada como re-run de {selected_run_id}"
                    )
                except Exception as exc:
                    status_message = str(exc)
        snapshot = build_run_jobs_snapshot(current_run_queue_root, preferred_run_id=preferred_run_id)
        return (
            _serialize_json(snapshot["summary"]),
            snapshot["options"],
            snapshot["selected_run_id"],
            _serialize_json(snapshot["selected_run_detail"]),
            status_message,
        )

    @app.callback(
        Output("run-job-detail", "children", allow_duplicate=True),
        Input("run-job-selected-id", "value"),
        State("run-queue-root", "data"),
        prevent_initial_call=True,
    )
    def _refresh_selected_run_job_detail(selected_run_id: str | None, current_run_queue_root: str) -> str:
        return _serialize_json(build_run_job_detail_summary(selected_run_id, queue_root=current_run_queue_root))

    @app.callback(
        Output("profile-dropdown", "options"),
        Output("profile-dropdown", "value"),
        Output("family-dropdown", "options"),
        Output("family-dropdown", "value"),
        Output("weight-cost", "value"),
        Output("weight-quality", "value"),
        Output("weight-flow", "value"),
        Output("weight-resilience", "value"),
        Output("weight-cleaning", "value"),
        Output("weight-operability", "value"),
        Input("scenario-dir", "data"),
        State("profile-dropdown", "value"),
        State("family-dropdown", "value"),
    )
    def _refresh_scenario_controls(
        current_scenario_dir: str,
        current_profile_id: str | None,
        current_family: str | None,
    ) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]], str, float, float, float, float, float, float]:
        current_bundle = load_scenario_bundle(current_scenario_dir)
        profile_options = _profile_dropdown_options(current_bundle)
        valid_profiles = {option["value"] for option in profile_options}
        profile_value = current_profile_id if current_profile_id in valid_profiles else str(
            current_bundle.scenario_settings["ranking"]["default_profile"]
        )
        family_options = _family_dropdown_options(current_bundle)
        valid_families = {option["value"] for option in family_options}
        family_value = current_family if current_family in valid_families else "ALL"
        weights = _weight_input_values(current_bundle, profile_value)
        return (
            profile_options,
            profile_value,
            family_options,
            family_value,
            weights["cost_weight"],
            weights["quality_weight"],
            weights["flow_weight"],
            weights["resilience_weight"],
            weights["cleaning_weight"],
            weights["operability_weight"],
        )

    @app.callback(
        Output("execution-summary", "children"),
        Input("run-button", "n_clicks"),
        State("scenario-dir", "data"),
    )
    def _run_pipeline(n_clicks: Any, current_scenario_dir: str) -> str:
        if not n_clicks:
            return _build_execution_summary(result, pipeline_error)
        rerun, rerun_error = _safe_run_pipeline(current_scenario_dir)
        return _build_execution_summary(rerun, rerun_error)

    @app.callback(
        Output("catalog-grid", "rowData"),
        Output("family-summary-grid", "rowData"),
        Output("selected-candidate-dropdown", "options"),
        Output("selected-candidate-dropdown", "value"),
        Output("compare-candidates-dropdown", "options"),
        Output("compare-candidates-dropdown", "value"),
        Output("catalog-state-summary", "children"),
        Input("scenario-dir", "data"),
        Input("profile-dropdown", "value"),
        Input("family-dropdown", "value"),
        Input("feasible-only-checklist", "value"),
        Input("max-cost-input", "value"),
        Input("min-quality-input", "value"),
        Input("min-flow-input", "value"),
        Input("min-resilience-input", "value"),
        Input("min-cleaning-input", "value"),
        Input("min-operability-input", "value"),
        Input("top-n-family-input", "value"),
        Input("fallback-filter-dropdown", "value"),
        Input("infeasibility-reason-dropdown", "value"),
        Input("weight-cost", "value"),
        Input("weight-quality", "value"),
        Input("weight-flow", "value"),
        Input("weight-resilience", "value"),
        Input("weight-cleaning", "value"),
        Input("weight-operability", "value"),
        State("selected-candidate-dropdown", "value"),
        State("compare-candidates-dropdown", "value"),
    )
    def _rerank_catalog(
        current_scenario_dir: str,
        profile: str,
        family: str,
        feasible_only: list[str],
        max_cost: Any,
        min_quality: Any,
        min_flow: Any,
        min_resilience: Any,
        min_cleaning: Any,
        min_operability: Any,
        top_n_per_family: Any,
        fallback_filter: str,
        infeasibility_reason: str,
        cost_weight: Any,
        quality_weight: Any,
        flow_weight: Any,
        resilience_weight: Any,
        cleaning_weight: Any,
        operability_weight: Any,
        current_selected_id: str | None,
        current_compare_ids: Any,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str | None, list[dict[str, Any]], list[str], str]:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not current_result:
            return [], [], [], None, [], [], json.dumps({}, ensure_ascii=False)
        weights = {
            "cost_weight": cost_weight,
            "quality_weight": quality_weight,
            "flow_weight": flow_weight,
            "resilience_weight": resilience_weight,
            "cleaning_weight": cleaning_weight,
            "operability_weight": operability_weight,
        }
        view_state = build_catalog_view_state(
            current_result,
            profile_id=profile,
            weight_overrides=weights,
            family=family,
            feasible_only="feasible_only" in (feasible_only or []),
            max_cost=max_cost,
            min_quality=min_quality,
            min_flow=min_flow,
            min_resilience=min_resilience,
            min_cleaning=min_cleaning,
            min_operability=min_operability,
            top_n_per_family=top_n_per_family,
            fallback_filter=fallback_filter,
            infeasibility_reason=infeasibility_reason,
            current_selected_id=current_selected_id,
            current_compare_ids=current_compare_ids,
        )
        filters = {
            "family": family,
            "feasible_only": "feasible_only" in (feasible_only or []),
            "max_cost": max_cost,
            "min_quality": min_quality,
            "min_flow": min_flow,
            "min_resilience": min_resilience,
            "min_cleaning": min_cleaning,
            "min_operability": min_operability,
            "top_n_per_family": top_n_per_family,
            "fallback_filter": fallback_filter,
            "infeasibility_reason": infeasibility_reason,
            "weight_overrides": weights,
        }
        return (
            view_state["ranked_records"],
            view_state["family_summary_records"],
            view_state["selected_options"],
            view_state["selected_candidate_id"],
            view_state["comparison_options"],
            view_state["comparison_ids"],
            _build_catalog_state_summary(
                profile_id=profile,
                selected_candidate_id=view_state["selected_candidate_id"],
                ranked_records=view_state["ranked_records"],
                filters=filters,
                aggregate_summary=current_result.get("summary", {}),
            ),
        )

    @app.callback(
        Output("circuit-cytoscape", "elements"),
        Output("route-highlight-dropdown", "options"),
        Output("route-highlight-dropdown", "value"),
        Output("route-metrics-grid", "rowData"),
        Output("selected-candidate-summary", "children"),
        Output("candidate-breakdown", "children"),
        Output("official-candidate-summary", "children"),
        Input("scenario-dir", "data"),
        Input("selected-candidate-dropdown", "value"),
        Input("profile-dropdown", "value"),
    )
    def _update_selected_candidate(
        current_scenario_dir: str,
        candidate_id: str,
        active_profile_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, list[dict[str, Any]], str, str, str]:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not current_result or not candidate_id:
            empty = json.dumps({}, ensure_ascii=False)
            return [], [], None, [], empty, empty, empty
        detail = build_candidate_detail(current_result, candidate_id, profile_id=active_profile_id)
        route_options = _route_dropdown_options(detail["route_rows"])
        route_value = _default_route_highlight(detail["route_rows"])
        return (
            detail["cytoscape_elements"],
            route_options,
            route_value,
            detail["route_rows"],
            json.dumps(detail["summary"], indent=2, ensure_ascii=False),
            json.dumps(detail["breakdown"], indent=2, ensure_ascii=False),
            json.dumps(
                build_official_candidate_summary(current_result, profile_id=active_profile_id, candidate_id=None),
                indent=2,
                ensure_ascii=False,
            ),
        )

    @app.callback(
        Output("circuit-cytoscape", "stylesheet"),
        Input("scenario-dir", "data"),
        Input("selected-candidate-dropdown", "value"),
        Input("route-highlight-dropdown", "value"),
    )
    def _highlight_route(current_scenario_dir: str, candidate_id: str | None, route_id: str | None) -> list[dict[str, Any]]:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not current_result:
            return _build_cytoscape_stylesheet({}, None, [])
        detail = build_candidate_detail(current_result, candidate_id)
        return _build_cytoscape_stylesheet(
            detail.get("route_highlights", {}),
            route_id,
            detail.get("critical_component_ids", []),
        )

    @app.callback(
        Output("comparison-figure", "figure"),
        Output("comparison-grid", "rowData"),
        Input("scenario-dir", "data"),
        Input("compare-candidates-dropdown", "value"),
        Input("profile-dropdown", "value"),
        Input("selected-candidate-dropdown", "value"),
    )
    def _update_comparison(
        current_scenario_dir: str,
        candidate_ids: Any,
        profile: str,
        selected_candidate_id: str | None,
    ) -> tuple[Any, list[dict[str, Any]]]:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not current_result:
            return build_solution_comparison_figure([]), []
        normalized_ids = _normalize_compare_ids(candidate_ids)
        return (
            build_solution_comparison_figure(_lookup_candidates(current_result, normalized_ids)),
            build_comparison_records(
                current_result,
                normalized_ids,
                profile_id=profile,
                active_selected_id=selected_candidate_id,
            ),
        )

    @app.callback(
        Output("catalog-download", "data"),
        Input("export-catalog-button", "n_clicks"),
        State("profile-dropdown", "value"),
        State("family-dropdown", "value"),
        State("feasible-only-checklist", "value"),
        State("max-cost-input", "value"),
        State("min-quality-input", "value"),
        State("min-flow-input", "value"),
        State("min-resilience-input", "value"),
        State("min-cleaning-input", "value"),
        State("min-operability-input", "value"),
        State("top-n-family-input", "value"),
        State("fallback-filter-dropdown", "value"),
        State("infeasibility-reason-dropdown", "value"),
        State("weight-cost", "value"),
        State("weight-quality", "value"),
        State("weight-flow", "value"),
        State("weight-resilience", "value"),
        State("weight-cleaning", "value"),
        State("weight-operability", "value"),
        State("scenario-dir", "data"),
        prevent_initial_call=True,
    )
    def _export_catalog(
        n_clicks: Any,
        profile: str,
        family: str,
        feasible_only: list[str],
        max_cost: Any,
        min_quality: Any,
        min_flow: Any,
        min_resilience: Any,
        min_cleaning: Any,
        min_operability: Any,
        top_n_per_family: Any,
        fallback_filter: str,
        infeasibility_reason: str,
        cost_weight: Any,
        quality_weight: Any,
        flow_weight: Any,
        resilience_weight: Any,
        cleaning_weight: Any,
        operability_weight: Any,
        current_scenario_dir: str,
    ) -> Any:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not n_clicks or not current_result:
            return None
        weights = {
            "cost_weight": cost_weight,
            "quality_weight": quality_weight,
            "flow_weight": flow_weight,
            "resilience_weight": resilience_weight,
            "cleaning_weight": cleaning_weight,
            "operability_weight": operability_weight,
        }
        view_state = build_catalog_view_state(
            current_result,
            profile_id=profile,
            weight_overrides=weights,
            family=family,
            feasible_only="feasible_only" in (feasible_only or []),
            max_cost=max_cost,
            min_quality=min_quality,
            min_flow=min_flow,
            min_resilience=min_resilience,
            min_cleaning=min_cleaning,
            min_operability=min_operability,
            top_n_per_family=top_n_per_family,
            fallback_filter=fallback_filter,
            infeasibility_reason=infeasibility_reason,
        )
        return _send_text_download(
            json.dumps(view_state["ranked_records"], indent=2, ensure_ascii=False),
            "ranked_catalog.json",
        )

    @app.callback(
        Output("comparison-download", "data"),
        Input("export-comparison-button", "n_clicks"),
        State("compare-candidates-dropdown", "value"),
        State("profile-dropdown", "value"),
        State("selected-candidate-dropdown", "value"),
        State("scenario-dir", "data"),
        prevent_initial_call=True,
    )
    def _export_comparison(
        n_clicks: Any,
        candidate_ids: Any,
        profile: str,
        selected_candidate_id: str | None,
        current_scenario_dir: str,
    ) -> Any:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not n_clicks or not current_result:
            return None
        records = build_comparison_records(
            current_result,
            _normalize_compare_ids(candidate_ids),
            profile_id=profile,
            active_selected_id=selected_candidate_id,
        )
        if not records:
            return None
        return _send_text_download(
            pd.DataFrame(records).to_csv(index=False),
            f"comparison_{profile}.csv",
        )

    @app.callback(
        Output("comparison-json-download", "data"),
        Input("export-comparison-json-button", "n_clicks"),
        State("compare-candidates-dropdown", "value"),
        State("profile-dropdown", "value"),
        State("selected-candidate-dropdown", "value"),
        State("scenario-dir", "data"),
        prevent_initial_call=True,
    )
    def _export_comparison_json(
        n_clicks: Any,
        candidate_ids: Any,
        profile: str,
        selected_candidate_id: str | None,
        current_scenario_dir: str,
    ) -> Any:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not n_clicks or not current_result:
            return None
        records = build_comparison_records(
            current_result,
            _normalize_compare_ids(candidate_ids),
            profile_id=profile,
            active_selected_id=selected_candidate_id,
        )
        if not records:
            return None
        return _send_text_download(
            json.dumps(records, indent=2, ensure_ascii=False),
            f"comparison_{profile}.json",
        )

    @app.callback(
        Output("selected-candidate-download", "data"),
        Input("export-selected-button", "n_clicks"),
        State("selected-candidate-dropdown", "value"),
        State("scenario-dir", "data"),
        prevent_initial_call=True,
    )
    def _export_selected_candidate(n_clicks: Any, candidate_id: str, current_scenario_dir: str) -> Any:
        current_result, _ = _safe_run_pipeline(current_scenario_dir)
        if not n_clicks or not current_result or not candidate_id:
            return None
        detail = build_candidate_detail(current_result, candidate_id)
        candidate = next(item for item in current_result["catalog"] if item["candidate_id"] == candidate_id)
        payload = {
            "candidate_id": candidate_id,
            "topology_family": candidate["topology_family"],
            "generation_source": candidate.get("generation_source"),
            "generation_metadata": candidate.get("generation_metadata", {}),
            "metrics": candidate["metrics"],
            "render": candidate["render"],
            "breakdown": detail["breakdown"],
        }
        return _send_text_download(
            json.dumps(payload, indent=2, ensure_ascii=False),
            f"{candidate_id}.json",
        )

    @app.callback(
        Output("studio-canvas-guidance-panel", "children"),
        Output("studio-command-center-shell", "children"),
        Output("studio-workspace-panel", "children"),
        Output("studio-readiness-panel", "children"),
        Output("studio-projection-coverage-panel", "children"),
        Output("runs-workspace-panel", "children"),
        Output("runs-flow-panel", "children"),
        Output("studio-focus-panel", "children"),
        Output("studio-connectivity-panel", "children"),
        Output("node-studio-summary-panel", "children"),
        Output("edge-studio-summary-panel", "children"),
        Input("nodes-grid", "rowData"),
        Input("candidate-links-grid", "rowData"),
        Input("routes-grid", "rowData"),
        Input("run-jobs-summary", "children"),
        Input("execution-summary", "children"),
        Input("node-studio-summary", "children"),
        Input("edge-studio-summary", "children"),
        Input("studio-status", "children"),
        Input("studio-route-draft-source-id", "data"),
    )
    def _refresh_studio_panels(
        nodes_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
        run_jobs_summary_text: str | None,
        execution_summary_text: str | None,
        node_summary_text: str | None,
        edge_summary_text: str | None,
        studio_status_text: str | None,
        route_draft_source_id: str | None,
    ) -> tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any, Any, Any]:
        studio_readiness = build_studio_readiness_summary(nodes_rows or [], candidate_links_rows or [], route_rows or [])
        node_summary = _safe_json_loads(node_summary_text)
        edge_summary = _safe_json_loads(edge_summary_text)
        run_jobs_summary = _safe_json_loads(run_jobs_summary_text)
        execution_summary = _safe_json_loads(execution_summary_text)
        return (
            render_studio_canvas_guidance_panel(studio_readiness, node_summary, edge_summary),
            render_studio_command_center_panel(
                studio_readiness,
                node_summary,
                edge_summary,
                nodes_rows or [],
                candidate_links_rows or [],
                route_rows,
            ),
            render_studio_workspace_panel(
                studio_readiness,
                node_summary,
                edge_summary,
                nodes_rows or [],
                candidate_links_rows or [],
                route_rows,
                studio_status_text,
                route_draft_source_id,
            ),
            render_studio_readiness_panel(studio_readiness),
            render_studio_projection_panel(
                build_studio_projection_summary(nodes_rows or [], candidate_links_rows or [], route_rows or [])
            ),
            render_runs_workspace_panel(
                studio_readiness,
                run_jobs_summary,
                execution_summary,
            ),
            render_runs_flow_panel(
                studio_readiness,
                run_jobs_summary,
                execution_summary,
            ),
            render_studio_focus_panel(
                node_summary,
                edge_summary,
                nodes_rows or [],
                candidate_links_rows or [],
                route_rows,
                studio_readiness,
                studio_status_text,
            ),
            render_studio_connectivity_panel(
                studio_readiness,
                node_summary,
                edge_summary,
                route_rows,
                nodes_rows,
                candidate_links_rows,
            ),
            render_studio_selection_panel(node_summary, "node"),
            render_studio_selection_panel(edge_summary, "edge"),
        )

    @app.callback(
        Output("studio-technical-guide", "open"),
        Input("studio-canvas-open-technical-guide-button", "n_clicks"),
        Input("studio-open-technical-guide-button", "n_clicks"),
        State("studio-technical-guide", "open"),
        prevent_initial_call=True,
    )
    def _open_studio_technical_guide(canvas_n_clicks: Any, n_clicks: Any, is_open: bool | None) -> bool:
        if not canvas_n_clicks and not n_clicks:
            return bool(is_open)
        return True

    @app.callback(
        Output("primary-navigation-tabs", "value"),
        Input("ui-location", "search"),
        Input("studio-open-audit-button", "n_clicks_timestamp"),
        Input("studio-open-runs-button", "n_clicks_timestamp"),
        Input("studio-workspace-open-runs-button", "n_clicks_timestamp"),
        Input("runs-workspace-open-decision-button", "n_clicks_timestamp"),
        Input("runs-flow-open-decision-button", "n_clicks_timestamp"),
        Input("execution-open-decision-button", "n_clicks_timestamp"),
        State("primary-navigation-tabs", "value"),
    )
    def _resolve_primary_navigation(
        search: str | None,
        open_audit_ts: Any,
        open_runs_ts: Any,
        workspace_open_runs_ts: Any,
        runs_workspace_open_decision_ts: Any,
        runs_flow_open_decision_ts: Any,
        execution_open_decision_ts: Any,
        current_tab: str | None,
    ) -> str:
        latest_click = max(
            [
                (_timestamp_or_zero(open_audit_ts), "audit"),
                (_timestamp_or_zero(open_runs_ts), "runs"),
                (_timestamp_or_zero(workspace_open_runs_ts), "runs"),
                (_timestamp_or_zero(runs_workspace_open_decision_ts), "decision"),
                (_timestamp_or_zero(runs_flow_open_decision_ts), "decision"),
                (_timestamp_or_zero(execution_open_decision_ts), "decision"),
            ],
            key=lambda item: item[0],
        )
        if latest_click[0] > 0:
            return latest_click[1]
        if search:
            return _primary_tab_from_search(search, default=str(current_tab or "studio"))
        return str(current_tab or "studio")

    @app.callback(
        Output("product-journey-panel", "children"),
        Input("primary-navigation-tabs", "value"),
        Input("nodes-grid", "rowData"),
        Input("candidate-links-grid", "rowData"),
        Input("routes-grid", "rowData"),
        Input("run-jobs-summary", "children"),
        Input("official-candidate-summary", "children"),
    )
    def _refresh_product_journey_panel(
        current_tab: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
        run_jobs_summary_text: str | None,
        decision_summary_text: str | None,
    ) -> Any:
        studio_summary = build_studio_readiness_summary(nodes_rows or [], candidate_links_rows or [], route_rows or [])
        return render_product_journey_panel(
            current_tab,
            studio_summary,
            _safe_json_loads(run_jobs_summary_text),
            _safe_json_loads(decision_summary_text),
        )

    @app.callback(
        Output("product-space-banner", "children"),
        Input("primary-navigation-tabs", "value"),
        Input("nodes-grid", "rowData"),
        Input("candidate-links-grid", "rowData"),
        Input("routes-grid", "rowData"),
        Input("run-jobs-summary", "children"),
        Input("official-candidate-summary", "children"),
    )
    def _refresh_product_space_banner(
        current_tab: str | None,
        nodes_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        route_rows: list[dict[str, Any]] | None,
        run_jobs_summary_text: str | None,
        decision_summary_text: str | None,
    ) -> Any:
        studio_summary = build_studio_readiness_summary(nodes_rows or [], candidate_links_rows or [], route_rows or [])
        return render_product_space_banner(
            current_tab,
            studio_summary,
            _safe_json_loads(run_jobs_summary_text),
            _safe_json_loads(decision_summary_text),
        )

    @app.callback(
        Output("run-jobs-overview-panel", "children"),
        Output("run-job-detail-panel", "children"),
        Output("run-jobs-status-banner", "children"),
        Input("run-jobs-summary", "children"),
        Input("run-job-detail", "children"),
        Input("run-jobs-status", "children"),
    )
    def _refresh_run_panels(
        summary_text: str | None,
        detail_text: str | None,
        status_text: str | None,
    ) -> tuple[Any, Any, Any]:
        return (
            render_run_jobs_overview_panel(_safe_json_loads(summary_text)),
            render_run_job_detail_panel(_safe_json_loads(detail_text)),
            render_status_banner(status_text),
        )

    @app.callback(
        Output("execution-summary-panel", "children"),
        Output("bundle-io-summary-panel", "children"),
        Output("audit-workspace-panel", "children"),
        Input("execution-summary", "children"),
        Input("bundle-io-summary", "children"),
    )
    def _refresh_audit_panels(execution_text: str | None, bundle_text: str | None) -> tuple[Any, Any, Any]:
        execution_payload = _safe_json_loads(execution_text)
        bundle_payload = _safe_json_loads(bundle_text)
        return (
            render_execution_summary_panel(execution_payload),
            render_bundle_io_panel(bundle_payload),
            render_audit_workspace_panel(bundle_payload, execution_payload),
        )

    @app.callback(
        Output("decision-workspace-panel", "children"),
        Output("decision-summary-panel", "children"),
        Output("decision-summary-panel-extended", "children"),
        Output("decision-contrast-panel", "children"),
        Output("decision-signal-panel", "children"),
        Output("decision-flow-panel", "children"),
        Output("catalog-state-summary-panel", "children"),
        Output("selected-candidate-summary-panel", "children"),
        Output("candidate-breakdown-panel", "children"),
        Input("official-candidate-summary", "children"),
        Input("catalog-state-summary", "children"),
        Input("selected-candidate-summary", "children"),
        Input("candidate-breakdown", "children"),
    )
    def _refresh_decision_panels(
        official_text: str | None,
        catalog_text: str | None,
        candidate_text: str | None,
        breakdown_text: str | None,
    ) -> tuple[Any, Any, Any, Any, Any, Any, Any, Any, Any]:
        official_payload = _safe_json_loads(official_text)
        catalog_payload = _safe_json_loads(catalog_text)
        return (
            render_decision_workspace_panel(official_payload, catalog_payload),
            render_decision_summary_panel(official_payload),
            render_decision_summary_panel(official_payload),
            render_decision_contrast_panel(official_payload),
            render_decision_signal_panel(official_payload),
            render_decision_flow_panel(official_payload),
            render_catalog_state_panel(catalog_payload),
            render_candidate_summary_panel(_safe_json_loads(candidate_text)),
            render_candidate_breakdown_panel(_safe_json_loads(breakdown_text)),
        )

    return app


def rerank_catalog(result: dict[str, Any], profile_id: str, weight_overrides: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if not result:
        return []
    if _weight_overrides_active(weight_overrides):
        weights = {key: float(value) if value not in (None, "") else 0.0 for key, value in (weight_overrides or {}).items()}
        return apply_dynamic_weights(result["catalog_frame"], weights)
    return result["ranked_profiles"].get(profile_id, [])


def build_catalog_view_state(
    result: dict[str, Any] | None,
    *,
    profile_id: str,
    weight_overrides: dict[str, Any] | None = None,
    family: str | None = None,
    feasible_only: bool = False,
    max_cost: Any = None,
    min_quality: Any = None,
    min_flow: Any = None,
    min_resilience: Any = None,
    min_cleaning: Any = None,
    min_operability: Any = None,
    top_n_per_family: Any = None,
    fallback_filter: str | None = None,
    infeasibility_reason: str | None = None,
    current_selected_id: str | None = None,
    current_compare_ids: list[str] | str | None = None,
) -> dict[str, Any]:
    if not result:
        return {
            "ranked_records": [],
            "family_summary_records": [],
            "selected_candidate_id": None,
            "selected_options": [],
            "comparison_ids": [],
            "comparison_options": [],
        }
    ranked_records = rerank_catalog(result, profile_id, weight_overrides)
    filtered_records = filter_catalog_records(
        ranked_records,
        family=family,
        feasible_only=feasible_only,
        max_cost=max_cost,
        min_quality=min_quality,
        min_flow=min_flow,
        min_resilience=min_resilience,
        min_cleaning=min_cleaning,
        min_operability=min_operability,
        top_n_per_family=top_n_per_family,
        fallback_filter=fallback_filter,
        infeasibility_reason=infeasibility_reason,
    )
    family_summary_records = _family_summary_from_records(filtered_records)
    selected_candidate_id = select_visible_candidate_id(
        result,
        profile_id=profile_id,
        filtered_records=filtered_records,
        current_selected_id=current_selected_id,
        weight_overrides=weight_overrides,
        filters_active=_filters_active(
            family=family,
            feasible_only=feasible_only,
            max_cost=max_cost,
            min_quality=min_quality,
            min_flow=min_flow,
            min_resilience=min_resilience,
            min_cleaning=min_cleaning,
            min_operability=min_operability,
            top_n_per_family=top_n_per_family,
            fallback_filter=fallback_filter,
            infeasibility_reason=infeasibility_reason,
        ),
    )
    selected_options = [
        {"label": record["candidate_id"], "value": record["candidate_id"]}
        for record in filtered_records
    ]
    normalized_compare_ids = _normalize_compare_ids(current_compare_ids)
    visible_ids = {record["candidate_id"] for record in filtered_records}
    comparison_ids = [candidate_id for candidate_id in normalized_compare_ids if candidate_id in visible_ids]
    if not comparison_ids:
        comparison_ids = _default_comparison_ids(result, profile_id, filtered_records, selected_candidate_id)
    comparison_options = selected_options[:8]
    return {
        "ranked_records": filtered_records,
        "family_summary_records": family_summary_records,
        "selected_candidate_id": selected_candidate_id,
        "selected_options": selected_options,
        "comparison_ids": comparison_ids,
        "comparison_options": comparison_options,
    }


def filter_catalog_records(
    records: list[dict[str, Any]],
    *,
    family: str | None = None,
    feasible_only: bool = False,
    max_cost: Any = None,
    min_quality: Any = None,
    min_flow: Any = None,
    min_resilience: Any = None,
    min_cleaning: Any = None,
    min_operability: Any = None,
    top_n_per_family: Any = None,
    fallback_filter: str | None = None,
    infeasibility_reason: str | None = None,
) -> list[dict[str, Any]]:
    filtered = list(records)
    if family and family != "ALL":
        filtered = [record for record in filtered if record["topology_family"] == family]
    if feasible_only:
        filtered = [record for record in filtered if bool(record["feasible"])]
    if max_cost not in (None, ""):
        filtered = [record for record in filtered if float(record["install_cost"]) <= float(max_cost)]
    if min_quality not in (None, ""):
        filtered = [record for record in filtered if float(record["quality_score_raw"]) >= float(min_quality)]
    if min_flow not in (None, ""):
        filtered = [record for record in filtered if float(record["flow_out_score"]) >= float(min_flow)]
    if min_resilience not in (None, ""):
        filtered = [record for record in filtered if float(record["resilience_score"]) >= float(min_resilience)]
    if min_cleaning not in (None, ""):
        filtered = [record for record in filtered if float(record["cleaning_score"]) >= float(min_cleaning)]
    if min_operability not in (None, ""):
        filtered = [record for record in filtered if float(record["operability_score"]) >= float(min_operability)]
    if fallback_filter == "NO_FALLBACK":
        filtered = [record for record in filtered if int(record["fallback_component_count"]) == 0]
    if fallback_filter == "WITH_FALLBACK":
        filtered = [record for record in filtered if int(record["fallback_component_count"]) > 0]
    if infeasibility_reason not in (None, "", "ALL"):
        filtered = [record for record in filtered if str(record.get("infeasibility_reason") or "NONE") == infeasibility_reason]
    if top_n_per_family not in (None, ""):
        limit = max(1, int(top_n_per_family))
        grouped: dict[str, list[dict[str, Any]]] = {}
        for record in filtered:
            grouped.setdefault(str(record["topology_family"]), []).append(record)
        filtered = [record for family_records in grouped.values() for record in family_records[:limit]]
    return filtered


def build_candidate_detail(
    result: dict[str, Any] | None,
    candidate_id: str | None,
    *,
    profile_id: str | None = None,
) -> dict[str, Any]:
    if not result or not candidate_id:
        return {
            "cytoscape_elements": [],
            "breakdown": {},
            "summary": {},
            "route_rows": [],
            "route_highlights": {},
            "critical_component_ids": [],
        }
    candidate = next(item for item in result["catalog"] if item["candidate_id"] == candidate_id)
    metrics = candidate["metrics"]
    route_rows = [
        {
            "route_id": route["route_id"],
            "feasible": route["feasible"],
            "reason": route["reason"],
            "required_flow_lpm": route["required_flow_lpm"],
            "delivered_flow_lpm": route["delivered_flow_lpm"],
            "route_effective_q_max_lpm": route.get("route_effective_q_max_lpm"),
            "hydraulic_slack_lpm": route.get("hydraulic_slack_lpm"),
            "total_loss_lpm_equiv": route.get("total_loss_lpm_equiv"),
            "bottleneck_component_id": route.get("bottleneck_component_id"),
            "critical_consequence": route.get("critical_consequence"),
            "path_link_ids": route.get("path_link_ids", []),
        }
        for route in metrics.get("route_metrics", [])
    ]
    return {
        "cytoscape_elements": candidate["render"]["cytoscape_elements"],
        "route_highlights": candidate["render"].get("route_highlights", {}),
        "critical_component_ids": _critical_component_ids(metrics.get("route_metrics", [])),
        "summary": {
            "candidate_id": candidate_id,
            "topology_family": candidate["topology_family"],
            "generation_source": candidate.get("generation_source"),
            "lineage_label": candidate.get("generation_metadata", {}).get("lineage_label"),
            "engine_used": metrics.get("engine_used"),
            "engine_mode": metrics.get("engine_mode"),
            "install_cost": metrics["install_cost"],
            "fallback_cost": metrics.get("fallback_cost"),
            "fallback_component_count": metrics.get("fallback_component_count"),
            "feasible": metrics.get("feasible"),
            "infeasibility_reason": metrics.get("infeasibility_reason"),
            "critical_routes": _critical_routes(metrics.get("route_metrics", [])),
            "score_final": _lookup_score(result, candidate_id, profile_id=profile_id),
        },
        "route_rows": route_rows,
        "breakdown": {
            "candidate_id": candidate_id,
            "topology_family": candidate["topology_family"],
            "generation_source": candidate.get("generation_source"),
            "generation_metadata": candidate.get("generation_metadata", {}),
            "engine_requested": metrics.get("engine_requested"),
            "engine_used": metrics.get("engine_used"),
            "engine_mode": metrics.get("engine_mode"),
            "install_cost": metrics["install_cost"],
            "quality_score_raw": metrics["quality_score_raw"],
            "resilience_score": metrics["resilience_score"],
            "operability_score": metrics["operability_score"],
            "cleaning_score": metrics["cleaning_score"],
            "fallback_component_count": metrics["fallback_component_count"],
            "infeasibility_reason": metrics.get("infeasibility_reason"),
            "constraint_failure_count": metrics.get("constraint_failure_count"),
            "constraint_failure_categories": metrics.get("constraint_failure_categories", {}),
            "constraint_failures": metrics.get("constraint_failures", []),
            "quality_score_breakdown": metrics.get("quality_score_breakdown", []),
            "quality_flags": metrics.get("quality_flags", []),
            "rules_triggered": metrics.get("rules_triggered", []),
            "selection_log": candidate["payload"].get("selection_log", []),
            "route_hydraulic_summary": route_rows,
        },
    }


def select_visible_candidate_id(
    result: dict[str, Any] | None,
    *,
    profile_id: str,
    filtered_records: list[dict[str, Any]],
    current_selected_id: str | None,
    weight_overrides: dict[str, Any] | None,
    filters_active: bool,
) -> str | None:
    if not result or not filtered_records:
        return None
    visible_ids = {record["candidate_id"] for record in filtered_records}
    if current_selected_id in visible_ids:
        return current_selected_id
    default_selected_id = result.get("selected_candidate_id")
    use_official_selected = (
        profile_id == result.get("default_profile_id")
        and not filters_active
        and not _weight_overrides_active(weight_overrides)
        and default_selected_id in visible_ids
    )
    if use_official_selected:
        return default_selected_id
    profile_selected_id, _ = resolve_selected_candidate(result, profile_id=profile_id, ranked_records=filtered_records)
    if profile_selected_id in visible_ids:
        return profile_selected_id
    return filtered_records[0]["candidate_id"]


def _lookup_candidates(result: dict[str, Any] | None, candidate_ids: list[str]) -> list[dict[str, Any]]:
    if not result:
        return []
    wanted = set(candidate_ids)
    return [item for item in result["catalog"] if item["candidate_id"] in wanted]


def build_official_candidate_summary(
    result: dict[str, Any] | None,
    *,
    profile_id: str,
    candidate_id: str | None,
) -> dict[str, Any]:
    if not result:
        return {}
    explanation = build_selected_candidate_explanation(result, profile_id=profile_id)
    official_candidate_id = candidate_id or explanation.get("candidate_id")
    if not official_candidate_id:
        return {}
    candidate = next(item for item in result["catalog"] if item["candidate_id"] == official_candidate_id)
    metrics = candidate["metrics"]
    winner = explanation.get("winner") or {}
    runner_up = explanation.get("runner_up") or {}
    return {
        "candidate_id": official_candidate_id,
        "active_profile_id": profile_id,
        "decision_status": explanation.get("decision_status"),
        "technical_tie": explanation.get("decision_status") == "technical_tie",
        "topology_family": candidate["topology_family"],
        "generation_source": candidate.get("generation_source"),
        "lineage_label": candidate.get("generation_metadata", {}).get("lineage_label"),
        "feasible": bool(metrics.get("feasible")),
        "infeasibility_reason": metrics.get("infeasibility_reason"),
        "install_cost": float(metrics.get("install_cost", 0.0)),
        "fallback_cost": float(metrics.get("fallback_cost", 0.0)),
        "total_cost": round(float(metrics.get("install_cost", 0.0)) + float(metrics.get("fallback_cost", 0.0)), 3),
        "score_final": _lookup_score(result, candidate_id, profile_id=profile_id),
        "engine_used": metrics.get("engine_used"),
        "engine_mode": metrics.get("engine_mode"),
        "fallback_component_count": int(metrics.get("fallback_component_count", 0)),
        "quality_flags": metrics.get("quality_flags", []),
        "critical_routes": _critical_routes(metrics.get("route_metrics", [])),
        "winner_reason_summary": explanation.get("winner_reason_summary"),
        "runner_up_candidate_id": runner_up.get("candidate_id"),
        "runner_up_topology_family": runner_up.get("topology_family"),
        "runner_up_score_final": runner_up.get("score_final"),
        "runner_up_total_cost": runner_up.get("total_cost"),
        "score_margin_winner": (explanation.get("score_margin") or {}).get("winner"),
        "score_margin_runner_up": (explanation.get("score_margin") or {}).get("runner_up"),
        "score_margin_delta": (explanation.get("score_margin") or {}).get("delta"),
        "winner_total_cost": winner.get("total_cost"),
        "decision_differences": explanation.get("decision_differences", {}),
        "key_factors": explanation.get("key_factors", []),
        "winner_penalties": explanation.get("winner_penalties", []),
    }


def build_comparison_records(
    result: dict[str, Any] | None,
    candidate_ids: list[str],
    *,
    profile_id: str,
    active_selected_id: str | None = None,
) -> list[dict[str, Any]]:
    if not result:
        return []
    explanation = build_selected_candidate_explanation(result, profile_id=profile_id)
    official_candidate_id = explanation.get("candidate_id")
    runner_up_id = (explanation.get("runner_up") or {}).get("candidate_id")
    records = []
    for item in _lookup_candidates(result, candidate_ids):
        metrics = item["metrics"]
        comparison_role = []
        if item["candidate_id"] == official_candidate_id:
            comparison_role.append("official")
        if item["candidate_id"] == runner_up_id:
            comparison_role.append("runner_up")
        if item["candidate_id"] == active_selected_id:
            comparison_role.append("selected")
        records.append(
            {
                "candidate_id": item["candidate_id"],
                "comparison_role": ",".join(comparison_role) or "candidate",
                "topology_family": item["topology_family"],
                "generation_source": item.get("generation_source"),
                "score_final": _lookup_score(result, item["candidate_id"], profile_id=profile_id),
                "feasible": bool(metrics.get("feasible")),
                "infeasibility_reason": metrics.get("infeasibility_reason"),
                "install_cost": float(metrics.get("install_cost", 0.0)),
                "fallback_cost": float(metrics.get("fallback_cost", 0.0)),
                "quality_score_raw": float(metrics.get("quality_score_raw", 0.0)),
                "flow_out_score": float(metrics.get("flow_out_score", 0.0)),
                "resilience_score": float(metrics.get("resilience_score", 0.0)),
                "cleaning_score": float(metrics.get("cleaning_score", 0.0)),
                "operability_score": float(metrics.get("operability_score", 0.0)),
                "fallback_component_count": int(metrics.get("fallback_component_count", 0)),
            }
        )
    return records


def _safe_run_pipeline(scenario_dir: str | Path) -> tuple[dict[str, Any] | None, str | None]:
    normalized_scenario_dir = _normalize_scenario_dir(scenario_dir)
    try:
        bundle = _require_canonical_scenario_bundle(
            load_scenario_bundle(normalized_scenario_dir),
            consumer="Decision Platform UI pipeline",
        )
        return run_decision_pipeline(
            normalized_scenario_dir,
            allow_diagnostic_python_emulation=_requires_diagnostic_python_emulation(bundle),
        ), None
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


def _resolve_initial_pipeline_state(
    scenario_dir: str | Path,
    *,
    bootstrap_pipeline: bool,
) -> tuple[dict[str, Any] | None, str | None]:
    if bootstrap_pipeline:
        return _safe_run_pipeline(scenario_dir)
    return None, "Initial pipeline bootstrap skipped for runs-focused UI stabilization."


def save_and_reopen_local_bundle(
    *,
    current_scenario_dir: str | Path,
    output_dir: str | Path,
    nodes_rows: list[dict[str, Any]] | None,
    components_rows: list[dict[str, Any]] | None,
    candidate_links_rows: list[dict[str, Any]] | None,
    edge_component_rules_rows: list[dict[str, Any]] | None,
    route_rows: list[dict[str, Any]] | None,
    layout_constraints_rows: list[dict[str, Any]] | None,
    topology_rules_text: str | None,
    scenario_settings_text: str | None,
) -> dict[str, Any]:
    normalized_source_dir = _normalize_scenario_dir(current_scenario_dir)
    normalized_output_dir = _normalize_scenario_dir(output_dir)
    _require_canonical_scenario_bundle(
        load_scenario_bundle(normalized_source_dir),
        consumer="Decision Platform UI save/reopen",
    )
    reloaded_bundle, exported_files = save_authored_scenario_bundle(
        normalized_source_dir,
        normalized_output_dir,
        nodes_rows=nodes_rows,
        components_rows=components_rows,
        candidate_links_rows=candidate_links_rows,
        edge_component_rules_rows=edge_component_rules_rows,
        route_rows=route_rows,
        layout_constraints_rows=layout_constraints_rows,
        topology_rules_text=topology_rules_text,
        scenario_settings_text=scenario_settings_text,
    )
    result, pipeline_error = _safe_run_pipeline(normalized_output_dir)
    canonical_scenario_root = str(reloaded_bundle.base_dir.resolve(strict=False))
    requested_output_dir = str(normalized_output_dir)
    return {
        "scenario_dir": str(normalized_output_dir),
        "bundle": reloaded_bundle,
        "result": result,
        "pipeline_error": pipeline_error,
        "bundle_io_summary": {
            "status": "saved_and_reopened",
            "source_scenario_dir": str(normalized_source_dir),
            "requested_scenario_dir": str(normalized_source_dir),
            "requested_output_dir": requested_output_dir,
            "saved_scenario_dir": str(normalized_output_dir),
            "canonical_scenario_root": canonical_scenario_root,
            "requested_dir_matches_bundle_root": requested_output_dir == canonical_scenario_root,
            "bundle_version": reloaded_bundle.bundle_version,
            "bundle_manifest": str(reloaded_bundle.bundle_manifest_path) if reloaded_bundle.bundle_manifest_path else None,
            "bundle_files": {
                logical_name: str(path.relative_to(reloaded_bundle.base_dir))
                for logical_name, path in reloaded_bundle.resolved_files.items()
            },
            "exported_files": {
                logical_name: str(path)
                for logical_name, path in exported_files.items()
            },
            "execution_scenario_provenance": result.get("scenario_provenance") if result else None,
            "pipeline_error": pipeline_error,
        },
    }


def apply_node_studio_edit(
    nodes_rows: list[dict[str, Any]],
    *,
    selected_node_id: str | None,
    node_id: str | None = None,
    label: str | None = None,
    node_type: str | None = None,
    x_m: Any = None,
    y_m: Any = None,
    allow_inbound: bool | None = None,
    allow_outbound: bool | None = None,
    candidate_links_rows: list[dict[str, Any]] | None = None,
    route_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    if selected_id is None:
        return nodes_rows, None
    selected_row = next(
        (dict(row) for row in nodes_rows if str(row.get("node_id", "")).strip() == selected_id),
        {},
    )
    target_node_id = str(node_id if node_id is not None else selected_row.get("node_id", selected_id)).strip()
    target_label = str(label if label is not None else selected_row.get("label", "")).strip()
    target_node_type = str(node_type if node_type is not None else selected_row.get("node_type", "")).strip()
    if not target_node_id:
        raise ValueError("nodes.csv cannot contain blank node_id values.")
    if not target_label:
        raise ValueError(f"nodes.csv requires a non-blank label for node '{selected_id}'.")
    if not target_node_type:
        raise ValueError(f"nodes.csv requires a non-blank node_type for node '{selected_id}'.")
    duplicate_node_ids = sorted(
        {
            str(row.get("node_id", "")).strip()
            for row in nodes_rows
            if str(row.get("node_id", "")).strip() and str(row.get("node_id", "")).strip() != selected_id
            and str(row.get("node_id", "")).strip() == target_node_id
        }
    )
    if duplicate_node_ids:
        raise ValueError(f"nodes.csv contains duplicated node_id values: {duplicate_node_ids}")
    if target_node_id != selected_id:
        link_refs = sorted(
            str(row.get("link_id", "")).strip()
            for row in (candidate_links_rows or [])
            if str(row.get("from_node", "")).strip() == selected_id or str(row.get("to_node", "")).strip() == selected_id
        )
        route_refs = sorted(
            str(row.get("route_id", "")).strip()
            for row in (route_rows or [])
            if str(row.get("source", "")).strip() == selected_id or str(row.get("sink", "")).strip() == selected_id
        )
        if link_refs or route_refs:
            raise ValueError(
                "Renaming node_id requires explicit reconciliation because candidate_links.csv/route_requirements.csv "
                f"still reference '{selected_id}': links={link_refs}, routes={route_refs}"
            )
    updated_rows: list[dict[str, Any]] = []
    next_selected_id = selected_id
    for row in nodes_rows:
        current_id = str(row.get("node_id", "")).strip()
        updated_row = dict(row)
        if current_id == selected_id:
            updated_row["node_id"] = target_node_id
            updated_row["label"] = target_label
            updated_row["node_type"] = target_node_type
            updated_row["x_m"] = _coerce_node_coordinate(x_m, updated_row.get("x_m"))
            updated_row["y_m"] = _coerce_node_coordinate(y_m, updated_row.get("y_m"))
            if allow_inbound is not None:
                updated_row["allow_inbound"] = bool(allow_inbound)
            if allow_outbound is not None:
                updated_row["allow_outbound"] = bool(allow_outbound)
            next_selected_id = str(updated_row["node_id"]).strip() or selected_id
        updated_rows.append(updated_row)
    return updated_rows, next_selected_id


def create_node_studio_node(
    nodes_rows: list[dict[str, Any]],
    *,
    selected_node_id: str | None,
) -> tuple[list[dict[str, Any]], str]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    selected_row = next(
        (dict(row) for row in nodes_rows if str(row.get("node_id", "")).strip() == selected_id),
        dict(nodes_rows[0]) if nodes_rows else {},
    )
    existing_ids = {
        str(row.get("node_id", "")).strip()
        for row in nodes_rows
        if str(row.get("node_id", "")).strip()
    }
    next_node_id = _next_structural_identifier(existing_ids, "NEW_NODE")
    base_x = _coerce_node_coordinate(selected_row.get("x_m"), 0.0) if selected_row else 0.0
    base_y = _coerce_node_coordinate(selected_row.get("y_m"), 0.0) if selected_row else 0.0
    new_row = {
        **selected_row,
        "node_id": next_node_id,
        "node_type": "junction",
        "label": f"Novo nó {next_node_id}",
        "x_m": round(base_x + 0.03, 4),
        "y_m": round(base_y + 0.03, 4),
        "allow_inbound": True,
        "allow_outbound": True,
        "requires_mixing_service": False,
        "zone": "internal",
        "is_candidate_hub": False,
        "notes": "Criado no studio",
    }
    return [*nodes_rows, new_row], next_node_id


def create_business_node_studio_node(
    nodes_rows: list[dict[str, Any]],
    *,
    selected_node_id: str | None,
    preset_key: str,
    x_m: float | None = None,
    y_m: float | None = None,
) -> tuple[list[dict[str, Any]], str]:
    preset = BUSINESS_NODE_PRESETS.get(str(preset_key).strip())
    if preset is None:
        raise ValueError(f"Unknown Studio business preset: {preset_key}")
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    selected_row = next(
        (dict(row) for row in nodes_rows if str(row.get("node_id", "")).strip() == selected_id),
        dict(nodes_rows[0]) if nodes_rows else {},
    )
    existing_ids = {
        str(row.get("node_id", "")).strip()
        for row in nodes_rows
        if str(row.get("node_id", "")).strip()
    }
    next_node_id = _next_structural_identifier(existing_ids, str(preset.get("node_id_prefix") or "NODE"))
    base_x = _coerce_node_coordinate(selected_row.get("x_m"), 0.15) if selected_row else 0.15
    base_y = _coerce_node_coordinate(selected_row.get("y_m"), 0.18) if selected_row else 0.18
    visible_same_type_count = sum(
        1
        for row in _visible_studio_nodes(nodes_rows)
        if str(row.get("node_type", "")).strip() == str(preset.get("node_type", "")).strip()
    )
    label = str(preset.get("default_label") or "Nova entidade").strip()
    if visible_same_type_count > 0:
        label = f"{label} {visible_same_type_count + 1}"
    new_row = {
        **selected_row,
        "node_id": next_node_id,
        "node_type": str(preset["node_type"]),
        "label": label,
        "x_m": round(float(x_m) if x_m is not None else base_x + 0.05, 4),
        "y_m": round(float(y_m) if y_m is not None else base_y + 0.04, 4),
        "allow_inbound": bool(preset["allow_inbound"]),
        "allow_outbound": bool(preset["allow_outbound"]),
        "requires_mixing_service": bool(preset["requires_mixing_service"]),
        "zone": str(preset["zone"]),
        "is_candidate_hub": False,
        "notes": "Criado pela paleta principal do Studio",
    }
    return [*nodes_rows, new_row], next_node_id


def duplicate_node_studio_selection(
    nodes_rows: list[dict[str, Any]],
    *,
    selected_node_id: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    if selected_id is None:
        return nodes_rows, None
    source_row = next(
        (dict(row) for row in nodes_rows if str(row.get("node_id", "")).strip() == selected_id),
        None,
    )
    if source_row is None:
        return nodes_rows, None
    existing_ids = {
        str(row.get("node_id", "")).strip()
        for row in nodes_rows
        if str(row.get("node_id", "")).strip()
    }
    next_node_id = _next_structural_identifier(existing_ids, f"{selected_id}_copy")
    duplicated_row = {
        **source_row,
        "node_id": next_node_id,
        "label": f"{str(source_row.get('label', '')).strip()} copia",
        "x_m": round(_coerce_node_coordinate(source_row.get("x_m"), 0.0) + 0.03, 4),
        "y_m": round(_coerce_node_coordinate(source_row.get("y_m"), 0.0) + 0.03, 4),
        "notes": f"{str(source_row.get('notes', '')).strip()} | duplicado no studio".strip(" |"),
    }
    return [*nodes_rows, duplicated_row], next_node_id


def apply_studio_context_menu_action(
    *,
    context_menu_data: dict[str, Any] | None,
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    selected_node_id: str | None,
    selected_link_id: str | None,
    route_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str | None, str | None, str, bool]:
    payload = context_menu_data or {}
    menu_item_id = str(payload.get("menuItemId") or "").strip()
    element_id = str(payload.get("elementId") or "").strip()
    click_x = payload.get("x")
    click_y = payload.get("y")
    if not menu_item_id:
        return nodes_rows, candidate_links_rows, route_rows, selected_node_id, selected_link_id, "", False
    next_node_selection = selected_node_id
    next_edge_selection = selected_link_id
    if menu_item_id.startswith("add-") and menu_item_id.endswith("-node"):
        preset_key = menu_item_id.removeprefix("add-").removesuffix("-node")
        x_m = round(float(click_x) / 1000.0, 4) if click_x is not None else None
        y_m = round(float(click_y) / 600.0, 4) if click_y is not None else None
        updated_nodes, next_node_selection = create_business_node_studio_node(
            nodes_rows,
            selected_node_id=element_id or selected_node_id,
            preset_key=preset_key,
            x_m=x_m,
            y_m=y_m,
        )
        return (
            updated_nodes,
            candidate_links_rows,
            route_rows,
            next_node_selection,
            next_edge_selection,
            "Entidade de negócio adicionada pelo menu contextual.",
            False,
        )
    if menu_item_id == "duplicate-node":
        updated_nodes, next_node_selection = duplicate_node_studio_selection(
            nodes_rows,
            selected_node_id=element_id or selected_node_id,
        )
        return (
            updated_nodes,
            candidate_links_rows,
            route_rows,
            next_node_selection,
            next_edge_selection,
            "Entidade duplicada pelo menu contextual.",
            False,
        )
    if menu_item_id == "remove-node":
        try:
            updated_nodes, next_node_selection = delete_node_studio_selection(
                nodes_rows,
                selected_node_id=element_id or selected_node_id,
                candidate_links_rows=candidate_links_rows,
                route_rows=route_rows,
            )
        except ValueError as exc:
            return nodes_rows, candidate_links_rows, route_rows, selected_node_id, selected_link_id, str(exc), False
        return (
            updated_nodes,
            candidate_links_rows,
            route_rows,
            next_node_selection,
            next_edge_selection,
            "Entidade removida pelo menu contextual.",
            False,
        )
    if menu_item_id == "remove-edge":
        updated_links, next_edge_selection = delete_edge_studio_selection(
            candidate_links_rows,
            selected_link_id=element_id or selected_link_id,
        )
        return (
            nodes_rows,
            updated_links,
            route_rows,
            next_node_selection,
            next_edge_selection,
            "Conexão removida pelo menu contextual.",
            False,
        )
    if menu_item_id == "create-route-from-edge":
        try:
            updated_routes, created_route_id = create_route_from_edge_studio_selection(
                route_rows,
                selected_link_id=element_id or selected_link_id,
                candidate_links_rows=candidate_links_rows,
            )
        except ValueError as exc:
            return nodes_rows, candidate_links_rows, route_rows, selected_node_id, selected_link_id, str(exc), False
        return (
            nodes_rows,
            candidate_links_rows,
            updated_routes,
            next_node_selection,
            element_id or selected_link_id,
            f"Rota {created_route_id} criada pelo menu contextual deste trecho.",
            False,
        )
    if menu_item_id in {"mark-route-mandatory", "mark-route-desirable", "mark-route-optional"}:
        intent = {
            "mark-route-mandatory": "mandatory",
            "mark-route-desirable": "desirable",
            "mark-route-optional": "optional",
        }[menu_item_id]
        try:
            updated_routes, selected_route_id = apply_route_intent_from_edge_context(
                route_rows,
                selected_link_id=element_id or selected_link_id,
                candidate_links_rows=candidate_links_rows,
                intent=intent,
            )
        except ValueError as exc:
            return nodes_rows, candidate_links_rows, route_rows, selected_node_id, selected_link_id, str(exc), False
        return (
            nodes_rows,
            candidate_links_rows,
            updated_routes,
            next_node_selection,
            element_id or selected_link_id,
            f"Rota {selected_route_id} marcada como {_route_intent_label(intent).lower()} pelo menu contextual.",
            False,
        )
    if menu_item_id == "reverse-edge":
        try:
            updated_links, next_edge_selection, status_message = _reverse_edge_with_feedback(
                candidate_links_rows,
                selected_link_id=element_id or selected_link_id,
                nodes_rows=nodes_rows,
                route_rows=route_rows,
                message_prefix="Conexão invertida pelo menu contextual.",
            )
        except ValueError as exc:
            return nodes_rows, candidate_links_rows, route_rows, selected_node_id, selected_link_id, str(exc), False
        return (
            nodes_rows,
            updated_links,
            route_rows,
            next_node_selection,
            next_edge_selection,
            status_message,
            False,
        )
    if menu_item_id == "open-workbench":
        if element_id:
            if any(str(row.get("node_id", "")).strip() == element_id for row in nodes_rows):
                next_node_selection = element_id
            if any(str(row.get("link_id", "")).strip() == element_id for row in candidate_links_rows):
                next_edge_selection = element_id
        return nodes_rows, candidate_links_rows, route_rows, next_node_selection, next_edge_selection, "", True
    return nodes_rows, candidate_links_rows, route_rows, next_node_selection, next_edge_selection, "", False


def delete_node_studio_selection(
    nodes_rows: list[dict[str, Any]],
    *,
    selected_node_id: str | None,
    candidate_links_rows: list[dict[str, Any]] | None = None,
    route_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    if selected_id is None:
        return nodes_rows, None
    link_refs = sorted(
        str(row.get("link_id", "")).strip()
        for row in (candidate_links_rows or [])
        if str(row.get("from_node", "")).strip() == selected_id or str(row.get("to_node", "")).strip() == selected_id
    )
    route_refs = sorted(
        str(row.get("route_id", "")).strip()
        for row in (route_rows or [])
        if str(row.get("source", "")).strip() == selected_id or str(row.get("sink", "")).strip() == selected_id
    )
    if link_refs or route_refs:
        raise ValueError(
            "Deleting node_id requires explicit reconciliation because candidate_links.csv/route_requirements.csv "
            f"still reference '{selected_id}': links={link_refs}, routes={route_refs}"
        )
    remaining_rows = [dict(row) for row in nodes_rows if str(row.get("node_id", "")).strip() != selected_id]
    next_selected_id = _default_node_studio_selection(remaining_rows)
    return remaining_rows, next_selected_id


def move_node_studio_selection(
    nodes_rows: list[dict[str, Any]],
    *,
    selected_node_id: str | None,
    direction: str | None,
    step: Any,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    if selected_id is None:
        return nodes_rows, None
    step_value = abs(_coerce_node_coordinate(step, 0.02))
    delta_x = 0.0
    delta_y = 0.0
    if direction == "left":
        delta_x = -step_value
    elif direction == "right":
        delta_x = step_value
    elif direction == "up":
        delta_y = -step_value
    elif direction == "down":
        delta_y = step_value
    updated_rows: list[dict[str, Any]] = []
    for row in nodes_rows:
        updated_row = dict(row)
        if str(row.get("node_id", "")).strip() == selected_id:
            updated_row["x_m"] = round(_coerce_node_coordinate(row.get("x_m"), 0.0) + delta_x, 4)
            updated_row["y_m"] = round(_coerce_node_coordinate(row.get("y_m"), 0.0) + delta_y, 4)
        updated_rows.append(updated_row)
    return updated_rows, selected_id


def apply_edge_studio_edit(
    candidate_links_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
    link_id: str | None = None,
    from_node: str | None = None,
    to_node: str | None = None,
    archetype: str | None = None,
    length_m: Any = None,
    bidirectional: bool | None = None,
    family_hint: str | None = None,
    nodes_rows: list[dict[str, Any]] | None = None,
    edge_component_rules_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    if selected_id is None:
        return candidate_links_rows, None
    selected_row = next(
        (dict(row) for row in candidate_links_rows if str(row.get("link_id", "")).strip() == selected_id),
        {},
    )
    target_link_id = str(link_id if link_id is not None else selected_row.get("link_id", selected_id)).strip()
    if not target_link_id:
        raise ValueError("candidate_links.csv contains blank link_id values.")
    duplicate_link_ids = sorted(
        {
            str(row.get("link_id", "")).strip()
            for row in candidate_links_rows
            if str(row.get("link_id", "")).strip() and str(row.get("link_id", "")).strip() != selected_id
            and str(row.get("link_id", "")).strip() == target_link_id
        }
    )
    if duplicate_link_ids:
        raise ValueError(f"candidate_links.csv contains duplicated link_id values: {duplicate_link_ids}")
    node_ids = {
        str(row.get("node_id", "")).strip()
        for row in (nodes_rows or [])
        if str(row.get("node_id", "")).strip()
    }
    target_from_node = str(from_node if from_node is not None else selected_row.get("from_node", "")).strip()
    target_to_node = str(to_node if to_node is not None else selected_row.get("to_node", "")).strip()
    if not target_from_node or not target_to_node:
        raise ValueError(
            "candidate_links.csv requires non-blank from_node and to_node values for "
            f"edge '{target_link_id}'."
        )
    unknown_nodes = sorted({node_id for node_id in (target_from_node, target_to_node) if node_id and node_id not in node_ids})
    if unknown_nodes:
        raise ValueError(f"candidate_links.csv references unknown nodes: {unknown_nodes}")
    if target_from_node == target_to_node:
        raise ValueError(
            "candidate_links.csv contains self-loop edges with from_node == to_node: "
            f"['{target_link_id}']"
        )
    target_archetype = str(archetype if archetype is not None else selected_row.get("archetype", "")).strip()
    if not target_archetype:
        raise ValueError(f"candidate_links.csv requires a non-blank archetype for edge '{target_link_id}'.")
    known_archetypes = {
        str(row.get("archetype", "")).strip()
        for row in (edge_component_rules_rows or [])
        if str(row.get("archetype", "")).strip()
    }
    if target_archetype not in known_archetypes:
        raise ValueError(
            "candidate_links.csv references archetype without matching edge_component_rules.csv rule: "
            f"[{{'link_id': '{target_link_id}', 'archetype': '{target_archetype}'}}]"
        )
    updated_rows: list[dict[str, Any]] = []
    next_selected_id = selected_id
    for row in candidate_links_rows:
        current_id = str(row.get("link_id", "")).strip()
        updated_row = dict(row)
        if current_id == selected_id:
            updated_row["link_id"] = target_link_id
            updated_row["from_node"] = target_from_node
            updated_row["to_node"] = target_to_node
            updated_row["archetype"] = target_archetype
            updated_row["length_m"] = round(_coerce_edge_length(length_m, row.get("length_m")), 4)
            if bidirectional is not None:
                updated_row["bidirectional"] = bool(bidirectional)
            updated_row["family_hint"] = str(
                family_hint if family_hint is not None else selected_row.get("family_hint", "")
            ).strip()
            next_selected_id = target_link_id
        updated_rows.append(updated_row)
    return updated_rows, next_selected_id


def create_edge_studio_link(
    candidate_links_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
    from_node: str | None = None,
    to_node: str | None = None,
    archetype: str | None = None,
    length_m: Any = None,
    bidirectional: bool | None = None,
    family_hint: str | None = None,
    nodes_rows: list[dict[str, Any]] | None = None,
    edge_component_rules_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    node_ids = [
        str(row.get("node_id", "")).strip()
        for row in (nodes_rows or [])
        if str(row.get("node_id", "")).strip()
    ]
    if len(node_ids) < 2:
        raise ValueError("candidate_links.csv requires at least two nodes to create an edge.")
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    selected_row = next(
        (dict(row) for row in candidate_links_rows if str(row.get("link_id", "")).strip() == selected_id),
        dict(candidate_links_rows[0]) if candidate_links_rows else {},
    )
    existing_ids = {
        str(row.get("link_id", "")).strip()
        for row in candidate_links_rows
        if str(row.get("link_id", "")).strip()
    }
    next_link_id = _next_structural_identifier(
        existing_ids,
        f"{selected_id}_copy" if selected_id else "NEW_LINK",
    )
    default_from = str(from_node if from_node is not None else selected_row.get("from_node", node_ids[0])).strip()
    default_to = str(to_node if to_node is not None else selected_row.get("to_node", node_ids[1])).strip()
    if default_from == default_to:
        default_to = next((node_id for node_id in node_ids if node_id != default_from), default_to)
    default_archetype = str(
        archetype if archetype is not None else selected_row.get("archetype", _default_edge_archetype(edge_component_rules_rows or []))
    ).strip()
    new_row = {
        **selected_row,
        "link_id": next_link_id,
        "from_node": default_from,
        "to_node": default_to,
        "archetype": default_archetype,
        "length_m": round(_coerce_edge_length(length_m, selected_row.get("length_m", 0.1)), 4),
        "bidirectional": bool(
            bidirectional if bidirectional is not None else bool(selected_row.get("bidirectional"))
        ),
        "family_hint": str(family_hint if family_hint is not None else selected_row.get("family_hint", "")).strip(),
        "group_id": str(selected_row.get("group_id", "")).strip() or next_link_id.lower(),
        "notes": str(selected_row.get("notes", "")).strip() or "Criada no studio",
    }
    updated_rows = [*candidate_links_rows, new_row]
    return apply_edge_studio_edit(
        updated_rows,
        selected_link_id=next_link_id,
        link_id=next_link_id,
        from_node=new_row["from_node"],
        to_node=new_row["to_node"],
        archetype=new_row["archetype"],
        length_m=new_row["length_m"],
        bidirectional=bool(new_row["bidirectional"]),
        family_hint=new_row["family_hint"],
        nodes_rows=nodes_rows or [],
        edge_component_rules_rows=edge_component_rules_rows or [],
    )


def delete_edge_studio_selection(
    candidate_links_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    if selected_id is None:
        return candidate_links_rows, None
    remaining_rows = [dict(row) for row in candidate_links_rows if str(row.get("link_id", "")).strip() != selected_id]
    next_selected_id = _default_edge_studio_selection(remaining_rows)
    return remaining_rows, next_selected_id


def reverse_edge_studio_selection(
    candidate_links_rows: list[dict[str, Any]],
    *,
    selected_link_id: str | None,
    nodes_rows: list[dict[str, Any]] | None = None,
    edge_component_rules_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    if selected_id is None:
        return candidate_links_rows, None
    selected_row = next(
        (dict(row) for row in candidate_links_rows if str(row.get("link_id", "")).strip() == selected_id),
        None,
    )
    if selected_row is None:
        return candidate_links_rows, None
    target_from_node = str(selected_row.get("to_node") or "").strip()
    target_to_node = str(selected_row.get("from_node") or "").strip()
    if not target_from_node or not target_to_node:
        raise ValueError(
            "candidate_links.csv requires non-blank from_node and to_node values for "
            f"edge '{selected_id}'."
        )
    if target_from_node == target_to_node:
        raise ValueError(
            "candidate_links.csv contains self-loop edges with from_node == to_node: "
            f"['{selected_id}']"
        )
    node_ids = {
        str(row.get("node_id", "")).strip()
        for row in (nodes_rows or [])
        if str(row.get("node_id", "")).strip()
    }
    unknown_nodes = sorted({node_id for node_id in (target_from_node, target_to_node) if node_ids and node_id not in node_ids})
    if unknown_nodes:
        raise ValueError(f"candidate_links.csv references unknown nodes: {unknown_nodes}")
    updated_rows: list[dict[str, Any]] = []
    for row in candidate_links_rows:
        updated_row = dict(row)
        if str(row.get("link_id", "")).strip() == selected_id:
            updated_row["from_node"] = target_from_node
            updated_row["to_node"] = target_to_node
        updated_rows.append(updated_row)
    return updated_rows, selected_id


def build_node_studio_elements(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    node_ids = {str(row.get("node_id", "")).strip() for row in nodes_rows if str(row.get("node_id", "")).strip()}
    elements: list[dict[str, Any]] = []
    for row in nodes_rows:
        node_id = str(row.get("node_id", "")).strip()
        if not node_id:
            continue
        elements.append(
            {
                "data": {
                    "id": node_id,
                    "label": f"{node_id}: {str(row.get('label', '')).strip()}",
                    "node_type": str(row.get("node_type", "")).strip(),
                    "allow_inbound": bool(row.get("allow_inbound")),
                    "allow_outbound": bool(row.get("allow_outbound")),
                },
                "position": _node_studio_position(row),
                "classes": _node_studio_classes(row),
            }
        )
    for row in candidate_links_rows:
        source = str(row.get("from_node", "")).strip()
        target = str(row.get("to_node", "")).strip()
        link_id = str(row.get("link_id", "")).strip()
        if not source or not target or not link_id:
            continue
        if source not in node_ids or target not in node_ids:
            continue
        elements.append(
            {
                "data": {
                    "id": link_id,
                    "link_id": link_id,
                    "source": source,
                    "target": target,
                    "label": f"{link_id}: {str(row.get('archetype', '')).strip()}",
                    "from_node": source,
                    "to_node": target,
                    "archetype": str(row.get("archetype", "")).strip(),
                    "length_m": _coerce_edge_length(row.get("length_m"), 0.0),
                    "bidirectional": bool(row.get("bidirectional")),
                    "family_hint": str(row.get("family_hint", "")).strip(),
                }
            }
        )
    return elements


def build_primary_node_studio_elements(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    route_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    visible_nodes = _visible_studio_nodes(nodes_rows)
    node_lookup = {
        str(row.get("node_id", "")).strip(): dict(row)
        for row in visible_nodes
        if str(row.get("node_id", "")).strip()
    }
    projected_routes = _primary_route_projection_rows(nodes_rows, route_rows)
    elements: list[dict[str, Any]] = []
    for row in visible_nodes:
        node_id = str(row.get("node_id", "")).strip()
        if not node_id:
            continue
        elements.append(
            {
                "data": {
                    "id": node_id,
                    "node_id": node_id,
                    "label": _studio_node_business_label(row),
                    "business_role": _studio_node_role_label(row),
                },
                "position": _node_studio_position(row),
                "classes": _node_studio_classes(row),
            }
        )
    if projected_routes:
        for route in projected_routes:
            elements.append(
                {
                    "data": {
                        "id": str(route["projection_id"]),
                        "route_id": str(route["route_id"]),
                        "source": str(route["source"]),
                        "target": str(route["target"]),
                        "label": str(route["label"]),
                        "route_group": str(route["route_group"]),
                        "intent": str(route["intent"]),
                        "mandatory": bool(route["mandatory"]),
                        "measurement_required": bool(route["measurement_required"]),
                        "q_min_delivered_lpm": float(route["q_min_delivered_lpm"]),
                        "notes": str(route["notes"]),
                    },
                    "classes": " ".join(
                        item
                        for item in [
                            "route-projection",
                            str(route["route_group"]),
                            str(route["intent"]),
                            "measurement-required" if bool(route["measurement_required"]) else "",
                        ]
                        if item
                    ),
                }
            )
        return elements
    visible_edges = _visible_studio_edges(nodes_rows, candidate_links_rows)
    for row in visible_edges:
        source = str(row.get("from_node", "")).strip()
        target = str(row.get("to_node", "")).strip()
        link_id = str(row.get("link_id", "")).strip()
        if not source or not target or not link_id:
            continue
        elements.append(
            {
                "data": {
                    "id": link_id,
                    "link_id": link_id,
                    "source": source,
                    "target": target,
                    "label": _studio_edge_business_label(row, node_lookup),
                    "from_node": source,
                    "to_node": target,
                    "length_m": _coerce_edge_length(row.get("length_m"), 0.0),
                    "bidirectional": bool(row.get("bidirectional")),
                    "family_hint": str(row.get("family_hint", "")).strip(),
                    "notes": str(row.get("notes", "")).strip(),
                }
            }
        )
    return elements


def _normalize_scenario_dir(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _require_canonical_scenario_bundle(bundle: Any, *, consumer: str) -> Any:
    if bundle.bundle_version == SCENARIO_BUNDLE_VERSION and bundle.bundle_manifest_path is not None:
        return bundle
    raise OfficialRuntimeConfigError(
        f"{consumer} requires a canonical scenario bundle with '{BUNDLE_MANIFEST_FILENAME}' "
        f"and bundle_version '{SCENARIO_BUNDLE_VERSION}'. Legacy directory layouts are only "
        "supported for explicit low-level migration or test helpers."
    )


def _build_execution_summary(result: dict[str, Any] | None, error: str | None) -> str:
    return json.dumps(
        {
            "candidate_count": len(result["catalog"]) if result else 0,
            "feasible_count": sum(1 for item in result["catalog"] if item["metrics"]["feasible"]) if result else 0,
            "default_profile_id": result.get("default_profile_id") if result else None,
            "selected_candidate_id": result.get("selected_candidate_id") if result else None,
            "scenario_bundle_root": result.get("scenario_bundle_root") if result else None,
            "scenario_bundle_version": result.get("scenario_bundle_version") if result else None,
            "scenario_bundle_manifest": result.get("scenario_bundle_manifest") if result else None,
            "scenario_bundle_files": result.get("scenario_bundle_files") if result else None,
            "scenario_provenance": result.get("scenario_provenance") if result else None,
            "error": error,
        },
        indent=2,
        ensure_ascii=False,
    )


def _default_node_studio_selection(
    nodes_rows: list[dict[str, Any]],
    *,
    preferred_node_id: str | None = None,
) -> str | None:
    preferred = str(preferred_node_id or "").strip()
    if preferred and any(str(row.get("node_id", "")).strip() == preferred for row in nodes_rows):
        return preferred
    for row in nodes_rows:
        node_id = str(row.get("node_id", "")).strip()
        if node_id:
            return node_id
    return None


def _default_primary_node_studio_selection(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    *,
    preferred_node_id: str | None = None,
) -> str | None:
    visible_node_ids = _visible_studio_node_ids(nodes_rows)
    preferred = str(preferred_node_id or "").strip()
    if preferred and preferred in visible_node_ids:
        return preferred
    for row in _visible_studio_nodes(nodes_rows):
        node_id = str(row.get("node_id", "")).strip()
        if node_id:
            return node_id
    return _default_node_studio_selection(nodes_rows, preferred_node_id=preferred_node_id)


def _default_edge_studio_selection(
    candidate_links_rows: list[dict[str, Any]],
    *,
    preferred_link_id: str | None = None,
) -> str | None:
    preferred = str(preferred_link_id or "").strip()
    if preferred and any(str(row.get("link_id", "")).strip() == preferred for row in candidate_links_rows):
        return preferred
    for row in candidate_links_rows:
        link_id = str(row.get("link_id", "")).strip()
        if link_id:
            return link_id
    return None


def _default_primary_edge_studio_selection(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    *,
    preferred_link_id: str | None = None,
) -> str | None:
    visible_link_ids = {
        str(row.get("link_id", "")).strip()
        for row in _visible_studio_edges(nodes_rows, candidate_links_rows)
        if str(row.get("link_id", "")).strip()
    }
    preferred = str(preferred_link_id or "").strip()
    if preferred and preferred in visible_link_ids:
        return preferred
    for row in _visible_studio_edges(nodes_rows, candidate_links_rows):
        link_id = str(row.get("link_id", "")).strip()
        if link_id:
            return link_id
    return None


def _node_studio_form_values(nodes_rows: list[dict[str, Any]], selected_node_id: str | None) -> dict[str, Any]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    row = next(
        (dict(item) for item in nodes_rows if str(item.get("node_id", "")).strip() == selected_id),
        None,
    )
    if row is None:
        return {
            "node_id": "",
            "label": "",
            "node_type": "",
            "x_m": None,
            "y_m": None,
            "allow_inbound": [],
            "allow_outbound": [],
        }
    return {
        "node_id": str(row.get("node_id", "")).strip(),
        "label": str(row.get("label", "")).strip(),
        "node_type": str(row.get("node_type", "")).strip(),
        "x_m": float(row.get("x_m", 0.0)),
        "y_m": float(row.get("y_m", 0.0)),
        "allow_inbound": ["allow_inbound"] if bool(row.get("allow_inbound")) else [],
        "allow_outbound": ["allow_outbound"] if bool(row.get("allow_outbound")) else [],
    }


def _edge_studio_form_values(
    candidate_links_rows: list[dict[str, Any]],
    selected_link_id: str | None,
) -> dict[str, Any]:
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    row = next(
        (dict(item) for item in candidate_links_rows if str(item.get("link_id", "")).strip() == selected_id),
        None,
    )
    if row is None:
        return {
            "link_id": "",
            "from_node": "",
            "to_node": "",
            "archetype": "",
            "length_m": None,
            "bidirectional": [],
            "family_hint": "",
        }
    return {
        "link_id": str(row.get("link_id", "")).strip(),
        "from_node": str(row.get("from_node", "")).strip(),
        "to_node": str(row.get("to_node", "")).strip(),
        "archetype": str(row.get("archetype", "")).strip(),
        "length_m": float(row.get("length_m", 0.0)),
        "bidirectional": ["bidirectional"] if bool(row.get("bidirectional")) else [],
        "family_hint": str(row.get("family_hint", "")).strip(),
    }


def _build_node_studio_summary(nodes_rows: list[dict[str, Any]], selected_node_id: str | None) -> dict[str, Any]:
    selected_id = _default_node_studio_selection(nodes_rows, preferred_node_id=selected_node_id)
    selected_row = next(
        (dict(item) for item in nodes_rows if str(item.get("node_id", "")).strip() == selected_id),
        None,
    )
    return {
        "node_count": len(nodes_rows),
        "business_node_count": len(_visible_studio_nodes(nodes_rows)),
        "hidden_internal_node_count": max(len(nodes_rows) - len(_visible_studio_nodes(nodes_rows)), 0),
        "selected_node_id": selected_id,
        "selected_node": selected_row,
        "business_label": _studio_node_business_label(selected_row),
        "role_label": _studio_node_role_label(selected_row),
        "is_internal": _is_internal_studio_node(selected_row),
    }


def _build_edge_studio_summary(
    nodes_rows: list[dict[str, Any]],
    candidate_links_rows: list[dict[str, Any]],
    selected_link_id: str | None,
) -> dict[str, Any]:
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    selected_row = next(
        (dict(item) for item in candidate_links_rows if str(item.get("link_id", "")).strip() == selected_id),
        None,
    )
    node_lookup = {
        str(row.get("node_id", "")).strip(): dict(row)
        for row in nodes_rows
        if str(row.get("node_id", "")).strip()
    }
    return {
        "edge_count": len(candidate_links_rows),
        "business_edge_count": len(_visible_studio_edges(nodes_rows, candidate_links_rows)),
        "selected_link_id": selected_id,
        "selected_edge": selected_row,
        "business_label": _studio_edge_business_label(selected_row, node_lookup),
        "role_label": _studio_edge_role_label(selected_row),
        "from_label": _studio_node_business_label(node_lookup.get(str((selected_row or {}).get("from_node", "")).strip())),
        "to_label": _studio_node_business_label(node_lookup.get(str((selected_row or {}).get("to_node", "")).strip())),
        "is_internal": any(
            _is_internal_studio_node(node_lookup.get(node_id))
            for node_id in [str((selected_row or {}).get("from_node", "")).strip(), str((selected_row or {}).get("to_node", "")).strip()]
            if node_id
        ),
    }


def _next_structural_identifier(existing_ids: set[str], base_id: str) -> str:
    normalized_base = str(base_id).strip() or "NEW_ITEM"
    if normalized_base not in existing_ids:
        return normalized_base
    suffix = 1
    while f"{normalized_base}_{suffix}" in existing_ids:
        suffix += 1
    return f"{normalized_base}_{suffix}"


def _default_edge_archetype(edge_component_rules_rows: list[dict[str, Any]]) -> str:
    for row in edge_component_rules_rows:
        archetype = str(row.get("archetype", "")).strip()
        if archetype:
            return archetype
    return ""


def _node_studio_position(row: dict[str, Any]) -> dict[str, float]:
    return {
        "x": round(_coerce_node_coordinate(row.get("x_m"), 0.0) * 1000.0, 2),
        "y": round(_coerce_node_coordinate(row.get("y_m"), 0.0) * 600.0, 2),
    }


def _node_studio_classes(row: dict[str, Any]) -> str:
    classes: list[str] = [str(row.get("node_type", "")).strip() or "generic"]
    if bool(row.get("allow_inbound")):
        classes.append("allow-inbound")
    else:
        classes.append("block-inbound")
    if bool(row.get("allow_outbound")):
        classes.append("allow-outbound")
    else:
        classes.append("block-outbound")
    if bool(row.get("is_candidate_hub")):
        classes.append("candidate-hub")
    return " ".join(classes)


def _build_node_studio_stylesheet(
    selected_node_id: str | None,
    selected_edge_id: str | None = None,
) -> list[dict[str, Any]]:
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "width": 34,
                "height": 34,
                "background-color": "#0f766e",
                "color": "#0f172a",
                "font-size": 11,
                "text-wrap": "wrap",
                "text-max-width": 92,
                "border-width": 2,
                "border-color": "#0f172a",
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "line-color": "#94a3b8",
                "target-arrow-shape": "triangle",
                "target-arrow-color": "#94a3b8",
                "width": 2,
                "font-size": 9,
                "label": "data(label)",
            },
        },
        {"selector": ".route-projection", "style": {"width": 4, "line-color": "#0f766e", "target-arrow-color": "#0f766e"}},
        {"selector": ".mandatory", "style": {"width": 5, "line-color": "#0f766e", "target-arrow-color": "#0f766e"}},
        {"selector": ".desirable", "style": {"line-style": "dashed", "line-color": "#d97706", "target-arrow-color": "#d97706", "opacity": 0.92}},
        {"selector": ".optional", "style": {"line-style": "dotted", "line-color": "#64748b", "target-arrow-color": "#64748b", "opacity": 0.82}},
        {"selector": ".service", "style": {"line-style": "dotted", "line-color": "#475569", "target-arrow-color": "#475569"}},
        {"selector": ".candidate-hub", "style": {"background-color": "#f59e0b", "shape": "diamond"}},
        {"selector": ".block-inbound", "style": {"border-color": "#dc2626"}},
        {"selector": ".block-outbound", "style": {"border-style": "dashed"}},
    ]
    if selected_node_id:
        stylesheet.append(
            {
                "selector": f'node[id = "{selected_node_id}"]',
                "style": {
                    "border-width": 5,
                    "border-color": "#1d4ed8",
                    "background-color": "#38bdf8",
                },
            }
        )
    if selected_edge_id:
        stylesheet.append(
            {
                "selector": f'edge[id = "{selected_edge_id}"]',
                "style": {
                    "line-color": "#ea580c",
                    "target-arrow-color": "#ea580c",
                    "width": 5,
                },
            }
        )
    return stylesheet


def _coerce_node_coordinate(value: Any, default: Any) -> float:
    candidate = default if value in (None, "") else value
    return float(candidate)


def _coerce_edge_length(value: Any, default: Any) -> float:
    candidate = default if value in (None, "") else value
    return float(candidate)


def build_run_jobs_summary(queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT) -> dict[str, Any]:
    try:
        return summarize_run_jobs(queue_root)
    except Exception as exc:  # pragma: no cover
        return {
            "queue_root": str(Path(queue_root).expanduser()),
            "worker_mode": "serial",
            "status": "error",
            "error": str(exc),
            "runs": [],
        }


def build_run_job_detail_summary(
    run_id: str | None,
    queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT,
) -> dict[str, Any]:
    if not run_id:
        return {
            "selected_run_id": None,
            "status": "idle",
            "message": "Nenhuma run selecionada.",
        }
    try:
        job = inspect_run_job(run_id, queue_root=queue_root)
    except Exception as exc:  # pragma: no cover
        return {
            "selected_run_id": run_id,
            "status": "error",
            "error": str(exc),
        }
    telemetry = {
        "engine_requested": job.get("engine_requested"),
        "engine_used": job.get("engine_used"),
        "engine_mode": job.get("engine_mode"),
        "julia_available": job.get("julia_available"),
        "watermodels_available": job.get("watermodels_available"),
        "real_julia_probe_disabled": job.get("real_julia_probe_disabled"),
        "execution_mode": job.get("execution_mode"),
        "official_gate_valid": job.get("official_gate_valid"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "duration_s": job.get("duration_s"),
        "policy_mode": job.get("policy_mode"),
        "policy_message": job.get("policy_message"),
        "failure_reason": job.get("failure_reason"),
        "failure_stacktrace_excerpt": job.get("failure_stacktrace_excerpt"),
    }
    return {
        "selected_run_id": job["run_id"],
        "status": job["status"],
        "requested_execution_mode": job.get("requested_execution_mode"),
        "execution_mode": job.get("execution_mode"),
        "official_gate_valid": job.get("official_gate_valid"),
        "rerun_of_run_id": job.get("rerun_of_run_id"),
        "rerun_source": job.get("rerun_source"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "run_dir": job.get("run_dir"),
        "events_path": job.get("events_path"),
        "log_path": job.get("log_path"),
        "source_bundle_reference_path": job.get("source_bundle_reference_path"),
        "source_bundle_reference": job.get("source_bundle_reference"),
        "source_bundle_root": job.get("source_bundle_root"),
        "source_bundle_version": job.get("source_bundle_version"),
        "source_bundle_manifest": job.get("source_bundle_manifest"),
        "source_bundle_files": job.get("source_bundle_files", {}),
        "queue_summary": job.get("queue_summary"),
        "result_summary_path": job.get("result_summary_path"),
        "error": job.get("error"),
        "engine_requested": telemetry["engine_requested"],
        "engine_used": telemetry["engine_used"],
        "engine_mode": telemetry["engine_mode"],
        "julia_available": telemetry["julia_available"],
        "watermodels_available": telemetry["watermodels_available"],
        "real_julia_probe_disabled": telemetry["real_julia_probe_disabled"],
        "duration_s": telemetry["duration_s"],
        "policy_mode": telemetry["policy_mode"],
        "policy_message": telemetry["policy_message"],
        "failure_reason": telemetry["failure_reason"],
        "failure_stacktrace_excerpt": telemetry["failure_stacktrace_excerpt"],
        "artifacts": job.get("artifacts", {}),
        "evidence": job.get("evidence", {}),
        "events": job.get("events", []),
        "log_tail": job.get("log_tail", ""),
        "telemetry": telemetry,
        "inspection": {
            "queue_root": str(Path(queue_root).expanduser().resolve(strict=False)),
            "run_dir": job.get("run_dir"),
            "artifacts_dir": job.get("artifacts_dir"),
            "events_path": job.get("events_path"),
            "log_path": job.get("log_path"),
            "source_bundle_reference_path": job.get("source_bundle_reference_path"),
            "queue_summary_source": (job.get("queue_summary") or {}).get("source"),
            "result_summary_path": job.get("result_summary_path"),
        },
    }


def build_run_jobs_snapshot(
    queue_root: str | Path = DEFAULT_RUN_QUEUE_ROOT,
    *,
    preferred_run_id: str | None = None,
) -> dict[str, Any]:
    summary = build_run_jobs_summary(queue_root)
    ordered_runs = list(summary.get("runs", []))
    options = [
        {
            "label": f"{run['run_id']} [{run['status']}]",
            "value": run["run_id"],
        }
        for run in reversed(ordered_runs)
    ]
    option_values = {option["value"] for option in options}
    selected_run_id = preferred_run_id if preferred_run_id in option_values else (
        options[0]["value"] if options else None
    )
    selected_run_summary = next((run for run in ordered_runs if run["run_id"] == selected_run_id), None)
    return {
        "summary": summary,
        "options": options,
        "selected_run_id": selected_run_id,
        "selected_run_summary": selected_run_summary,
        "selected_run_detail": build_run_job_detail_summary(selected_run_id, queue_root=queue_root),
    }


def _serialize_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _requires_diagnostic_python_emulation(bundle: Any) -> bool:
    engine_cfg = bundle.scenario_settings.get("hydraulic_engine", {})
    primary_engine = str(engine_cfg.get("primary", "watermodels_jl")).strip()
    fallback_engine = str(engine_cfg.get("fallback", "none")).strip()
    return primary_engine != "watermodels_jl" or fallback_engine != "none"


def _profile_dropdown_options(bundle: Any) -> list[dict[str, Any]]:
    return [{"label": profile, "value": profile} for profile in bundle.weight_profiles["profile_id"].tolist()]


def _family_dropdown_options(bundle: Any) -> list[dict[str, Any]]:
    return [{"label": "Todas", "value": "ALL"}] + [
        {"label": family, "value": family}
        for family in sorted(bundle.scenario_settings["enabled_families"])
    ]


def _weight_input_values(bundle: Any, profile_id: str) -> dict[str, float]:
    profile = bundle.weight_profiles.loc[bundle.weight_profiles["profile_id"] == profile_id].iloc[0]
    return {
        "cost_weight": float(profile["cost_weight"]),
        "quality_weight": float(profile["quality_weight"]),
        "flow_weight": float(profile["flow_weight"]),
        "resilience_weight": float(profile["resilience_weight"]),
        "cleaning_weight": float(profile["cleaning_weight"]),
        "operability_weight": float(profile["operability_weight"]),
    }


def _table(component_id: str, frame: pd.DataFrame, *, editable: bool = False) -> Any:
    return dag.AgGrid(
        id=component_id,
        columnDefs=[{"field": column} for column in frame.columns],
        rowData=frame.to_dict("records"),
        defaultColDef={"editable": editable, "resizable": True},
        dashGridOptions={"pagination": True, "animateRows": True},
    )


def _comparison_grid(records: list[dict[str, Any]]) -> Any:
    columns = [
        {"field": "comparison_role"},
        {"field": "candidate_id"},
        {"field": "topology_family"},
        {"field": "generation_source"},
        {"field": "score_final"},
        {"field": "feasible"},
        {"field": "infeasibility_reason"},
        {"field": "install_cost"},
        {"field": "fallback_cost"},
        {"field": "quality_score_raw"},
        {"field": "flow_out_score"},
        {"field": "resilience_score"},
        {"field": "cleaning_score"},
        {"field": "operability_score"},
        {"field": "fallback_component_count"},
    ]
    return dag.AgGrid(
        id="comparison-grid",
        columnDefs=columns,
        rowData=records,
        dashGridOptions={"pagination": True, "animateRows": True},
    )


def _family_summary_grid(records: list[dict[str, Any]]) -> Any:
    columns = [
        {"field": "topology_family"},
        {"field": "candidate_count"},
        {"field": "feasible_count"},
        {"field": "infeasible_candidate_count"},
        {"field": "viability_rate"},
        {"field": "min_cost"},
        {"field": "median_cost"},
        {"field": "max_cost"},
    ]
    return dag.AgGrid(
        id="family-summary-grid",
        columnDefs=columns,
        rowData=records,
        dashGridOptions={"pagination": True, "animateRows": True},
    )


def _catalog_grid(records: list[dict[str, Any]]) -> Any:
    columns = [
        {"field": "candidate_id"},
        {"field": "topology_family"},
        {"field": "generation_source"},
        {"field": "lineage_label"},
        {"field": "origin_family"},
        {"field": "generation_index"},
        {"field": "was_repaired"},
        {"field": "feasible"},
        {"field": "score_final"},
        {"field": "install_cost"},
        {"field": "quality_score_raw"},
        {"field": "flow_out_score"},
        {"field": "resilience_score"},
        {"field": "cleaning_score"},
        {"field": "operability_score"},
        {"field": "fallback_component_count"},
        {"field": "infeasibility_reason"},
        {"field": "constraint_failure_count"},
    ]
    return dag.AgGrid(
        id="catalog-grid",
        columnDefs=columns,
        rowData=records,
        dashGridOptions={"pagination": True, "animateRows": True},
    )


def _route_grid(records: list[dict[str, Any]]) -> Any:
    columns = [
        {"field": "route_id"},
        {"field": "feasible"},
        {"field": "reason"},
        {"field": "required_flow_lpm"},
        {"field": "delivered_flow_lpm"},
        {"field": "route_effective_q_max_lpm"},
        {"field": "hydraulic_slack_lpm"},
        {"field": "total_loss_lpm_equiv"},
        {"field": "bottleneck_component_id"},
        {"field": "critical_consequence"},
        {"field": "path_link_ids"},
    ]
    return dag.AgGrid(
        id="route-metrics-grid",
        columnDefs=columns,
        rowData=records,
        dashGridOptions={"pagination": True, "animateRows": True},
    )


def _route_dropdown_options(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"label": str(record["route_id"]), "value": str(record["route_id"])} for record in records]


def _default_route_highlight(records: list[dict[str, Any]]) -> str | None:
    if not records:
        return None
    ranked = sorted(
        records,
        key=lambda record: (
            bool(record.get("feasible", True)),
            float(record.get("hydraulic_slack_lpm") or 0.0),
            str(record.get("route_id")),
        ),
    )
    return str(ranked[0]["route_id"])


def _build_cytoscape_stylesheet(
    route_highlights: dict[str, Any],
    route_id: str | None,
    critical_component_ids: list[str],
) -> list[dict[str, Any]]:
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "background-color": "#1f77b4",
                "label": "data(label)",
                "color": "#ffffff",
                "font-size": "12px",
                "text-wrap": "wrap",
                "text-max-width": "120px",
            },
        },
        {"selector": "edge", "style": {"line-color": "#9aa4af", "width": 3, "curve-style": "bezier"}},
        {
            "selector": ".route-projection",
            "style": {
                "line-style": "dashed",
                "line-color": "#2d6a5a",
                "target-arrow-color": "#2d6a5a",
                "target-arrow-shape": "triangle",
                "width": 5,
            },
        },
    ]
    for component_id in critical_component_ids:
        stylesheet.append(
            {
                "selector": f'edge[id = "{component_id}"], node[id = "{component_id}"]',
                "style": {"line-color": "#f0a202", "background-color": "#f0a202", "width": 5},
            }
        )
    if not route_id:
        return stylesheet
    for link_id in route_highlights.get(route_id, []):
        stylesheet.append(
            {
                "selector": f'edge[id = "{link_id}"]',
                "style": {"line-color": "#d94f04", "width": 7, "target-arrow-color": "#d94f04"},
            }
        )
    stylesheet.append(
        {
            "selector": f'edge[route_id = "{route_id}"]',
            "style": {"line-color": "#d94f04", "width": 7, "target-arrow-color": "#d94f04"},
        }
    )
    return stylesheet


def _weight_inputs(bundle: Any) -> Any:
    profile = _weight_input_values(bundle, str(bundle.scenario_settings["ranking"]["default_profile"]))
    return html.Div(
        children=[
            html.H3("Pesos dinâmicos"),
            dcc.Input(id="weight-cost", type="number", value=profile["cost_weight"], persistence=True, persistence_type="session"),
            dcc.Input(id="weight-quality", type="number", value=profile["quality_weight"], persistence=True, persistence_type="session"),
            dcc.Input(id="weight-flow", type="number", value=profile["flow_weight"], persistence=True, persistence_type="session"),
            dcc.Input(id="weight-resilience", type="number", value=profile["resilience_weight"], persistence=True, persistence_type="session"),
            dcc.Input(id="weight-cleaning", type="number", value=profile["cleaning_weight"], persistence=True, persistence_type="session"),
            dcc.Input(id="weight-operability", type="number", value=profile["operability_weight"], persistence=True, persistence_type="session"),
        ],
    )


def _send_text_download(content: str, filename: str) -> Any:
    sender = getattr(dcc, "send_string", None)
    if callable(sender):  # pragma: no branch
        return sender(content, filename)
    return {"content": content, "filename": filename}


def _critical_routes(route_metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(
        route_metrics,
        key=lambda route: (
            bool(route.get("feasible", True)),
            float(route.get("hydraulic_slack_lpm") or 0.0),
            -float(route.get("required_flow_lpm") or 0.0),
        ),
    )
    return [
        {
            "route_id": route.get("route_id"),
            "feasible": route.get("feasible"),
            "reason": route.get("reason"),
            "hydraulic_slack_lpm": route.get("hydraulic_slack_lpm"),
            "bottleneck_component_id": route.get("bottleneck_component_id"),
            "critical_consequence": route.get("critical_consequence"),
        }
        for route in ranked[:3]
    ]


def _build_catalog_state_summary(
    *,
    profile_id: str,
    selected_candidate_id: str | None,
    ranked_records: list[dict[str, Any]],
    filters: dict[str, Any],
    aggregate_summary: dict[str, Any],
) -> str:
    summary = {
        "profile_id": profile_id,
        "selected_candidate_id": selected_candidate_id,
        "visible_candidate_count": len(ranked_records),
        "top_visible_candidate_id": ranked_records[0]["candidate_id"] if ranked_records else None,
        "visible_family_summary": _family_summary_from_records(ranked_records),
        "filters": filters,
        "aggregate_summary": {
            "candidate_count": aggregate_summary.get("candidate_count"),
            "viability_rate_by_family": aggregate_summary.get("viability_rate_by_family", {}),
            "infeasible_candidate_rate_by_reason": aggregate_summary.get("infeasible_candidate_rate_by_reason", {}),
            "feasible_cost_distribution": aggregate_summary.get("feasible_cost_distribution", {}),
        },
    }
    return json.dumps(summary, indent=2, ensure_ascii=False)


def _lookup_score(result: dict[str, Any], candidate_id: str, profile_id: str | None = None) -> float | None:
    ranked = result.get("ranked_profiles", {}).get(profile_id or result.get("default_profile_id"), [])
    for record in ranked:
        if record["candidate_id"] == candidate_id:
            return float(record.get("score_final", 0.0))
    return None


def _weight_overrides_active(weight_overrides: dict[str, Any] | None) -> bool:
    return bool(weight_overrides) and any(value not in (None, "") for value in weight_overrides.values())


def _filters_active(
    *,
    family: str | None,
    feasible_only: bool,
    max_cost: Any,
    min_quality: Any,
    min_flow: Any,
    min_resilience: Any,
    min_cleaning: Any,
    min_operability: Any,
    top_n_per_family: Any,
    fallback_filter: str | None,
    infeasibility_reason: str | None,
) -> bool:
    return any(
        [
            family not in (None, "", "ALL"),
            feasible_only,
            max_cost not in (None, ""),
            min_quality not in (None, ""),
            min_flow not in (None, ""),
            min_resilience not in (None, ""),
            min_cleaning not in (None, ""),
            min_operability not in (None, ""),
            top_n_per_family not in (None, ""),
            fallback_filter not in (None, "", "ALL"),
            infeasibility_reason not in (None, "", "ALL"),
        ]
    )


def _normalize_compare_ids(current_compare_ids: list[str] | str | None) -> list[str]:
    if current_compare_ids is None:
        return []
    if isinstance(current_compare_ids, str):
        return [current_compare_ids]
    return list(current_compare_ids)


def _default_comparison_ids(
    result: dict[str, Any],
    profile_id: str,
    filtered_records: list[dict[str, Any]],
    selected_candidate_id: str | None,
) -> list[str]:
    if not filtered_records:
        return []
    explanation = build_selected_candidate_explanation(result, profile_id=profile_id)
    visible_ids = {record["candidate_id"] for record in filtered_records}
    preferred_ids = [
        explanation.get("candidate_id"),
        (explanation.get("runner_up") or {}).get("candidate_id"),
        selected_candidate_id,
    ]
    comparison_ids = []
    for candidate_id in preferred_ids:
        if candidate_id and candidate_id in visible_ids and candidate_id not in comparison_ids:
            comparison_ids.append(candidate_id)
    if comparison_ids:
        return comparison_ids
    return [record["candidate_id"] for record in filtered_records[:4]]


def _family_summary_from_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("topology_family")), []).append(record)
    summary_rows = []
    for family, family_records in sorted(grouped.items()):
        feasible_records = [record for record in family_records if bool(record.get("feasible"))]
        costs = [float(record.get("install_cost", 0.0)) + float(record.get("fallback_cost", 0.0)) for record in feasible_records]
        summary_rows.append(
            {
                "topology_family": family,
                "candidate_count": len(family_records),
                "feasible_count": len(feasible_records),
                "infeasible_candidate_count": len(family_records) - len(feasible_records),
                "viability_rate": round(len(feasible_records) / max(len(family_records), 1), 4),
                "min_cost": round(min(costs), 3) if costs else None,
                "median_cost": round(float(pd.Series(costs).median()), 3) if costs else None,
                "max_cost": round(max(costs), 3) if costs else None,
            }
        )
    return summary_rows


def _infeasibility_reason_options(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    options = [{"label": "Todos", "value": "ALL"}]
    if not result:
        return options
    reasons = sorted(
        {
            str(item["metrics"].get("infeasibility_reason") or "NONE")
            for item in result.get("catalog", [])
        }
    )
    options.extend({"label": reason, "value": reason} for reason in reasons)
    return options


def _critical_component_ids(route_metrics: list[dict[str, Any]]) -> list[str]:
    component_ids = []
    for route in _critical_routes(route_metrics):
        component_id = route.get("bottleneck_component_id")
        if component_id and component_id not in component_ids:
            component_ids.append(str(component_id))
    return component_ids


def main() -> None:
    app = build_app()
    if DASH_AVAILABLE:  # pragma: no cover
        app.run(debug=False)
        return
    raise RuntimeError("Dash dependencies are not installed. The app layout was built successfully.")


if __name__ == "__main__":
    main()
