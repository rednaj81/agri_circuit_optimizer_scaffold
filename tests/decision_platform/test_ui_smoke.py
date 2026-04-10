from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest
import pandas as pd
import yaml

from decision_platform.api.run_pipeline import OfficialRuntimeConfigError
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.rendering.circuit import build_render_payload
from decision_platform.ui_dash._compat import DASH_AVAILABLE
from decision_platform.ui_dash.app import (
    _primary_tab_from_search,
    apply_edge_studio_edit,
    apply_node_studio_edit,
    build_studio_readiness_summary,
    build_app,
    build_node_studio_elements,
    build_primary_node_studio_elements,
    build_studio_projection_summary,
    build_candidate_detail,
    build_comparison_records,
    build_official_candidate_summary,
    build_catalog_view_state,
    filter_catalog_records,
    render_bundle_io_panel,
    render_catalog_state_panel,
    render_candidate_breakdown_panel,
    render_candidate_summary_panel,
    render_decision_contrast_panel,
    render_decision_flow_panel,
    render_decision_justification_panel,
    render_decision_signal_panel,
    render_decision_summary_panel,
    render_execution_summary_panel,
    render_product_journey_panel,
    render_product_space_banner,
    render_audit_workspace_panel,
    render_run_job_detail_panel,
    render_run_jobs_overview_panel,
    render_runs_flow_panel,
    render_runs_workspace_panel,
    render_studio_canvas_guidance_panel,
    render_studio_connectivity_panel,
    render_studio_focus_panel,
    render_studio_projection_panel,
    render_studio_readiness_panel,
    render_studio_selection_panel,
    render_studio_workspace_panel,
    render_decision_workspace_panel,
    move_node_studio_selection,
    rerank_catalog,
    save_and_reopen_local_bundle,
)
from tests.decision_platform.scenario_utils import (
    cleanup_scenario_copy,
    diagnostic_runtime_test_mode,
    prepare_isolated_tmp_dir,
    prepare_scenario_copy,
)

pytestmark = [pytest.mark.requires_dash, pytest.mark.ui]


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


def _collect_components_by_class_name(component: object, class_name: str) -> list[object]:
    matches: list[object] = []
    if getattr(component, "__class__", None).__name__ == class_name:
        matches.append(component)
    children = getattr(component, "children", None)
    if children is None:
        return matches
    child_items = children if isinstance(children, (list, tuple)) else [children]
    for child in child_items:
        matches.extend(_collect_components_by_class_name(child, class_name))
    return matches


def _collect_component_ids(component: object) -> list[str]:
    component_id = getattr(component, "id", None)
    collected = [str(component_id)] if component_id else []
    children = getattr(component, "children", None)
    if children is None:
        return collected
    child_items = children if isinstance(children, (list, tuple)) else [children]
    for child in child_items:
        collected.extend(_collect_component_ids(child))
    return collected


def _visible_tab_labels(component: object) -> list[str]:
    labels: list[str] = []
    for tab in _collect_components_by_class_name(component, "Tab"):
        style = getattr(tab, "style", {}) or {}
        if style.get("display") == "none":
            continue
        labels.append(str(getattr(tab, "label", "")))
    return labels


def _find_tab_by_label(component: object, label: str) -> object | None:
    for tab in _collect_components_by_class_name(component, "Tab"):
        style = getattr(tab, "style", {}) or {}
        if style.get("display") == "none":
            continue
        if str(getattr(tab, "label", "")) == label:
            return tab
    return None


def _component_id_is_inside_details(component: object, target_id: str) -> bool:
    for details in _collect_components_by_class_name(component, "Details"):
        if _find_component_by_id(details, target_id) is not None:
            return True
    return False


def _collect_text_content(component: object) -> str:
    if component is None:
        return ""
    if isinstance(component, str):
        return component
    if isinstance(component, (int, float, bool)):
        return str(component)
    children = getattr(component, "children", None)
    text = ""
    if children is None:
        return text
    child_items = children if isinstance(children, (list, tuple)) else [children]
    for child in child_items:
        text += _collect_text_content(child)
    return text


def _get_callback(app: object, *, output_prefix: str | None = None, input_id: str | None = None) -> Callable[..., Any]:
    callback_map = getattr(app, "callback_map", {})
    for callback_key, metadata in callback_map.items():
        if output_prefix is not None and not str(callback_key).startswith(output_prefix):
            continue
        if input_id is not None and not any(item["id"] == input_id for item in metadata.get("inputs", [])):
            continue
        callback = metadata.get("callback")
        if callback is None:
            continue
        return getattr(callback, "__wrapped__", callback)
    raise KeyError(f"Callback not found for output_prefix={output_prefix!r} input_id={input_id!r}")


def test_dash_app_builds_layout_and_callbacks_even_when_fail_closed() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    assert hasattr(app, "layout")
    assert app.layout is not None
    callback_count = len(getattr(app, "callbacks", [])) or len(getattr(app, "callback_map", {}))
    assert callback_count >= 4


def test_dash_app_http_entrypoints_open_locally_without_server_error() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    client = app.server.test_client()
    studio_response = client.get("/?tab=studio")
    decision_response = client.get("/?tab=decision")

    assert studio_response.status_code == 200
    assert decision_response.status_code == 200
    assert "Traceback" not in studio_response.get_data(as_text=True)
    assert "Traceback" not in decision_response.get_data(as_text=True)


@pytest.mark.skipif(not DASH_AVAILABLE, reason="Dash stack not installed in local validation environment.")
def test_real_dash_stack_is_available() -> None:
    assert DASH_AVAILABLE is True


def test_dash_app_exposes_authoring_save_reopen_controls() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    layout_repr = repr(app.layout)
    assert "node-studio-cytoscape" in layout_repr
    assert "node-studio-apply-button" in layout_repr
    assert "node-studio-move-button" in layout_repr
    assert "edge-studio-apply-button" in layout_repr
    assert "edge-studio-link-id" in layout_repr
    assert "edge-studio-from-node" in layout_repr
    assert "edge-studio-to-node" in layout_repr
    assert "save-reopen-bundle-button" in layout_repr
    assert "candidate-links-grid" in layout_repr
    assert "edge-component-rules-grid" in layout_repr
    assert "layout-constraints-grid" in layout_repr
    assert "topology-rules-editor" in layout_repr
    assert "scenario-settings-editor" in layout_repr
    assert "bundle-output-dir-input" in layout_repr


def test_dash_app_surfaces_only_four_primary_product_spaces() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    assert _visible_tab_labels(app.layout) == ["Studio", "Runs", "Decisão", "Auditoria"]
    assert _find_component_by_id(app.layout, "product-journey-panel") is not None
    assert _find_component_by_id(app.layout, "product-journey-card-studio") is not None
    assert _find_component_by_id(app.layout, "product-journey-card-runs") is not None
    assert _find_component_by_id(app.layout, "product-journey-card-decision") is not None
    assert _find_component_by_id(app.layout, "product-journey-card-audit") is not None
    assert _find_component_by_id(app.layout, "product-journey-open-studio-link") is not None
    assert _find_component_by_id(app.layout, "product-journey-open-runs-link") is not None
    assert _find_component_by_id(app.layout, "product-journey-open-decision-link") is not None
    assert _find_component_by_id(app.layout, "product-journey-open-audit-link") is not None
    assert _find_component_by_id(app.layout, "product-space-banner") is not None
    assert _find_component_by_id(app.layout, "product-space-switcher-studio-link") is not None
    assert _find_component_by_id(app.layout, "product-space-switcher-runs-link") is not None
    assert _find_component_by_id(app.layout, "product-space-switcher-decision-link") is not None
    assert _find_component_by_id(app.layout, "product-space-switcher-audit-link") is not None
    assert getattr(_find_component_by_id(app.layout, "product-space-banner"), "style", {}).get("position") == "sticky"
    assert _find_component_by_id(app.layout, "hero-open-studio-link") is not None
    assert _find_component_by_id(app.layout, "hero-open-runs-link") is not None
    assert _find_component_by_id(app.layout, "hero-open-decision-link") is not None
    assert _find_component_by_id(app.layout, "hero-open-audit-link") is not None


def test_studio_primary_surface_exposes_business_command_center() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    assert _find_component_by_id(app.layout, "studio-command-center-panel") is not None
    assert _find_component_by_id(app.layout, "studio-command-open-workbench-button") is not None
    assert _find_component_by_id(app.layout, "studio-add-source-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-add-product-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-add-mixer-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-add-service-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-add-outlet-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-quick-link-source") is not None
    assert _find_component_by_id(app.layout, "studio-quick-link-target") is not None
    assert _find_component_by_id(app.layout, "studio-quick-link-archetype") is not None
    assert _find_component_by_id(app.layout, "studio-quick-link-create-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-editor-panel") is not None
    assert _find_component_by_id(app.layout, "studio-route-focus-dropdown") is not None
    assert _find_component_by_id(app.layout, "studio-route-intent") is not None
    assert _find_component_by_id(app.layout, "studio-route-apply-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-start-from-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-complete-to-node-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-cancel-draft-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-create-from-edge-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-compose-intent") is not None
    assert _find_component_by_id(app.layout, "studio-route-compose-q-min-lpm") is not None
    assert _find_component_by_id(app.layout, "studio-route-compose-dose-min-l") is not None
    assert _find_component_by_id(app.layout, "studio-route-compose-measurement-required") is not None
    assert _find_component_by_id(app.layout, "studio-route-compose-confirm-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-composer-preview-panel") is not None
    assert _find_component_by_id(app.layout, "studio-route-composer-particularities") is not None
    assert _find_component_by_id(app.layout, "studio-route-particularities-panel") is not None
    assert _find_component_by_id(app.layout, "studio-route-draft-source-id") is None
    assert _find_component_by_id(app.layout, "studio-route-intent-mandatory-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-intent-desirable-button") is not None
    assert _find_component_by_id(app.layout, "studio-route-intent-optional-button") is not None
    assert _find_component_by_id(app.layout, "studio-canvas-selected-edge-banner") is not None
    assert _find_component_by_id(app.layout, "studio-primary-route-focus-dropdown") is not None
    assert _find_component_by_id(app.layout, "studio-primary-route-focus-apply-button") is not None
    assert getattr(_find_component_by_id(app.layout, "studio-context-detailed-panels"), "open", None) is False
    cytoscape = _find_component_by_id(app.layout, "node-studio-cytoscape")
    context_menu = getattr(cytoscape, "contextMenu", None)
    assert isinstance(context_menu, list)
    assert any(item.get("id") == "add-product-node" for item in context_menu)
    assert any(item.get("id") == "create-route-from-edge" for item in context_menu)
    assert any(item.get("id") == "mark-route-mandatory" for item in context_menu)
    assert any(item.get("id") == "reverse-edge" for item in context_menu)
    assert any(item.get("id") == "open-workbench" for item in context_menu)

    studio_text = _collect_text_content(_find_component_by_id(app.layout, "studio-command-center-panel"))
    assert "Desenhe primeiro as rotas que precisam de serviço" in studio_text
    assert "Intenção das rotas" in studio_text
    assert "R001 ·" not in studio_text
    assert "W ->" not in studio_text
    assert "Tap" not in studio_text
    assert "Junção" not in studio_text
    route_text = _collect_text_content(_find_component_by_id(app.layout, "studio-route-editor-panel"))
    canvas_text = _collect_text_content(_find_component_by_id(app.layout, "studio-canvas-guidance-panel"))
    assert "Trazer este trecho para o composer" in route_text
    assert "Usar esta entidade como origem" in route_text
    assert "Usar esta entidade como destino" in route_text
    assert "Quem supre quem agora" in route_text
    assert "Composer local da rota" in route_text
    assert "Confirmar rota no canvas" in route_text
    assert "Particularidades da rota em preparo" in route_text
    assert "Particularidades da rota em foco" in route_text
    assert "W ->" not in route_text
    assert "Tap" not in route_text
    assert "Junção" not in route_text
    assert "Trocar trecho sugerido" in canvas_text
    assert "Por que começar por aqui" in canvas_text
    assert "route:R001" not in canvas_text
    assert "R001 ·" not in canvas_text


def test_studio_initial_edge_focus_is_visible_and_not_null() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    edge_store = _find_component_by_id(app.layout, "edge-studio-selected-id")
    banner = _find_component_by_id(app.layout, "studio-canvas-selected-edge-banner")

    assert getattr(edge_store, "data", None)
    assert str(getattr(edge_store, "data", "")).startswith("route:")
    banner_text = _collect_text_content(banner)
    assert "Trecho fixado no Studio" in banner_text
    assert "route:R001" not in banner_text


def test_studio_primary_workspace_avoids_technical_internal_terms() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    workspace_text = _collect_text_content(_find_component_by_id(app.layout, "studio-workspace-panel"))
    canvas_text = _collect_text_content(_find_component_by_id(app.layout, "studio-canvas-guidance-panel"))

    assert "Junção" not in workspace_text
    assert "Hub estrela" not in workspace_text
    assert "Tap" not in workspace_text
    assert "Junção" not in canvas_text
    assert "Tap" not in canvas_text


def test_studio_route_focus_dropdown_keeps_business_language_in_primary_surface() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    dropdown = _find_component_by_id(app.layout, "studio-route-focus-dropdown")
    option_labels = [str(option.get("label")) for option in getattr(dropdown, "options", [])[:3]]
    readiness_text = _collect_text_content(_find_component_by_id(app.layout, "studio-readiness-panel"))

    assert option_labels
    assert option_labels[0].startswith("Tanque de água para Misturador")
    assert all("R00" not in label for label in option_labels)
    assert all("->" not in label for label in option_labels)
    assert "R001" not in readiness_text
    assert "W ->" not in readiness_text


def test_product_space_banner_uses_consistent_product_language_for_each_space() -> None:
    studio_banner = _collect_text_content(render_product_space_banner("studio"))
    runs_banner = _collect_text_content(render_product_space_banner("runs"))
    decision_banner = _collect_text_content(render_product_space_banner("decision"))
    audit_banner = _collect_text_content(render_product_space_banner("audit"))

    assert "Espaço ativo" in studio_banner
    assert "Trocar espaço" in studio_banner
    assert "Studio" in studio_banner
    assert "O que esta área resolve" in studio_banner
    assert "Estado do fluxo agora" in studio_banner
    assert "Próximo destino sugerido" in studio_banner
    assert "Runs" in runs_banner
    assert "Fila local e execução em foco" in runs_banner
    assert "Decisão" in decision_banner
    assert "Winner, runner-up e contraste com contexto" in decision_banner
    assert "Auditoria" in audit_banner
    assert "Trilha canônica e evidência técnica" in audit_banner


def test_decision_justification_panel_avoids_repeating_winner_summary_header() -> None:
    panel = render_decision_justification_panel(
        {
            "candidate_id": "cand-01",
            "official_product_candidate_id": "cand-01",
            "winner_reason_summary": "Lidera por menor custo mantendo leitura operacional suficiente.",
            "decision_status": "winner_clear",
            "technical_tie": False,
            "feasible": True,
            "critical_routes": [],
            "winner_penalties": [],
        },
        {
            "fallback_component_count": 0,
            "rules_triggered": ["Regra de custo dominante"],
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Justificativa da escolha" in panel_text
    assert "Por que lidera" in panel_text
    assert "Exportação" in panel_text
    assert "Winner oficial" not in panel_text


def test_product_space_banner_exposes_shell_switcher_for_all_primary_spaces() -> None:
    banner = render_product_space_banner(
        "runs",
        {"status": "ready", "readiness_headline": "O cenário está pronto para seguir para Runs."},
        {"run_count": 1, "active_run_ids": [], "next_queued_run_id": None},
        {"candidate_id": "cand-01", "feasible": True},
    )
    banner_text = _collect_text_content(banner)

    assert "Trocar espaço" in banner_text
    assert "Estado do fluxo agora" in banner_text
    assert "Próximo destino sugerido" in banner_text
    assert "Ir para Decisão" in banner_text
    assert getattr(_find_component_by_id(banner, "product-space-switcher-studio-link"), "href", None) == "?tab=studio"
    assert getattr(_find_component_by_id(banner, "product-space-switcher-runs-link"), "href", None) == "?tab=runs"
    assert getattr(_find_component_by_id(banner, "product-space-switcher-decision-link"), "href", None) == "?tab=decision"
    assert getattr(_find_component_by_id(banner, "product-space-switcher-audit-link"), "href", None) == "?tab=audit"


def test_product_space_banner_guides_next_destination_from_real_state() -> None:
    studio_ready_banner = _collect_text_content(
        render_product_space_banner(
            "studio",
            {
                "status": "ready",
                "readiness_headline": "O cenário já pode sair do Studio sem depender da trilha técnica.",
                "primary_action": "Validar a fila.",
            },
            {"run_count": 0, "active_run_ids": [], "next_queued_run_id": None},
            {},
        )
    )
    decision_blocked_banner = _collect_text_content(
        render_product_space_banner(
            "decision",
            {"status": "ready"},
            {"run_count": 2, "active_run_ids": [], "next_queued_run_id": None},
            {},
        )
    )

    assert "Fluxo liberado" in studio_ready_banner
    assert "Seguir para Runs" in studio_ready_banner
    assert "Decisão ainda depende de Runs" in decision_blocked_banner
    assert "Voltar para Runs" in decision_blocked_banner


def test_product_journey_panel_summarizes_all_primary_spaces() -> None:
    panel = render_product_journey_panel(
        "runs",
        {
            "status": "ready",
            "readiness_headline": "O cenário está pronto para seguir para Runs.",
            "next_steps": ["Abra a fila para validar a próxima rodada."],
        },
        {
            "run_count": 2,
            "next_queued_run_id": "run-002",
            "active_run_ids": [],
            "status_counts": {"completed": 1, "failed": 0},
        },
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "decision_status": "technical_tie",
            "technical_tie": True,
            "feasible": True,
        },
    )
    panel_text = _collect_text_content(panel)
    assert "Jornada principal" in panel_text
    assert "Escolha a próxima área pelo estado do produto" in panel_text
    assert "Studio" in panel_text
    assert "Pronto para Runs" in panel_text
    assert "Runs" in panel_text
    assert "Fila pronta" in panel_text
    assert "Decisão" in panel_text
    assert "Empate técnico" in panel_text
    assert "Auditoria" in panel_text
    assert "Trilha técnica" in panel_text
    assert "Transição sugerida" in panel_text
    assert "Seguir para Runs" in panel_text
    assert "Ir para Decisão" in panel_text
    assert getattr(_find_component_by_id(panel, "product-journey-open-studio-link"), "href", None) == "?tab=runs"
    assert getattr(_find_component_by_id(panel, "product-journey-open-runs-link"), "href", None) == "?tab=decision"


def test_shell_chrome_compacts_studio_and_decision_first_fold() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, output_prefix="..shell-hero-panel.style...product-journey-panel.style...product-space-banner.style..")

    studio_styles = callback("studio")
    decision_styles = callback("decision")
    runs_styles = callback("runs")

    assert studio_styles[0]["padding"] == "14px 16px"
    assert studio_styles[1]["display"] == "none"
    assert studio_styles[2]["padding"] == "12px 14px"
    assert decision_styles[1]["display"] == "none"
    assert runs_styles[0]["padding"] == "20px"
    assert runs_styles[1].get("display") != "none"


def test_product_space_banner_callback_tracks_active_primary_tab() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, output_prefix="product-space-banner.children")
    nodes_rows = [{"node_id": "W"}, {"node_id": "P1"}]
    routes_rows = [{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}]
    run_summary_text = json.dumps({"run_count": 1, "active_run_ids": [], "next_queued_run_id": None}, ensure_ascii=False)
    decision_summary_text = json.dumps({"candidate_id": "cand-01", "feasible": True}, ensure_ascii=False)
    studio_text = _collect_text_content(callback("studio", nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))
    runs_text = _collect_text_content(callback("runs", nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))
    decision_text = _collect_text_content(callback("decision", nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))
    audit_text = _collect_text_content(callback("audit", nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))

    assert "Studio" in studio_text
    assert "Próximo destino sugerido" in studio_text
    assert "Runs" in runs_text
    assert "Ir para Decisão" in runs_text
    assert "Decisão" in decision_text
    assert "Auditoria" in audit_text


def test_product_space_banner_stays_aligned_with_navigation_resolution() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    navigation_callback = _get_callback(app, input_id="studio-open-audit-button")
    banner_callback = _get_callback(app, output_prefix="product-space-banner.children")
    nodes_rows = [{"node_id": "W"}, {"node_id": "P1"}]
    routes_rows = [{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}]
    run_summary_text = json.dumps({"run_count": 1, "active_run_ids": [], "next_queued_run_id": None}, ensure_ascii=False)
    decision_summary_text = json.dumps({"candidate_id": "cand-01", "feasible": True}, ensure_ascii=False)

    runs_tab = navigation_callback("?tab=studio", 0, 40, 0, 0, 0, 0, "studio")
    decision_tab = navigation_callback("?tab=studio", 0, 0, 0, 50, 0, 0, "runs")
    audit_tab = navigation_callback("?tab=studio", 60, 0, 0, 0, 0, 0, "decision")

    assert "Runs" in _collect_text_content(banner_callback(runs_tab, nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))
    assert "Decisão" in _collect_text_content(banner_callback(decision_tab, nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))
    assert "Auditoria" in _collect_text_content(banner_callback(audit_tab, nodes_rows, [], routes_rows, run_summary_text, decision_summary_text))


def test_product_journey_panel_callback_tracks_active_primary_tab_and_state() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, output_prefix="product-journey-panel.children")
    journey_text = _collect_text_content(
        callback(
            "decision",
            [{"node_id": "S", "node_type": "water_tank", "x_m": 0.0, "y_m": 0.0}],
            [],
            [],
            json.dumps({"run_count": 0, "status_counts": {}, "active_run_ids": []}, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),
        )
    )

    assert "Espaço ativo" in journey_text
    assert "Decisão" in journey_text
    assert "Sem decisão utilizável" in journey_text
    assert "Sem runs" in journey_text


def test_studio_tab_surfaces_readiness_and_selection_context() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    studio_tab = _find_tab_by_label(app.layout, "Studio")
    assert studio_tab is not None
    assert _find_component_by_id(studio_tab, "studio-canvas-guidance-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-canvas-open-workbench-button") is not None
    assert _find_component_by_id(studio_tab, "studio-canvas-open-technical-guide-button") is not None
    assert _find_component_by_id(studio_tab, "studio-canvas-open-runs-link") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-context-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-context-direct-actions") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-require-measurement-button") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-create-route-button") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-reverse-edge-button") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-quick-edit-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-local-actions-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-context-detailed-panels") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-open-workbench-button") is not None
    assert _find_component_by_id(studio_tab, "studio-workspace-open-runs-button") is not None
    assert _find_component_by_id(studio_tab, "studio-readiness-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-status-banner") is not None
    assert _find_component_by_id(studio_tab, "studio-projection-coverage-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-connectivity-panel") is not None
    assert _find_component_by_id(studio_tab, "node-studio-summary-panel") is not None
    assert _find_component_by_id(studio_tab, "edge-studio-summary-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-editor-workbench") is not None
    assert _find_component_by_id(studio_tab, "node-studio-business-editor") is not None
    assert _find_component_by_id(studio_tab, "edge-studio-business-editor") is not None
    assert _find_component_by_id(studio_tab, "studio-technical-guide") is not None
    assert _find_component_by_id(studio_tab, "studio-open-technical-guide-button") is not None
    assert _find_component_by_id(studio_tab, "studio-open-audit-button") is not None
    assert _find_component_by_id(studio_tab, "studio-open-runs-button") is not None
    assert _find_component_by_id(studio_tab, "studio-readiness-open-workbench-button") is not None
    assert _find_component_by_id(studio_tab, "studio-readiness-open-audit-link") is not None
    recommended_focus_actions = [
        _find_component_by_id(studio_tab, "studio-focus-recommended-move-right-button"),
        _find_component_by_id(studio_tab, "studio-focus-recommended-open-workbench-button"),
        _find_component_by_id(studio_tab, "studio-focus-recommended-delete-edge-button"),
    ]
    assert any(action is not None for action in recommended_focus_actions)
    assert _find_component_by_id(studio_tab, "studio-focus-move-left-button") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-duplicate-node-button") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-delete-edge-button") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-node-label") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-node-apply-button") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-edge-length-m") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-edge-family-hint") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-edge-apply-button") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-edge-reverse-button") is not None
    assert _find_component_by_id(studio_tab, "studio-focus-open-workbench-button") is not None
    assert getattr(_find_component_by_id(studio_tab, "studio-context-detailed-panels"), "open", None) is False
    assert getattr(_find_component_by_id(studio_tab, "studio-workspace-supply-strip"), "open", None) is False
    assert getattr(_find_component_by_id(studio_tab, "studio-business-flow-panel"), "open", None) is False


def test_studio_canvas_guidance_panel_keeps_canvas_as_primary_entry() -> None:
    panel_without_focus = render_studio_canvas_guidance_panel(
        {
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
        },
        {},
        {},
    )
    panel_with_edge_focus = render_studio_canvas_guidance_panel(
        {
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "selected_node_id": "P1",
            "business_label": "Bomba principal",
        },
        {
            "selected_link_id": "L001",
            "business_label": "Bomba -> Misturador",
            "selected_edge": {"from_node": "P1", "to_node": "M"},
        },
        {"source_node_id": "P1", "sink_node_id": "M", "intent": "mandatory"},
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
        ],
        [{"link_id": "L001", "from_node": "P1", "to_node": "M", "archetype": "bus_segment"}],
        [{"route_id": "R001", "source": "P1", "sink": "M", "mandatory": True, "measurement_required": 0, "dose_min_l": 0}],
    )
    without_focus_text = _collect_text_content(panel_without_focus)
    with_edge_focus_text = _collect_text_content(panel_with_edge_focus)

    assert "Comece pelo canvas" in without_focus_text
    assert "Nenhum foco ativo no canvas." in without_focus_text
    assert "Bloqueio ou liberação local" in without_focus_text
    assert "Clique em uma entidade ou conexão do grafo" in without_focus_text
    assert "Gate para Runs" in without_focus_text
    assert "Cadeia visível neste foco" in without_focus_text
    assert "Abrir bancada completa" in without_focus_text
    assert "Trecho em foco: Bomba principal para Misturador" in with_edge_focus_text
    assert "Trocar trecho sugerido" in with_edge_focus_text
    assert "Por que começar por aqui" in with_edge_focus_text
    assert "Trazer este trecho para foco" in with_edge_focus_text
    assert "inverta a direção direto no primeiro fold" in with_edge_focus_text.lower()
    assert "Trazer trecho" in with_edge_focus_text
    assert "Mais ações: obrigatoriedade e bancada" in with_edge_focus_text
    assert "Abrir bancada desta conexão" in with_edge_focus_text
    assert "Abrir orientação deste foco" in with_edge_focus_text
    assert "Cenário pronto para seguir para Runs." in with_edge_focus_text
    assert "Quem supre este foco" in with_edge_focus_text
    assert "Quem este foco supre" in with_edge_focus_text
    assert "Rota em preparo" in with_edge_focus_text
    assert "Ver trechos legíveis deste foco" in with_edge_focus_text
    assert "route:R001" not in with_edge_focus_text


def test_studio_canvas_guidance_panel_surfaces_contextual_blocker_and_runs_gate() -> None:
    panel = render_studio_canvas_guidance_panel(
        {
            "status": "needs_attention",
            "blocker_count": 1,
            "warning_count": 0,
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
        },
        {
            "selected_node_id": "",
            "business_label": "",
        },
        {
            "selected_link_id": "L900",
            "business_label": "Produto 1 -> W",
            "selected_edge": {"from_node": "P1", "to_node": "W"},
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Bloqueio local" in panel_text
    assert "Tanque de água" in panel_text
    assert "Ir para Runs quando o cenário estiver pronto" in panel_text
    assert _find_component_by_id(panel, "studio-canvas-reverse-edge-button") is not None
    assert _find_component_by_id(panel, "studio-canvas-intent-mandatory-button") is not None
    assert _find_component_by_id(panel, "studio-canvas-supply-chain-panel") is not None


def test_studio_canvas_guidance_promotes_route_completion_when_draft_source_exists() -> None:
    panel = render_studio_canvas_guidance_panel(
        {
            "status": "needs_attention",
            "warning_count": 1,
            "readiness_headline": "O cenário já pode avançar, mas ainda vale fechar avisos antes de rodar.",
        },
        {
            "selected_node_id": "M",
            "business_label": "Misturador",
        },
        {},
        {"source_node_id": "W", "sink_node_id": "", "intent": "desirable"},
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
        ],
        [{"link_id": "L001", "from_node": "W", "to_node": "M", "archetype": "bus_segment"}],
        [{"route_id": "R001", "source": "W", "sink": "M", "mandatory": False, "measurement_required": 0, "dose_min_l": 0}],
    )

    panel_text = _collect_text_content(panel)

    assert "Use Misturador como destino para concluir a rota em preparo direto no canvas." in panel_text
    assert "Tanque de água já está armado como origem; falta escolher o destino." in panel_text
    assert _find_component_by_id(panel, "studio-canvas-arm-target-button") is not None


def test_primary_route_focus_callback_switches_focus_using_business_route_selection() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    apply_focus_callback = _get_callback(app, input_id="studio-primary-route-focus-apply-button")
    sync_primary_focus_callback = _get_callback(app, output_prefix="..studio-primary-route-focus-dropdown.options")
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    nodes_rows = bundle.nodes.to_dict("records")
    route_rows = bundle.route_requirements.to_dict("records")
    candidate_links_rows = bundle.candidate_links.to_dict("records")

    options, selected_route_id = sync_primary_focus_callback(
        nodes_rows,
        route_rows,
        "route:R001",
        candidate_links_rows,
        None,
    )

    assert options
    assert selected_route_id == "R001"
    assert all("R00" not in str(option.get("label")) for option in options)

    next_edge_id, next_node_id, status = apply_focus_callback(
        1,
        "R004",
        route_rows,
        nodes_rows,
        "route:R001",
        "W",
    )

    assert next_edge_id == "route:R004"
    assert next_node_id == "P1"
    assert "Foco principal trocado para" in status
    assert "route:R004" not in status
    assert "Produto 1 para Misturador" in status


def test_studio_workspace_panel_unifies_focus_connectivity_and_runs_gate() -> None:
    panel = render_studio_workspace_panel(
        {
            "status": "needs_attention",
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
            "primary_action": "Corrigir regras estruturais e rotas inválidas antes de enfileirar uma nova run.",
            "blocker_count": 2,
            "warning_count": 1,
            "mandatory_route_count": 2,
            "blockers": ["L900 entra em W", "Rotas com dosagem sem medicao direta: R002"],
            "warnings": ["Nos sem conexao no grafo visivel: P3"],
            "next_steps": ["Feche os bloqueios estruturais antes de enfileirar uma nova run."],
        },
        {
            "selected_node_id": "P1",
            "business_label": "Bomba principal",
        },
        {},
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
        ],
        [
            {"link_id": "L001", "from_node": "W", "to_node": "P1", "archetype": "bus_segment"},
            {"link_id": "L002", "from_node": "P1", "to_node": "M", "archetype": "bus_segment"},
        ],
        [
            {"route_id": "R001", "source": "P1", "sink": "M", "mandatory": True},
        ],
        "Nó reposicionado com sucesso.",
    )
    panel_text = _collect_text_content(panel)

    assert "Leitura do cenário" in panel_text
    assert "Contexto dominante do Studio" in panel_text
    assert "Agora no Studio" in panel_text
    assert "Próxima ação" in panel_text
    assert "Passagem para Runs" in panel_text
    assert "Ações contextuais deste foco" in panel_text
    assert "Cadeia de suprimento e saída do Studio" in panel_text
    assert "A conexão L900 termina em Tanque de água" in panel_text
    assert "Cadeia visível deste foco" in panel_text
    assert "Bomba principal" in panel_text
    assert "Ajustes locais do canvas" in panel_text
    assert "Ajustes finos do foco" in panel_text
    assert "Fluxo atual" in panel_text
    assert "Impacto previsto" in panel_text
    assert "Corrigir no canvas" in panel_text
    assert "Runs bloqueado neste estado" in panel_text
    assert "Sinal de saída desta área" in panel_text
    assert getattr(_find_component_by_id(panel, "studio-workspace-open-runs-button"), "disabled", None) is True
    assert _find_component_by_id(panel, "studio-business-flow-panel") is not None
    assert _find_component_by_id(panel, "studio-workspace-supply-strip") is not None
    assert getattr(_find_component_by_id(panel, "studio-workspace-supply-strip"), "open", None) is False
    assert getattr(_find_component_by_id(panel, "studio-business-flow-panel"), "open", None) is False
    assert _find_component_by_id(panel, "studio-focus-node-label") is not None
    assert _find_component_by_id(panel, "studio-focus-node-apply-button") is not None
    assert _find_component_by_id(panel, "studio-focus-edge-length-m") is not None
    assert _find_component_by_id(panel, "studio-focus-edge-family-hint") is not None
    assert _find_component_by_id(panel, "studio-focus-edge-apply-button") is not None
    assert _find_component_by_id(panel, "studio-focus-edge-reverse-button") is not None
    assert _find_component_by_id(panel, "studio-focus-edge-flow-preview") is not None
    assert _find_component_by_id(panel, "studio-focus-move-left-button") is not None
    assert _find_component_by_id(panel, "studio-focus-move-right-button") is not None
    assert _find_component_by_id(panel, "studio-focus-duplicate-node-button") is not None
    assert _find_component_by_id(panel, "studio-focus-delete-edge-button") is not None
    assert _find_component_by_id(panel, "studio-focus-open-workbench-button") is not None
    assert _find_component_by_id(panel, "studio-workspace-fine-tuning-panel") is not None
    assert _find_component_by_id(panel, "studio-workspace-priority-flow") is not None


def test_studio_workspace_panel_promotes_direct_measurement_fix_in_primary_context() -> None:
    panel = render_studio_workspace_panel(
        {
            "status": "needs_attention",
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
            "primary_action": "Corrigir regras estruturais e rotas inválidas antes de enfileirar uma nova run.",
            "blocker_count": 1,
            "warning_count": 0,
            "mandatory_route_count": 1,
            "blockers": ["Rotas com dosagem sem medicao direta: R002"],
            "warnings": [],
            "next_steps": ["Feche os bloqueios estruturais antes de enfileirar uma nova run."],
        },
        {
            "selected_node_id": "W",
            "business_label": "Tanque de água",
        },
        {
            "selected_link_id": "route:R002",
            "selected_edge": {"from_node": "W", "to_node": "M"},
            "from_label": "Tanque de água",
            "to_label": "Misturador",
            "business_label": "Tanque de água para Misturador",
        },
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
        ],
        [
            {"link_id": "L001", "from_node": "W", "to_node": "M", "archetype": "bus_segment"},
        ],
        [
            {"route_id": "R002", "source": "W", "sink": "M", "mandatory": True, "dose_min_l": 2.0, "measurement_required": False},
        ],
        "Trecho principal revisado.",
    )
    panel_text = _collect_text_content(panel)
    measurement_button = _find_component_by_id(panel, "studio-workspace-require-measurement-button")
    create_route_button = _find_component_by_id(panel, "studio-workspace-create-route-button")

    assert "Exigir medição direta" in panel_text
    assert "Próxima ação" in panel_text
    assert "Disponível agora neste trecho com dosagem." in panel_text
    assert measurement_button is not None
    assert getattr(measurement_button, "disabled", None) is False
    assert create_route_button is not None
    assert getattr(create_route_button, "disabled", None) is True


def test_studio_workspace_panel_keeps_context_actions_discoverable_when_not_applicable() -> None:
    panel = render_studio_workspace_panel(
        {
            "status": "needs_attention",
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
            "primary_action": "Corrigir regras estruturais e rotas inválidas antes de enfileirar uma nova run.",
            "blocker_count": 1,
            "warning_count": 0,
            "mandatory_route_count": 0,
            "blockers": ["Falta definir pelo menos uma rota obrigatória"],
            "warnings": [],
            "next_steps": ["Defina uma rota principal antes de abrir Runs."],
        },
        {
            "selected_node_id": "P1",
            "business_label": "Bomba principal",
        },
        {},
        [
            {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
        ],
        [],
        [],
        "Selecione um trecho para seguir.",
    )
    panel_text = _collect_text_content(panel)

    assert "Ações contextuais deste foco" in panel_text
    assert "Selecione uma conexão do canvas para revisar medição direta." in panel_text
    assert "Selecione uma conexão do canvas para criar uma rota a partir dela." in panel_text
    assert "Selecione uma conexão do canvas para revisar a direção deste trecho." in panel_text
    assert "Passagem para Runs" in panel_text
    assert "Corrigir no canvas" in panel_text
    assert getattr(_find_component_by_id(panel, "studio-workspace-require-measurement-button"), "disabled", None) is True
    assert getattr(_find_component_by_id(panel, "studio-workspace-create-route-button"), "disabled", None) is True
    assert getattr(_find_component_by_id(panel, "studio-workspace-reverse-edge-button"), "disabled", None) is True


def test_studio_primary_canvas_hides_internal_and_hub_nodes() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    studio_tab = _find_tab_by_label(app.layout, "Studio")
    cytoscape = _find_component_by_id(studio_tab, "node-studio-cytoscape")
    assert cytoscape is not None
    elements = getattr(cytoscape, "elements", [])
    node_ids = {element["data"]["id"] for element in elements if "source" not in element["data"]}
    edge_ids = {element["data"]["id"] for element in elements if "source" in element["data"]}
    assert node_ids.isdisjoint({"HS", "HD", "J1", "J2", "J3", "J4", "U1", "U2", "U3"})
    assert "route:R001" in edge_ids
    assert "route:R009" in edge_ids


def test_studio_canvas_uses_stable_zoom_bounds_for_full_hd() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    studio_tab = _find_tab_by_label(app.layout, "Studio")
    cytoscape = _find_component_by_id(studio_tab, "node-studio-cytoscape")
    assert cytoscape is not None
    assert getattr(cytoscape, "minZoom", None) == 0.58
    assert getattr(cytoscape, "maxZoom", None) == 1.28
    assert getattr(cytoscape, "wheelSensitivity", None) == 0.08
    assert getattr(cytoscape, "layout", {}).get("fit") is False
    assert getattr(cytoscape, "autoRefreshLayout", None) is False
    assert getattr(cytoscape, "boxSelectionEnabled", None) is False
    assert getattr(cytoscape, "style", {}).get("height") == "760px"


def test_studio_primary_editors_push_technical_fields_into_disclosure() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    studio_tab = _find_tab_by_label(app.layout, "Studio")
    for component_id in [
        "node-studio-node-id",
        "node-studio-node-type",
        "node-studio-allow-inbound",
        "node-studio-allow-outbound",
        "edge-studio-link-id",
        "edge-studio-from-node",
        "edge-studio-to-node",
        "edge-studio-archetype",
        "edge-studio-bidirectional",
    ]:
        assert _component_id_is_inside_details(studio_tab, component_id) is True


def test_studio_discovery_callbacks_open_guide_and_audit_tab() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    open_guide_callback = _get_callback(app, input_id="studio-open-technical-guide-button")
    open_navigation_callback = _get_callback(app, input_id="studio-open-audit-button")

    assert open_guide_callback(0, 1, False) is True
    assert open_navigation_callback("?tab=runs", 30, 20, 0, 0, 0, 10, "studio") == "audit"
    assert open_navigation_callback("?tab=decision", 0, 40, 0, 0, 0, 0, "studio") == "runs"
    assert open_navigation_callback("?tab=studio", 0, 0, 50, 0, 0, 0, "studio") == "runs"
    assert open_navigation_callback("?tab=studio", 0, 0, 0, 50, 0, 0, "runs") == "decision"
    assert open_navigation_callback("?tab=decision", 0, 0, 0, 0, 50, 0, "runs") == "decision"
    assert open_navigation_callback("?tab=decision", 0, 0, 0, 0, 0, 50, "runs") == "decision"
    assert open_navigation_callback("?tab=decision", 0, 0, 0, 0, 0, 0, "studio") == "decision"


def test_primary_tab_from_search_accepts_known_main_spaces() -> None:
    assert _primary_tab_from_search("?tab=studio") == "studio"
    assert _primary_tab_from_search("?tab=runs") == "runs"
    assert _primary_tab_from_search("?tab=decision") == "decision"
    assert _primary_tab_from_search("?tab=audit") == "audit"
    assert _primary_tab_from_search("?tab=unknown") == "studio"


def test_decision_tab_contains_advanced_sections_without_extra_primary_tabs() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    decision_tab = _find_tab_by_label(app.layout, "Decisão")
    assert decision_tab is not None
    assert _find_component_by_id(decision_tab, "decision-workspace-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-context-detailed-panels") is not None
    assert _find_component_by_id(decision_tab, "decision-summary-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-contrast-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-signal-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-flow-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-profile-views-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-final-comparison-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-final-choice-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-flow-open-runs-link") is not None
    assert _find_component_by_id(decision_tab, "decision-flow-open-audit-link") is not None
    assert _find_component_by_id(decision_tab, "decision-workspace-open-runs-link") is not None
    assert _find_component_by_id(decision_tab, "decision-workspace-open-audit-link") is not None
    assert _find_component_by_id(decision_tab, "decision-open-runs-button") is None
    assert _find_component_by_id(decision_tab, "decision-open-audit-button") is None
    assert _find_component_by_id(decision_tab, "compare-candidates-dropdown") is not None
    assert _find_component_by_id(decision_tab, "comparison-figure") is not None
    assert _find_component_by_id(decision_tab, "selected-candidate-dropdown") is not None
    assert _find_component_by_id(decision_tab, "candidate-breakdown-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-ranking-details") is not None
    assert _find_component_by_id(decision_tab, "decision-comparison-details") is not None
    assert _find_component_by_id(decision_tab, "decision-workspace-comparison-details") is not None
    extended_summary = _find_component_by_id(decision_tab, "decision-summary-panel-extended")
    assert extended_summary is not None
    extended_summary_text = _collect_text_content(extended_summary)
    assert "Justificativa da escolha" in extended_summary_text
    assert "Winner oficial" not in extended_summary_text


def test_app_layout_does_not_repeat_component_ids() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    component_ids = _collect_component_ids(app.layout)
    duplicates = sorted({component_id for component_id in component_ids if component_ids.count(component_id) > 1})
    assert duplicates == []


def test_studio_first_fold_pushes_route_editor_and_destructive_actions_below_disclosure() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    studio_tab = _find_tab_by_label(app.layout, "Studio")
    route_shell = _find_component_by_id(studio_tab, "studio-route-editor-shell")

    assert route_shell is not None
    assert getattr(route_shell, "open", None) is False
    assert _component_id_is_inside_details(studio_tab, "studio-route-editor-panel") is True
    assert _component_id_is_inside_details(studio_tab, "studio-focus-duplicate-node-button") is True
    assert _component_id_is_inside_details(studio_tab, "studio-focus-delete-edge-button") is True
    assert _component_id_is_inside_details(studio_tab, "studio-readiness-panel") is True
    assert _component_id_is_inside_details(studio_tab, "studio-focus-panel") is True
    assert _component_id_is_inside_details(studio_tab, "studio-connectivity-panel") is True


def test_edge_focus_switch_keeps_primary_node_positions_stable() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    refresh_elements_callback = _get_callback(app, output_prefix="node-studio-elements-store.data")
    sync_edge_callback = _get_callback(app, output_prefix="..edge-studio-selected-id.data")
    nodes_rows = bundle.nodes.to_dict("records")
    candidate_links_rows = bundle.candidate_links.to_dict("records")
    route_rows = bundle.route_requirements.to_dict("records")

    elements_before = refresh_elements_callback(nodes_rows, candidate_links_rows, route_rows, {})
    next_selected = sync_edge_callback(candidate_links_rows, {"id": "route:R004", "route_id": "R004"}, "route:R001")[0]
    elements_after = refresh_elements_callback(nodes_rows, candidate_links_rows, route_rows, {})

    node_positions_before = {
        element["data"]["id"]: dict(element.get("position") or {})
        for element in elements_before
        if "source" not in element.get("data", {})
    }
    node_positions_after = {
        element["data"]["id"]: dict(element.get("position") or {})
        for element in elements_after
        if "source" not in element.get("data", {})
    }

    assert next_selected == "route:R004"
    assert node_positions_before == node_positions_after


def test_runs_tab_combines_queue_and_execution_summary() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    runs_tab = _find_tab_by_label(app.layout, "Runs")
    assert runs_tab is not None
    assert _find_component_by_id(runs_tab, "runs-workspace-panel") is not None
    assert _find_component_by_id(runs_tab, "runs-context-detailed-panels") is not None
    assert _find_component_by_id(runs_tab, "run-jobs-overview-panel") is not None
    assert _find_component_by_id(runs_tab, "run-jobs-overview-signals") is not None
    assert _find_component_by_id(runs_tab, "runs-flow-panel") is not None
    assert _find_component_by_id(runs_tab, "runs-flow-open-studio-link") is not None
    assert _find_component_by_id(runs_tab, "runs-flow-open-decision-button") is not None
    assert _find_component_by_id(runs_tab, "runs-workspace-open-studio-link") is not None
    assert _find_component_by_id(runs_tab, "runs-workspace-open-decision-button") is not None
    assert _find_component_by_id(runs_tab, "runs-workspace-operational-lanes") is not None
    assert _find_component_by_id(runs_tab, "runs-workspace-next-step-panel") is not None
    assert _find_component_by_id(runs_tab, "execution-summary-panel") is not None
    assert _find_component_by_id(runs_tab, "run-jobs-status-banner") is not None
    assert _find_component_by_id(runs_tab, "run-job-detail-panel") is not None
    assert _find_component_by_id(runs_tab, "runs-open-studio-button") is None
    assert _find_component_by_id(runs_tab, "runs-open-decision-button") is None
    assert _find_component_by_id(runs_tab, "execution-open-decision-button") is not None
    assert _find_component_by_id(runs_tab, "run-button") is not None
    assert _find_component_by_id(runs_tab, "runs-operations-details") is not None


def test_runs_workspace_panel_distinguishes_scenario_gate_from_execution_state() -> None:
    blocked_panel = render_runs_workspace_panel(
        {
            "status": "needs_attention",
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
        },
        {
            "run_count": 2,
            "next_queued_run_id": "run-002",
            "active_run_ids": [],
            "queued_run_ids": ["run-002"],
            "latest_run_id": "run-001",
            "status_counts": {"completed": 1, "failed": 0},
        },
        {},
    )
    ready_panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 3,
            "next_queued_run_id": "run-003",
            "active_run_ids": ["run-002"],
            "queued_run_ids": ["run-003"],
            "latest_run_id": "run-001",
            "status_counts": {"completed": 1, "failed": 1},
        },
        {},
    )
    blocked_text = _collect_text_content(blocked_panel)
    ready_text = _collect_text_content(ready_panel)

    assert "Run em foco" in blocked_text
    assert "Fila agora" in blocked_text
    assert "Histórico terminal" in blocked_text
    assert "Próxima ação segura" in blocked_text
    assert "Histórico terminal secundário" in blocked_text
    assert "Gate do cenário e limites desta leitura" in blocked_text
    assert "Limitação agora" in blocked_text
    assert "A limitação principal ainda está no cenário" in blocked_text
    assert "Resultado" in blocked_text
    assert "Gate do cenário e limites desta leitura" in ready_text
    assert "Limitação agora" in ready_text
    assert "O cenário já passou no gate principal" in ready_text
    assert "Run em foco" in ready_text
    assert "run-002" in ready_text


def test_run_job_detail_panel_prioritizes_events_and_artifacts_over_logs() -> None:
    panel = render_run_job_detail_panel(
        {
            "selected_run_id": "run-007",
            "status": "completed",
            "requested_execution_mode": "diagnostic",
            "official_gate_valid": False,
            "duration_s": 12.5,
            "policy_mode": "diagnostic_override_probe_disabled",
            "source_bundle_root": "data/decision_platform/maquete_v2",
            "engine_used": "python_emulated_julia",
            "events": [
                {"status": "queued", "message": "Run criada na fila local."},
                {"status": "running", "message": "Execução principal em andamento."},
                {"status": "completed", "message": "Resumo executivo consolidado."},
            ],
            "artifacts": {
                "summary_json": "summary.json",
                "selected_candidate_json": "selected_candidate.json",
                "catalog_csv": "catalog.csv",
                "artifacts_dir": "artifacts",
            },
            "events_path": "events.jsonl",
            "log_path": "run.log",
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Timeline operacional" in panel_text
    assert "Eventos relevantes" in panel_text
    assert "Resultado e artefatos" in panel_text
    assert "Progresso desta run" in panel_text
    assert "Pode agir agora" in panel_text
    assert "O que falta" in panel_text
    assert "Origem desta rodada" in panel_text
    assert "Cenário" in panel_text
    assert "Run/job" in panel_text
    assert "Resultado agora" in panel_text
    assert "Passagem Runs -> Decisão" in panel_text
    assert "Resumo executivo disponível." in panel_text
    assert "Candidato selecionado disponível." in panel_text
    assert "Logs" not in panel_text
    assert _find_component_by_id(panel, "run-job-detail-timeline") is not None
    assert _find_component_by_id(panel, "run-job-detail-technical-details") is not None


def test_studio_readiness_panel_surfaces_runs_transition_with_real_readiness() -> None:
    summary = build_studio_readiness_summary(
        nodes_rows=[{"node_id": "W"}, {"node_id": "P1"}],
        candidate_links_rows=[],
        route_rows=[{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}],
    )
    panel = render_studio_readiness_panel(summary)
    panel_text = _collect_text_content(panel)

    assert "Passagem para Runs" in panel_text
    assert "Objetivo desta área" in panel_text
    assert "Próxima ação" in panel_text
    assert "Fluxo principal" in panel_text
    assert "Fila local de correção" in panel_text
    assert "Agora no Studio" in panel_text
    assert "Destino seguinte" in panel_text
    assert "ainda não tem fluxo suficiente" in panel_text.lower()
    assert "Conectar o grafo principal" in panel_text
    assert "Exige atenção" in panel_text
    assert "Revisar no canvas" in panel_text
    assert "Abrir Runs quando o cenário estiver pronto" in panel_text
    assert _find_component_by_id(panel, "studio-open-runs-button") is not None
    assert _find_component_by_id(panel, "studio-readiness-open-workbench-button") is not None
    assert _find_component_by_id(panel, "studio-readiness-action-0-button") is not None
    assert getattr(_find_component_by_id(panel, "studio-readiness-open-audit-link"), "href", None) == "?tab=audit"


def test_studio_readiness_panel_humanizes_primary_blockers_and_warnings() -> None:
    panel = render_studio_readiness_panel(
        {
            "status": "needs_attention",
            "readiness_headline": "Ainda há bloqueios estruturais impedindo a passagem segura para Runs.",
            "readiness_stage": "Remover bloqueios",
            "primary_action": "Corrigir regras estruturais e rotas inválidas antes de enfileirar uma nova run.",
            "business_node_count": 4,
            "business_edge_count": 2,
            "hidden_internal_node_count": 3,
            "mandatory_route_count": 2,
            "blocker_count": 2,
            "warning_count": 1,
            "blockers": ["L900 entra em W", "Rotas com dosagem sem medicao direta: R002"],
            "warnings": ["Nos sem conexao no grafo visivel: P3"],
            "next_steps": ["Feche os bloqueios estruturais antes de enfileirar uma nova run."],
        },
        [{"route_id": "R002", "source": "W", "sink": "M", "mandatory": True, "dose_min_l": 2.0}],
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
            {"node_id": "P3", "label": "Produto 3", "node_type": "product_tank", "zone": "process"},
        ],
    )
    panel_text = _collect_text_content(panel)

    assert "A conexão L900 termina em Tanque de água" in panel_text
    assert "Há rotas com dosagem sem medição direta compatível: Tanque de água para Misturador." in panel_text
    assert "Ainda existem entidades sem conexão na leitura principal do grafo: Produto 3." in panel_text
    assert "Bloqueado no Studio" in panel_text
    assert "Corrigir no canvas" in panel_text
    assert "Abrir Runs com bloqueios" in panel_text
    assert "Impacto operacional" in panel_text
    assert "Trazer para o canvas" in panel_text


def test_studio_readiness_panel_surfaces_primary_blocker_before_detailed_lists() -> None:
    panel = render_studio_readiness_panel(
        {
            "status": "needs_attention",
            "readiness_headline": "Ainda ha bloqueios estruturais impedindo a passagem segura para Runs.",
            "readiness_stage": "Remover bloqueios",
            "primary_action": "Corrija a principal restricao antes de revisar o restante do cenario.",
            "business_node_count": 8,
            "business_edge_count": 6,
            "hidden_internal_node_count": 2,
            "mandatory_route_count": 2,
            "blocker_count": 1,
            "warning_count": 1,
            "blockers": ["Rotas com dosagem sem medicao direta: R002"],
            "warnings": ["Nos sem conexao no grafo visivel: P3"],
            "next_steps": ["Feche o bloqueio principal antes de abrir Runs."],
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Bloqueio principal" in panel_text
    assert "Há rotas com dosagem sem medição direta compatível: R002." in panel_text
    assert "Feche o bloqueio principal antes de abrir Runs." in panel_text


def test_studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas() -> None:
    nodes_rows = [
        {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
        {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
    ]
    candidate_links_rows = [
        {"link_id": "L001", "from_node": "W", "to_node": "M", "archetype": "bus_segment", "length_m": 0.4, "family_hint": "loop"},
    ]
    panel = render_studio_connectivity_panel(
        {
            "blocker_count": 1,
            "warning_count": 2,
            "mandatory_route_count": 3,
            "measurement_route_count": 1,
            "blockers": [
                "L900 entra em W",
                "Rotas com dosagem sem medicao direta: R002",
            ],
            "warnings": [
                "Nos sem conexao no grafo visivel: P3",
            ],
            "next_steps": [
                "Corrigir bloqueios estruturais antes de enfileirar uma nova run.",
                "Salvar e reabrir o bundle canonico quando a revisao estiver pronta.",
            ],
        },
        {
            "selected_node_id": "W",
        },
        {
            "selected_link_id": "L001",
            "selected_edge": {"from_node": "W", "to_node": "M"},
            "from_label": "Tanque de água",
            "to_label": "Misturador",
        },
        [
            {"route_id": "R001", "source": "W", "sink": "M", "mandatory": True, "measurement_required": False},
            {"route_id": "R002", "source": "W", "sink": "M", "mandatory": True, "measurement_required": False, "dose_min_l": 2.0},
        ],
        nodes_rows,
        candidate_links_rows,
    )
    panel_text = _collect_text_content(panel)

    assert "Conectividade do grafo" in panel_text
    assert "O que destrava o cenário" in panel_text
    assert "Antes de abrir Runs" in panel_text
    assert "Trecho acionável no canvas" in panel_text
    assert "Origem do trecho" in panel_text
    assert "Destino do trecho" in panel_text
    assert "Se inverter no canvas" in panel_text
    assert "Rotas tocadas" in panel_text
    assert "Tanque de água para Misturador · Obrigatória" in panel_text
    assert "R001: W -> M" not in panel_text
    assert "Prioridade da seleção atual" in panel_text
    assert "Seleção atual" in panel_text
    assert "Cenário inteiro" in panel_text
    assert "Tanque de água só pode iniciar fluxo" in panel_text
    assert "Tanque de água para Misturador · Obrigatória usa dosagem sem medição direta compatível" in panel_text
    assert "Particularidades diretas deste trecho" in panel_text
    assert "Aplicar neste trecho" in panel_text
    assert "Exigir medição direta" in panel_text
    assert "Há conexões entrando em W no cenário" in panel_text
    assert "Corrigir bloqueios estruturais" in panel_text
    assert _find_component_by_id(panel, "studio-connectivity-route-direct-panel") is not None
    assert _find_component_by_id(panel, "studio-connectivity-route-intent") is not None
    assert _find_component_by_id(panel, "studio-connectivity-route-apply-button") is not None


def test_studio_connectivity_panel_previews_reverse_action_in_business_language() -> None:
    nodes_rows = [
        {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
        {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
    ]
    candidate_links_rows = [
        {"link_id": "L900", "from_node": "P1", "to_node": "W", "archetype": "bus_segment", "length_m": 0.3, "family_hint": "loop"},
    ]
    panel = render_studio_connectivity_panel(
        {
            "blocker_count": 1,
            "warning_count": 0,
            "mandatory_route_count": 0,
            "measurement_route_count": 0,
            "blockers": ["L900 entra em W"],
            "warnings": [],
            "next_steps": ["Corrija a direção antes de abrir Runs."],
        },
        {
            "selected_node_id": "P1",
            "business_label": "Bomba principal",
        },
        {
            "selected_link_id": "L900",
            "selected_edge": {"from_node": "P1", "to_node": "W", "archetype": "bus_segment", "length_m": 0.3, "family_hint": "loop"},
            "from_label": "Bomba principal",
            "to_label": "Tanque de água",
            "business_label": "Bomba principal -> Tanque de água",
        },
        [],
        nodes_rows,
        candidate_links_rows,
    )
    panel_text = _collect_text_content(panel)

    assert "Trecho acionável no canvas" in panel_text
    assert "Bomba principal supre Tanque de água." in panel_text
    assert "Impacto agora" in panel_text
    assert "A conexão em foco termina em Tanque de água; ajuste a direção antes de continuar." in panel_text
    assert "Se inverter agora, Tanque de água passa a suprir Bomba principal." in panel_text
    assert "A inversão reduz os bloqueios de readiness do cenário." in panel_text
    assert "Rotas tocadas" in panel_text
    assert "Nenhuma rota obrigatória ou de dosagem está ligada a este trecho agora." in panel_text
    assert "Abra o menu contextual desta conexão e use Inverter direção" in panel_text


def test_connectivity_route_callback_updates_selected_edge_route_directly() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="studio-connectivity-route-apply-button")
    route_rows = [
        {"route_id": "R001", "source": "W", "sink": "M", "mandatory": True, "measurement_required": 0, "dose_min_l": 0.0, "q_min_delivered_lpm": 12.0, "notes": ""},
    ]
    candidate_links_rows = [
        {"link_id": "L001", "from_node": "W", "to_node": "M", "archetype": "bus_segment"},
    ]

    updated_rows, status = callback(
        1,
        0,
        0,
        route_rows,
        "L001",
        candidate_links_rows,
        "desirable",
        ["measurement_required"],
        2.5,
        18.0,
        "ajuste local",
    )

    assert status == "Rota R001 atualizada direto no painel de conectividade."
    assert updated_rows[0]["route_group"] == "desirable"
    assert updated_rows[0]["measurement_required"] == 1
    assert updated_rows[0]["dose_min_l"] == 2.5
    assert updated_rows[0]["q_min_delivered_lpm"] == 18.0
    assert updated_rows[0]["notes"] == "ajuste local"


def test_workspace_context_measurement_button_updates_selected_edge_route_directly() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="studio-workspace-require-measurement-button")
    route_rows = [
        {"route_id": "R001", "source": "W", "sink": "M", "mandatory": True, "measurement_required": 0, "dose_min_l": 2.0, "q_min_delivered_lpm": 12.0, "notes": ""},
    ]
    candidate_links_rows = [
        {"link_id": "L001", "from_node": "W", "to_node": "M", "archetype": "bus_segment"},
    ]

    updated_rows, status = callback(
        0,
        0,
        1,
        route_rows,
        "L001",
        candidate_links_rows,
        "mandatory",
        [],
        2.0,
        12.0,
        "",
    )

    assert status == "Rota R001 agora exige medição direta no trecho em foco."
    assert updated_rows[0]["measurement_required"] == 1


def test_studio_focus_panel_uses_canvas_selection_as_primary_context() -> None:
    panel = render_studio_focus_panel(
        {
            "selected_node_id": "W",
            "business_label": "Tanque de água",
            "role_label": "Tanque de água",
        },
        {
            "selected_link_id": "L001",
            "business_label": "Água para misturador",
            "selected_edge": {"from_node": "W", "to_node": "M"},
            "from_label": "Tanque de água",
            "to_label": "Misturador",
        },
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "M", "label": "Misturador", "node_type": "mixer", "zone": "process"},
            {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
        ],
        [
            {"link_id": "L001", "from_node": "W", "to_node": "M", "archetype": "bus_segment"},
            {"link_id": "L002", "from_node": "W", "to_node": "P1", "archetype": "bus_segment"},
        ],
        [
            {"route_id": "R001", "source": "W", "sink": "M", "mandatory": True, "dose_min_l": 2.0, "measurement_required": True},
            {"route_id": "R002", "source": "P1", "sink": "M", "mandatory": True},
        ],
    )
    panel_text = _collect_text_content(panel)

    assert "Foco do canvas" in panel_text
    assert "Tanque de água" in panel_text
    assert "Água para misturador" in panel_text
    assert "Rotas ligadas ao nó" in panel_text
    assert "Conexão em foco" in panel_text
    assert "Problema ou oportunidade" in panel_text
    assert "Relações de negócio deste foco" in panel_text
    assert "Tanque de água e Misturador supre Bomba principal." not in panel_text
    assert "Tanque de água supre Misturador (rota obrigatória)." in panel_text
    assert "Tanque de água supre Bomba principal." in panel_text
    assert "Edição direta deste foco" in panel_text
    assert "Controles rápidos já estão no primeiro fold do Studio." in panel_text
    assert "Use o painel local ao lado do canvas" in panel_text
    assert "Por que este foco importa" in panel_text
    assert "Exige atenção" in panel_text
    assert "Ações rápidas deste foco" in panel_text
    assert "Ação sugerida agora" in panel_text
    assert "Tanque de água não pode receber rotas entrando" in panel_text
    assert "rotas com dosagem exigem medição direta compatível" in panel_text
    assert "Rotas deste foco: 2 obrigatória(s), 1 com dosagem, 1 com medição direta." in panel_text
    assert "Confira comprimento e famílias sugeridas para a conexão L001." in panel_text
    assert _find_component_by_id(panel, "studio-focus-recommended-open-workbench-button") is not None
    assert _find_component_by_id(panel, "studio-focus-move-left-button") is None
    assert _find_component_by_id(panel, "studio-focus-move-up-button") is None
    assert _find_component_by_id(panel, "studio-focus-move-down-button") is None
    assert _find_component_by_id(panel, "studio-focus-node-label") is None
    assert _find_component_by_id(panel, "studio-focus-node-apply-button") is None
    assert _find_component_by_id(panel, "studio-focus-edge-length-m") is None
    assert _find_component_by_id(panel, "studio-focus-edge-family-hint") is None
    assert _find_component_by_id(panel, "studio-focus-edge-apply-button") is None
    assert _find_component_by_id(panel, "studio-focus-edge-reverse-button") is None
    assert _find_component_by_id(panel, "studio-focus-duplicate-node-button") is None
    assert _find_component_by_id(panel, "studio-focus-delete-edge-button") is None
    assert _find_component_by_id(panel, "studio-focus-open-workbench-button") is None


def test_studio_focus_panel_embeds_status_and_runs_gate_context() -> None:
    panel = render_studio_focus_panel(
        {
            "selected_node_id": "P1",
            "business_label": "Bomba principal",
            "role_label": "Bomba principal",
        },
        {},
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
        ],
        [
            {"link_id": "L001", "from_node": "W", "to_node": "P1", "archetype": "bus_segment"},
        ],
        [],
        {
            "blocker_count": 2,
            "warning_count": 0,
            "primary_action": "Corrigir regras estruturais e rotas inválidas antes de enfileirar uma nova run.",
        },
        "Nó reposicionado com sucesso.",
    )
    panel_text = _collect_text_content(panel)

    assert "Este foco ainda convive com bloqueios antes de Runs." in panel_text
    assert "Bomba principal é suprido por Tanque de água." in panel_text
    assert "Por que este foco importa" in panel_text
    assert "O cenário ainda tem 2 bloqueio(s) antes de Runs" in panel_text
    assert _find_component_by_id(panel, "studio-status-banner") is not None


def test_studio_focus_panel_prioritizes_recommended_action_for_invalid_edge() -> None:
    panel = render_studio_focus_panel(
        {
            "selected_node_id": "P1",
            "business_label": "Bomba principal",
            "role_label": "Bomba principal",
        },
        {
            "selected_link_id": "L900",
            "business_label": "Ligação inválida",
            "selected_edge": {"from_node": "P1", "to_node": "W"},
            "from_label": "Bomba principal",
            "to_label": "Tanque de água",
        },
        [
            {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
            {"node_id": "P1", "label": "Bomba principal", "node_type": "pump", "zone": "process"},
        ],
        [
            {"link_id": "L900", "from_node": "P1", "to_node": "W", "archetype": "bus_segment"},
        ],
        [],
    )
    panel_text = _collect_text_content(panel)

    assert "Ação sugerida agora" in panel_text
    assert "Remover conexão inválida" in panel_text
    assert "viola uma regra estrutural" in panel_text
    assert _find_component_by_id(panel, "studio-focus-recommended-delete-edge-button") is not None


def test_runs_flow_panel_reflects_studio_gate_and_queue_state() -> None:
    panel = render_runs_flow_panel(
        {
            "status": "needs_attention",
            "blocker_count": 2,
            "warning_count": 1,
            "readiness_headline": "Ainda há bloqueios ou avisos a revisar antes de enfileirar.",
        },
        {
            "run_count": 3,
            "next_queued_run_id": "run-003",
            "active_run_ids": [],
            "status_counts": {"failed": 1},
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Camada detalhada de Runs" in panel_text
    assert "Objetivo desta área" in panel_text
    assert "Próxima ação" in panel_text
    assert "Estado do cenário" in panel_text
    assert "Entrada da Decisão" in panel_text
    assert "Aguardando readiness do Studio" in panel_text
    assert "Exige atenção" in panel_text
    assert "Voltar ao Studio" in panel_text
    assert "Decisão ainda secundária" in panel_text
    assert "run-003" in panel_text
    assert "conectividade" in panel_text.lower()
    assert getattr(_find_component_by_id(panel, "runs-flow-open-studio-link"), "href", None) == "?tab=studio"
    assert getattr(_find_component_by_id(panel, "runs-flow-open-decision-button"), "disabled", None) is True


def test_runs_workspace_panel_prioritizes_queue_focus_and_primary_transition() -> None:
    panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "blocker_count": 0,
            "warning_count": 0,
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 3,
            "next_queued_run_id": "run-003",
            "active_run_ids": [],
            "queued_run_ids": ["run-003"],
            "latest_run_id": "run-002",
            "status_counts": {"completed": 2, "failed": 0},
        },
        {
            "selected_candidate_id": "cand-01",
            "error": None,
        },
        {
            "selected_run_id": "run-002",
            "status": "completed",
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Leitura operacional de Runs" in panel_text
    assert "Run em foco" in panel_text
    assert "Fila agora" in panel_text
    assert "Histórico terminal" in panel_text
    assert "Próxima ação segura" in panel_text
    assert "Histórico terminal secundário" in panel_text
    assert "Gate do cenário e limites desta leitura" in panel_text
    assert "run-003" in panel_text
    assert "resultado utilizável" in panel_text.lower()
    assert "Resultado" in panel_text
    assert _find_component_by_id(panel, "runs-workspace-progress-rail") is not None
    assert _find_component_by_id(panel, "runs-workspace-operational-lanes") is not None
    assert _find_component_by_id(panel, "runs-workspace-open-studio-link") is not None
    assert getattr(_find_component_by_id(panel, "runs-workspace-open-decision-button"), "disabled", None) is False
    assert _find_component_by_id(panel, "runs-workspace-primary-open-decision-button") is not None
    assert _component_id_is_inside_details(panel, "runs-workspace-history-panel") is True


def test_studio_runs_decision_primary_journey_uses_consistent_transition_language() -> None:
    studio_panel = render_studio_readiness_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
            "readiness_stage": "Liberar a fila",
            "primary_action": "Abra Runs para transformar o cenário pronto em resultado utilizável.",
            "next_steps": ["Abra Runs para transformar o cenário pronto em resultado utilizável."],
            "blockers": [],
            "warnings": [],
            "blocker_count": 0,
            "warning_count": 0,
        }
    )
    runs_panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "blocker_count": 0,
            "warning_count": 0,
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 2,
            "next_queued_run_id": None,
            "active_run_ids": [],
            "queued_run_ids": [],
            "latest_run_id": "run-010",
            "status_counts": {"completed": 1, "failed": 0},
        },
        {
            "selected_candidate_id": "cand-01",
            "error": None,
        },
        {
            "selected_run_id": "run-010",
            "status": "completed",
        },
    )
    decision_panel = render_decision_workspace_panel(
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "decision_status": "winner_clear",
            "technical_tie": False,
            "feasible": True,
            "active_profile_id": "balanced",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-01",
            "score_margin_delta": 0.4,
            "winner_reason_summary": "Lidera por custo, fechamento das rotas e leitura operacional mais estável.",
        },
        {
            "visible_candidate_count": 4,
            "top_visible_family": "hybrid_free",
        },
        {
            "candidate_id": "cand-01",
            "topology_family": "hybrid_free",
        },
    )

    studio_text = _collect_text_content(studio_panel)
    runs_text = _collect_text_content(runs_panel)
    decision_text = _collect_text_content(decision_panel)

    assert "Próxima ação" in studio_text
    assert "Próxima ação" in runs_text
    assert "Próxima ação" in decision_text
    assert "resultado utilizável" in studio_text.lower()
    assert "resultado utilizável" in runs_text.lower()
    assert "resultado utilizável" not in decision_text.lower() or "decisão" in decision_text.lower()
    assert "Leitura humana" in decision_text
    assert "Referência oficial do produto" in decision_text


def test_runs_workspace_panel_distinguishes_failure_recovery_from_decision_ready() -> None:
    failed_panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 2,
            "next_queued_run_id": None,
            "active_run_ids": [],
            "queued_run_ids": [],
            "latest_run_id": "run-009",
            "status_counts": {"failed": 1, "completed": 0},
        },
        {
            "error": "Falha ao consolidar bundle.",
        },
        {
            "selected_run_id": "run-009",
            "status": "failed",
        },
    )
    failed_text = _collect_text_content(failed_panel)

    assert "Resultado bloqueado" in failed_text
    assert "Histórico terminal" in failed_text
    assert "run-009" in failed_text
    assert "Revisar falha" in failed_text
    assert "Decisao continua bloqueada" in failed_text
    assert getattr(_find_component_by_id(failed_panel, "runs-workspace-open-decision-button"), "disabled", None) is True
    assert getattr(_find_component_by_id(failed_panel, "runs-workspace-rerun-button"), "disabled", None) is False


def test_runs_workspace_panel_contrasts_failed_and_canceled_focus_states() -> None:
    failed_panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 1,
            "next_queued_run_id": None,
            "active_run_ids": [],
            "queued_run_ids": [],
            "latest_run_id": "run-030",
            "status_counts": {"failed": 1},
        },
        {},
        {
            "selected_run_id": "run-030",
            "status": "failed",
        },
    )
    canceled_panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 1,
            "next_queued_run_id": None,
            "active_run_ids": [],
            "queued_run_ids": [],
            "latest_run_id": "run-031",
            "status_counts": {"canceled": 1},
        },
        {},
        {
            "selected_run_id": "run-031",
            "status": "canceled",
        },
    )
    failed_text = _collect_text_content(failed_panel)
    canceled_text = _collect_text_content(canceled_panel)

    assert "Falha operacional em foco" in failed_text
    assert "Reexecutar com correção" in failed_text
    assert "Estado final" in failed_text
    assert "Cancelamento em foco" in canceled_text
    assert "Reexecutar se ainda fizer sentido" in canceled_text
    assert "Estado final" in canceled_text


def test_runs_workspace_panel_uses_refresh_cta_for_intermediate_execution_states() -> None:
    panel = render_runs_workspace_panel(
        {
            "status": "ready",
            "readiness_headline": "Cenário pronto para seguir para Runs.",
        },
        {
            "run_count": 2,
            "next_queued_run_id": None,
            "active_run_ids": ["run-004"],
            "queued_run_ids": [],
            "latest_run_id": "run-003",
            "status_counts": {"running": 1, "completed": 1},
        },
        {},
        {
            "selected_run_id": "run-004",
            "status": "running",
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Aguardar run em foco" in panel_text
    assert "Run em foco" in panel_text
    assert "Em execução" in panel_text
    assert _find_component_by_id(panel, "runs-workspace-progress-rail") is not None
    assert _find_component_by_id(panel, "runs-workspace-refresh-button") is not None


def test_primary_runs_panels_hide_raw_backend_keys_in_main_surface() -> None:
    overview_panel = render_run_jobs_overview_panel(
        {
            "run_count": 4,
            "queue_state": "running",
            "worker_mode": "serial",
            "next_queued_run_id": "run-004",
            "active_run_ids": ["run-003"],
            "queued_run_ids": ["run-004"],
            "terminal_run_ids": ["run-001", "run-002"],
            "latest_run_id": "run-003",
            "latest_updated_at": "2026-04-06T04:00:00Z",
            "status_counts": {"queued": 1, "running": 1, "completed": 1, "failed": 1},
        }
    )
    detail_panel = render_run_job_detail_panel(
        {
            "selected_run_id": "run-001",
            "status": "completed",
            "requested_execution_mode": "official",
            "official_gate_valid": True,
            "duration_s": 12.5,
            "source_bundle_root": "data/decision_platform/maquete_v2",
            "policy_mode": "julia_only",
            "engine_used": "julia",
        }
    )
    execution_panel = render_execution_summary_panel(
        {
            "candidate_count": 8,
            "feasible_count": 3,
            "selected_candidate_id": "cand-01",
            "default_profile_id": "balanced",
            "scenario_bundle_root": "data/decision_platform/maquete_v2",
            "error": None,
        }
    )
    overview_text = _collect_text_content(overview_panel)
    detail_text = _collect_text_content(detail_panel)
    execution_text = _collect_text_content(execution_panel)

    assert "Ver fila e histórico detalhados" in overview_text
    assert "official_gate_valid:" not in detail_text
    assert "policy_mode:" not in detail_text
    assert "duracao_s:" not in detail_text
    assert "Concluída" in detail_text
    assert "Modo da rodada" in detail_text
    assert "Erro operacional:" in execution_text
    assert "Objetivo desta área" in execution_text
    assert "Próxima ação" in execution_text
    assert "Próxima ação" in detail_text
    assert "Próxima ação" in execution_text
    assert "Abrir Decisão desta execução" in execution_text
    assert _component_id_is_inside_details(overview_panel, "run-jobs-overview-history-block") is True
    assert _component_id_is_inside_details(execution_panel, "execution-summary-context-list") is True


def test_run_job_detail_panel_covers_preparing_and_exporting_states() -> None:
    preparing_panel = render_run_job_detail_panel(
        {
            "selected_run_id": "run-010",
            "status": "preparing",
            "requested_execution_mode": "official",
            "official_gate_valid": True,
        }
    )
    exporting_panel = render_run_job_detail_panel(
        {
            "selected_run_id": "run-011",
            "status": "exporting",
            "requested_execution_mode": "official",
            "official_gate_valid": True,
        }
    )
    preparing_text = _collect_text_content(preparing_panel)
    exporting_text = _collect_text_content(exporting_panel)

    assert "preparando artefatos" in preparing_text.lower()
    assert "Em preparação" in preparing_text
    assert "1/5 etapas em andamento" in preparing_text
    assert "Andamento real em preparação" in preparing_text
    assert "Run em foco" in preparing_text
    assert "finalizando artefatos" in exporting_text.lower()
    assert "Consolidando saída" in exporting_text
    assert "4/5 etapas em andamento" in exporting_text
    assert "Andamento real na consolidação" in exporting_text
    assert "Timeline operacional" in exporting_text
    assert "Agora" in exporting_text


def test_run_jobs_overview_panel_clarifies_queue_now_vs_recent_history() -> None:
    panel = render_run_jobs_overview_panel(
        {
            "run_count": 4,
            "queue_state": "running",
            "worker_mode": "serial",
            "next_queued_run_id": "run-004",
            "active_run_ids": ["run-003"],
            "queued_run_ids": ["run-004"],
            "terminal_run_ids": ["run-001", "run-002"],
            "latest_run_id": "run-003",
            "latest_updated_at": "2026-04-06T04:00:00Z",
            "status_counts": {
                "queued": 1,
                "running": 1,
                "completed": 1,
                "failed": 1,
            },
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Execução em andamento" in panel_text
    assert "Fila agora" in panel_text
    assert "Execução agora" in panel_text
    assert "Histórico recente" in panel_text
    assert "Estados da operação" in panel_text
    assert "Falhou" in panel_text
    assert "Pode fazer agora" in panel_text
    assert "Em execução: run-003" in panel_text
    assert "Próxima a rodar: run-004" in panel_text
    assert "Última run conhecida: run-003" in panel_text
    assert "Falhas" in panel_text
    assert _component_id_is_inside_details(panel, "run-jobs-overview-history-block") is True


def test_run_jobs_overview_panel_surfaces_preparing_and_recovery_states() -> None:
    panel = render_run_jobs_overview_panel(
        {
            "run_count": 3,
            "queue_state": "preparing",
            "worker_mode": "serial",
            "next_queued_run_id": None,
            "active_run_ids": [],
            "queued_run_ids": [],
            "terminal_run_ids": ["run-001"],
            "latest_run_id": "run-002",
            "status_counts": {"preparing": 1, "failed": 1, "completed": 1},
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Preparação em andamento" in panel_text
    assert "1 preparando" in panel_text
    assert "Falhou" in panel_text
    assert "Preparando" in panel_text


def test_run_jobs_overview_panel_explains_status_language_for_terminal_and_rerun_states() -> None:
    panel = render_run_jobs_overview_panel(
        {
            "run_count": 5,
            "queue_state": "exporting",
            "worker_mode": "serial",
            "next_queued_run_id": None,
            "active_run_ids": [],
            "queued_run_ids": [],
            "latest_run_id": "run-011",
            "runs": [
                {"run_id": "run-007", "status": "completed", "lineage": {"is_rerun": False}},
                {"run_id": "run-008", "status": "canceled", "lineage": {"is_rerun": False}},
                {"run_id": "run-009", "status": "queued", "lineage": {"is_rerun": True, "source_run_id": "run-007"}},
                {"run_id": "run-010", "status": "preparing", "lineage": {"is_rerun": False}},
                {"run_id": "run-011", "status": "exporting", "lineage": {"is_rerun": False}},
            ],
            "status_counts": {"queued": 1, "preparing": 1, "exporting": 1, "completed": 1, "canceled": 1},
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Estados da operação" in panel_text
    assert "Em preparação" in panel_text
    assert "Consolidando saída" in panel_text
    assert "Cancelada" in panel_text
    assert "Reexecução" in panel_text


def test_run_job_detail_panel_distinguishes_failed_canceled_and_rerun_guidance() -> None:
    failed_panel = render_run_job_detail_panel(
        {
            "selected_run_id": "run-020",
            "status": "failed",
            "requested_execution_mode": "official",
            "official_gate_valid": False,
            "events": [{"status": "failed", "message": "Gate oficial recusou a execução."}],
        }
    )
    canceled_panel = render_run_job_detail_panel(
        {
            "selected_run_id": "run-021",
            "status": "canceled",
            "requested_execution_mode": "diagnostic",
            "official_gate_valid": False,
            "rerun_of_run_id": "run-015",
            "source_bundle_root": "data/decision_platform/maquete_v2",
            "events": [{"status": "canceled", "message": "Operador interrompeu a rodada."}],
        }
    )
    failed_text = _collect_text_content(failed_panel)
    canceled_text = _collect_text_content(canceled_panel)

    assert "Bloqueio operacional" in failed_text
    assert "Passagem Runs -> Decisão" in failed_text
    assert "Interrompida com intenção" in canceled_text
    assert "Origem desta rodada" in canceled_text
    assert "reexecução de run-015" in canceled_text.lower()


def test_execution_summary_panel_only_opens_decision_with_usable_result() -> None:
    panel = render_execution_summary_panel(
        {
            "candidate_count": 0,
            "feasible_count": 0,
            "selected_candidate_id": None,
            "default_profile_id": "balanced",
            "scenario_bundle_root": "data/decision_platform/maquete_v2",
            "error": None,
        }
    )
    panel_text = _collect_text_content(panel)
    decision_button = _find_component_by_id(panel, "execution-open-decision-button")

    assert "Ainda sem candidato oficial" in panel_text
    assert "Decisão indisponível nesta execução" in panel_text
    assert getattr(decision_button, "disabled", None) is True


def test_primary_surfaces_explain_empty_states_without_debug_language() -> None:
    studio_selection = render_studio_selection_panel({}, "node")
    edge_selection = render_studio_selection_panel({}, "edge")
    runs_queue = render_run_jobs_overview_panel({})
    run_detail = render_run_job_detail_panel({})
    execution = render_execution_summary_panel({})
    decision = render_decision_summary_panel({})
    candidate = render_candidate_summary_panel({})
    contrast = render_decision_contrast_panel({})
    signals = render_decision_signal_panel({})
    breakdown = render_candidate_breakdown_panel({})

    assert "Nenhuma entidade em foco." in _collect_text_content(studio_selection)
    assert "Selecione um nó no canvas" in _collect_text_content(studio_selection)
    assert "Nenhuma conexão em foco." in _collect_text_content(edge_selection)
    assert "Selecione uma conexão no canvas" in _collect_text_content(edge_selection)
    assert "Nenhuma run registrada ainda." in _collect_text_content(runs_queue)
    assert "Ainda não existe uma run em foco" in _collect_text_content(run_detail)
    assert "Estado atual" in _collect_text_content(run_detail)
    assert "Ainda não há resultado executivo suficiente" in _collect_text_content(execution)
    assert "ainda não existe decisão utilizável" in _collect_text_content(decision).lower()
    assert "Ainda não há candidato visível" in _collect_text_content(candidate)
    assert "Ainda não existe decisão utilizável" in _collect_text_content(contrast)
    assert "Ainda não há sinais consolidados" in _collect_text_content(signals)
    assert "Ainda não existe breakdown suficiente" in _collect_text_content(breakdown)


def test_runs_tab_keeps_workspace_recovery_ctas_in_primary_surface() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    runs_tab = _find_tab_by_label(app.layout, "Runs")
    assert runs_tab is not None
    assert _find_component_by_id(runs_tab, "runs-workspace-panel") is not None


def test_studio_selection_panel_distinguishes_node_and_edge_editing_guidance() -> None:
    node_panel = render_studio_selection_panel(
        {
            "business_label": "Bomba principal",
            "role_label": "Bomba principal",
            "selected_node": {"x_m": 0.4, "y_m": 0.2, "notes": "Node note"},
        },
        "node",
    )
    edge_panel = render_studio_selection_panel(
        {
            "business_label": "Ligação principal",
            "role_label": "Conexão principal",
            "from_label": "Bomba principal",
            "to_label": "Misturador",
            "selected_edge": {"length_m": 1.2, "family_hint": "loop", "notes": "Edge note"},
        },
        "edge",
    )
    node_text = _collect_text_content(node_panel)
    edge_text = _collect_text_content(edge_panel)

    assert "Use este resumo para preparar a edição do nó" in node_text
    assert "Posição: x=0.4 m, y=0.2 m" in node_text
    assert "Ajuste posição, rótulo e papel deste nó" in node_text
    assert "Use este resumo para preparar a revisão desta conexão" in edge_text
    assert "Fluxo principal: Bomba principal -> Misturador" in edge_text
    assert "Revise direção, comprimento e famílias sugeridas" in edge_text


def test_canvas_context_button_opens_studio_workbench() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, output_prefix="studio-editor-workbench.open")
    assert callback(1, None, None, None, None) is True


def test_focus_node_quick_edit_callback_updates_label_without_workbench() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="studio-focus-node-apply-button")
    updated_nodes, next_selected_id, status = callback(
        1,
        bundle.nodes.to_dict("records"),
        "P1",
        "Bomba principal refinada",
        bundle.candidate_links.to_dict("records"),
        bundle.route_requirements.to_dict("records"),
    )

    updated_row = next(row for row in updated_nodes if str(row["node_id"]) == "P1")
    assert next_selected_id == "P1"
    assert updated_row["label"] == "Bomba principal refinada"
    assert status == "Rótulo da entidade atualizado direto no foco do canvas."


def test_route_panel_callbacks_manage_composer_and_confirm_route_without_workbench() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    route_rows = [
        row
        for row in bundle.route_requirements.to_dict("records")
        if str(row["route_id"]) != "R018"
    ]
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    set_source_callback = _get_callback(app, input_id="studio-route-start-from-node-button")
    set_target_callback = _get_callback(app, input_id="studio-route-complete-to-node-button")
    sync_fields_callback = _get_callback(app, input_id="studio-route-compose-intent")
    confirm_callback = _get_callback(app, input_id="studio-route-compose-confirm-button")
    cancel_callback = _get_callback(app, input_id="studio-route-cancel-draft-button")

    composer_state, status = set_source_callback(1, 0, "I", {})
    assert composer_state["source_node_id"] == "I"
    assert status == "Origem da rota armada em I. Agora defina o destino explicitamente no composer."

    composer_state, status = set_target_callback(1, 0, "IR", composer_state)
    assert composer_state["sink_node_id"] == "IR"
    assert status == "Destino da rota ajustado para IR. Revise o preview e confirme no canvas."

    composer_state = sync_fields_callback("mandatory", 18, 2.5, "Fluxo local validado", ["measurement_required"], composer_state)
    assert composer_state["intent"] == "mandatory"
    assert composer_state["measurement_required"] is True
    assert composer_state["q_min_delivered_lpm"] == pytest.approx(18.0)
    assert composer_state["dose_min_l"] == pytest.approx(2.5)
    assert composer_state["notes"] == "Fluxo local validado"

    completed_rows, cleared_state, status = confirm_callback(1, composer_state, route_rows)
    created_route = next(row for row in completed_rows if str(row["route_id"]) == "R018")
    assert created_route["source"] == "I"
    assert created_route["sink"] == "IR"
    assert bool(created_route["mandatory"]) is True
    assert bool(created_route["measurement_required"]) is True
    assert created_route["q_min_delivered_lpm"] == pytest.approx(18.0)
    assert created_route["dose_min_l"] == pytest.approx(2.5)
    assert created_route["notes"] == "Fluxo local validado"
    assert cleared_state["source_node_id"] == ""
    assert status == "Rota R018 confirmada no canvas com preview revisado."

    canceled_state, cancel_status = cancel_callback(1)
    assert canceled_state["source_node_id"] == ""
    assert canceled_state["sink_node_id"] == ""
    assert cancel_status == "Composer local da rota limpo no canvas."


def test_readiness_action_callback_brings_blocker_into_canvas_focus() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="studio-readiness-action-0-button")
    nodes_rows = [
        {"node_id": "W", "label": "Tanque de água", "node_type": "water_tank", "zone": "supply"},
        {"node_id": "P1", "label": "Produto 1", "node_type": "product_tank", "zone": "process"},
    ]
    candidate_links_rows = [
        {"link_id": "L900", "from_node": "P1", "to_node": "W", "length_m": 1.0, "bidirectional": False, "family_hint": "", "archetype": "vertical_link"},
    ]
    route_rows = [
        {"route_id": "R900", "source": "P1", "sink": "W", "mandatory": True, "measurement_required": True, "dose_min_l": 0.0},
    ]

    next_node_id, next_edge_id, status = callback(
        100,
        None,
        None,
        None,
        nodes_rows,
        candidate_links_rows,
        route_rows,
        None,
        None,
    )

    assert next_node_id == "P1"
    assert next_edge_id == "L900"
    assert "A conexão L900 termina em Tanque de água" in status
    assert "inversão de direção" in status


def test_focus_edge_quick_edit_callback_updates_length_and_family_without_workbench() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="studio-focus-edge-apply-button")
    updated_links, next_selected_link_id, status = callback(
        1,
        bundle.candidate_links.to_dict("records"),
        "L013",
        0.91,
        "loop,hybrid",
        bundle.nodes.to_dict("records"),
        bundle.edge_component_rules.to_dict("records"),
    )

    updated_row = next(row for row in updated_links if str(row["link_id"]) == "L013")
    assert next_selected_link_id == "L013"
    assert updated_row["length_m"] == pytest.approx(0.91)
    assert updated_row["family_hint"] == "loop,hybrid"
    assert status == "Conexão ajustada direto no foco do canvas."


def test_focus_edge_reverse_callback_swaps_flow_without_workbench() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    original_row = next(row for row in bundle.candidate_links.to_dict("records") if str(row["link_id"]) == "L013")
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="studio-focus-edge-reverse-button")
    updated_links, next_selected_link_id, status = callback(
        1,
        0,
        0,
        bundle.candidate_links.to_dict("records"),
        "L013",
        bundle.nodes.to_dict("records"),
        bundle.route_requirements.to_dict("records"),
        bundle.edge_component_rules.to_dict("records"),
    )

    updated_row = next(row for row in updated_links if str(row["link_id"]) == "L013")
    assert next_selected_link_id == "L013"
    assert updated_row["from_node"] == original_row["to_node"]
    assert updated_row["to_node"] == original_row["from_node"]
    assert "Conexão invertida direto no foco do canvas." in status
    assert "Agora" in status
    assert "A inversão" in status or "Runs" in status


def test_decision_flow_panel_makes_transition_and_next_action_explicit() -> None:
    panel = render_decision_flow_panel(
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "active_profile_id": "min_cost",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-03",
            "decision_status": "technical_tie",
            "technical_tie": True,
            "topology_family": "hybrid_free",
            "runner_up_topology_family": "hybrid_loop",
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Passagem Runs -> Decisão" in panel_text
    assert "Estado atual" in panel_text
    assert "Objetivo desta área" in panel_text
    assert "Próxima ação" in panel_text
    assert "Winner atual" in panel_text
    assert "Saída do fluxo" in panel_text
    assert "cand-01" in panel_text
    assert "cand-02" in panel_text
    assert "Winner oficial" in panel_text
    assert "Runner-up de referência" in panel_text
    assert "Perfil em leitura" in panel_text
    assert "Menor custo" in panel_text
    assert "Referência oficial: Equilibrado -> cand-03" in panel_text
    assert "Estado da decisão" in panel_text
    assert "Empate técnico ativo" in panel_text
    assert "Empate técnico" in panel_text
    assert "Voltar para Runs" in panel_text
    assert "Abrir Auditoria" in panel_text
    assert "leitura humana assistida" in panel_text.lower()
    assert getattr(_find_component_by_id(panel, "decision-flow-open-runs-link"), "href", None) == "?tab=runs"
    assert getattr(_find_component_by_id(panel, "decision-flow-open-audit-link"), "href", None) == "?tab=audit"


def test_decision_workspace_panel_makes_winner_runner_up_and_tie_legible() -> None:
    panel = render_decision_workspace_panel(
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "active_profile_id": "min_cost",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-03",
            "key_factors": [{"summary": "winner e runner-up seguem empatados em custo global e leitura operacional principal."}],
            "profile_views": [
                {"profile_id": "min_cost", "candidate_id": "cand-01", "runner_up_candidate_id": "cand-02", "technical_tie": False, "feasible": True, "topology_family": "loop_ring", "score_margin_delta": 0.2},
                {"profile_id": "balanced", "candidate_id": "cand-03", "runner_up_candidate_id": "cand-02", "technical_tie": True, "feasible": True, "topology_family": "hybrid_free", "score_margin_delta": 0.0},
            ],
            "decision_status": "technical_tie",
            "technical_tie": True,
            "topology_family": "hybrid_free",
        },
        {
            "visible_candidate_count": 4,
            "top_visible_family": "hybrid_free",
        },
        {
            "candidate_id": "cand-04",
            "topology_family": "branch_loop",
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Leitura principal da decisão" in panel_text
    assert "Estado decisório agora" in panel_text
    assert "Passagem Runs -> Decisão" in panel_text
    assert "Winner oficial agora" in panel_text
    assert "Runner-up sob revisão" in panel_text
    assert "Próxima ação segura" in panel_text
    assert "Technical tie" in panel_text
    assert "Explícito" in panel_text
    assert "Technical tie explícito" in panel_text
    assert "Faixa decisória operacional" in panel_text
    assert "Referência oficial do produto" in panel_text
    assert "Runner-up ainda importa porque" in panel_text
    assert "Escolha manual atual" in panel_text
    assert "O que está empatado" in panel_text
    assert "empatados em custo global e leitura operacional principal" in panel_text
    assert "cand-04" in panel_text
    assert "confirme o critério humano antes de liberar a exportação assistida" in panel_text.lower()
    assert "registre o critério humano do empate" in panel_text.lower()
    assert "Comparação assistida e contexto" in panel_text
    assert _find_component_by_id(panel, "decision-workspace-primary-fold") is not None
    assert _find_component_by_id(panel, "decision-workspace-state-hero") is not None
    assert _find_component_by_id(panel, "decision-workspace-state-rail") is not None
    assert _find_component_by_id(panel, "decision-workspace-open-runs-link") is not None
    assert _find_component_by_id(panel, "decision-workspace-open-audit-link") is not None
    assert _find_component_by_id(panel, "decision-profile-views-panel") is not None
    assert _find_component_by_id(panel, "decision-final-comparison-panel") is not None
    assert _find_component_by_id(panel, "decision-final-choice-panel") is not None


def test_decision_workspace_panel_blocks_primary_choice_without_usable_result() -> None:
    panel = render_decision_workspace_panel({}, {"visible_candidate_count": 0}, {})
    panel_text = _collect_text_content(panel)

    assert "Sem decisão utilizável" in panel_text
    assert "Winner oficial indisponível" in panel_text
    assert "Runner-up ainda indisponível" in panel_text
    assert "Recuperar execução em Runs" in panel_text
    assert "A Decisão permanece aberta apenas como leitura bloqueada" in panel_text
    assert "Voltar para Runs" in panel_text
    assert "volte para runs antes de qualquer escolha manual" in panel_text.lower()


def test_decision_workspace_panel_surfaces_infeasible_winner_as_blocked_state() -> None:
    panel = render_decision_workspace_panel(
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "decision_status": "winner_clear",
            "technical_tie": False,
            "feasible": False,
            "infeasibility_reason": "mandatory_route_failure",
            "winner_reason_summary": "Segue na frente por custo, mas sem fechar as rotas obrigatórias.",
        },
        {"visible_candidate_count": 2},
        {"candidate_id": "cand-01", "topology_family": "hybrid_free"},
    )
    panel_text = _collect_text_content(panel)

    assert "Winner inviável" in panel_text
    assert "Revisar bloqueio em Runs" in panel_text
    assert "rota obrigatória não conseguiu fechar" in panel_text
    assert "Existe ranking visível, mas a decisão principal segue bloqueada" in panel_text
    assert "Runner-up sob revisão" in panel_text
    assert "não exporte enquanto o winner oficial permanecer bloqueado" in panel_text.lower()


def test_runs_flow_panel_enables_decision_only_with_usable_execution_result() -> None:
    panel = render_runs_flow_panel(
        {
            "status": "ready",
            "blocker_count": 0,
            "warning_count": 0,
            "readiness_headline": "O cenário já passou pelo gate principal de prontidão do Studio.",
        },
        {
            "run_count": 2,
            "next_queued_run_id": None,
            "active_run_ids": [],
            "status_counts": {"completed": 2, "failed": 0},
        },
        {
            "selected_candidate_id": "cand-01",
            "error": None,
        },
    )
    panel_text = _collect_text_content(panel)
    decision_button = _find_component_by_id(panel, "runs-flow-open-decision-button")

    assert "Decisão disponível" in panel_text
    assert "Ir para Decisão" in panel_text
    assert getattr(decision_button, "disabled", None) is False


def test_decision_flow_panel_surfaces_contrast_risk_before_secondary_comparison() -> None:
    panel = render_decision_flow_panel(
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "decision_status": "winner_clear",
            "technical_tie": False,
            "feasible": True,
            "topology_family": "hybrid_free",
            "runner_up_topology_family": "hybrid_loop",
            "score_margin_delta": 0.2,
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Contraste fraco" in panel_text
    assert "margem curta" in panel_text
    assert "cand-01 lidera a leitura atual com contraste suficiente" in panel_text
    assert "cand-02 segue como melhor alternativa comparável" in panel_text


def test_decision_flow_panel_explains_when_no_usable_run_exists() -> None:
    panel = render_decision_flow_panel({})
    panel_text = _collect_text_content(panel)

    assert "Sem decisão utilizável" in panel_text
    assert "Ainda falta uma run utilizável" in panel_text
    assert "confirme uma execução concluída" in panel_text


def test_catalog_state_panel_explains_when_filters_hide_all_candidates() -> None:
    panel = render_catalog_state_panel(
        {
            "visible_candidate_count": 0,
            "selected_candidate_id": None,
            "visible_family_summary": [],
            "top_visible_candidate_id": None,
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Nenhum candidato ficou visível" in panel_text
    assert "Revise filtros, fallback e viabilidade" in panel_text


def test_primary_decision_panels_hide_raw_metric_keys_in_main_surface() -> None:
    decision_summary_panel = render_decision_summary_panel(
        {
            "candidate_id": "cand-01",
            "active_profile_id": "min_cost",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-03",
            "decision_status": "technical_tie",
            "technical_tie": True,
            "feasible": True,
            "topology_family": "hybrid_free",
            "score_final": 91.2,
            "total_cost": 10.5,
            "fallback_component_count": 1,
            "winner_reason_summary": "O candidato oficial manteve melhor equilíbrio global.",
            "runner_up_candidate_id": "cand-02",
        }
    )
    contrast_panel = render_decision_contrast_panel(
        {
            "candidate_id": "cand-01",
            "active_profile_id": "min_cost",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-03",
            "profile_views": [
                {"profile_id": "min_cost", "candidate_id": "cand-01", "runner_up_candidate_id": "cand-02", "technical_tie": False, "feasible": True, "topology_family": "loop_ring", "score_margin_delta": 0.2},
                {"profile_id": "balanced", "candidate_id": "cand-03", "runner_up_candidate_id": "cand-02", "technical_tie": True, "feasible": True, "topology_family": "hybrid_free", "score_margin_delta": 0.0},
                {"profile_id": "robust_quality", "candidate_id": "cand-03", "runner_up_candidate_id": "cand-02", "technical_tie": True, "feasible": True, "topology_family": "hybrid_free", "score_margin_delta": 0.0},
            ],
            "decision_status": "technical_tie",
            "technical_tie": True,
            "runner_up_candidate_id": "cand-02",
            "runner_up_topology_family": "hybrid_loop",
            "runner_up_score_final": 91.2,
            "runner_up_total_cost": 11.0,
            "total_cost": 10.5,
            "score_margin_delta": 0.0,
            "key_factors": [
                {
                    "summary": "vencedor e runner-up ficaram empatados nos scores e nas dimensões principais."
                }
            ],
        }
    )
    signal_panel = render_decision_signal_panel(
        {
            "infeasibility_reason": "mandatory_route_failure",
            "winner_penalties": ["usa 1 componentes de fallback"],
            "critical_routes": [{"route_id": "R001", "reason": "slack baixo"}],
            "fallback_component_count": 1,
        }
    )
    selected_panel = render_candidate_summary_panel(
        {
            "candidate_id": "cand-01",
            "topology_family": "hybrid_free",
            "feasible": False,
            "install_cost": 10.0,
            "fallback_cost": 0.5,
            "score_final": 91.2,
            "fallback_component_count": 1,
            "engine_used": "julia",
            "infeasibility_reason": "mandatory_route_failure",
        }
    )
    breakdown_panel = render_candidate_breakdown_panel(
        {
            "candidate_id": "cand-01",
            "install_cost": 10.0,
            "constraint_failure_count": 0,
            "fallback_component_count": 1,
            "quality_score_raw": 88.0,
            "resilience_score": 92.0,
            "operability_score": 86.0,
            "cleaning_score": 83.0,
            "rules_triggered": ["route coverage ok"],
        }
    )
    decision_text = _collect_text_content(decision_summary_panel)
    contrast_text = _collect_text_content(contrast_panel)
    signal_text = _collect_text_content(signal_panel)
    selected_text = _collect_text_content(selected_panel)
    breakdown_text = _collect_text_content(breakdown_panel)

    assert "Empate técnico" in decision_text
    assert "Winner do perfil atual" in decision_text
    assert "Perfil em leitura" in decision_text
    assert "Referência oficial do produto" in decision_text
    assert "Status da decisão" in decision_text
    assert "Leitura humana" in decision_text
    assert "Próxima ação" in decision_text
    assert "winner do perfil atual" in decision_text.lower()
    assert "mantenha o runner-up visível" in decision_text
    assert "Runner-up e contraste" in contrast_text
    assert "cand-02" in contrast_text
    assert "Empate técnico" in contrast_text
    assert "Technical tie em leitura humana" in contrast_text
    assert "decisão humana assistida" in contrast_text.lower()
    assert "Technical tie e trade-offs" in contrast_text
    assert "O que está empatado" in contrast_text
    assert "vencedor e runner-up ficaram empatados" in contrast_text.lower()
    assert "Perfis diferentes estão puxando winners diferentes" in contrast_text
    assert "`" not in decision_text
    assert "`" not in contrast_text
    assert "balanced" not in decision_text
    assert "robust_quality" not in contrast_text
    assert "mandatory_route_failure" not in signal_text
    assert "rota obrigatória não conseguiu fechar" in signal_text
    assert "Rota crítica R001" in signal_text
    assert "mandatory_route_failure" not in selected_text
    assert "engine_used:" not in selected_text
    assert "infeasibility_reason:" not in selected_text
    assert "quality_score_raw:" not in breakdown_text
    assert "resilience_score:" not in breakdown_text
    assert "winner_penalties" not in signal_text
    assert "Engine de avaliação:" in selected_text
    assert "rota obrigatória não conseguiu fechar" in selected_text
    assert "Qualidade bruta:" in breakdown_text


def test_decision_summary_panel_surfaces_infeasible_winner_without_console_language() -> None:
    panel = render_decision_summary_panel(
        {
            "candidate_id": "cand-01",
            "active_profile_id": "balanced",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-01",
            "decision_status": "winner_clear",
            "technical_tie": False,
            "feasible": False,
            "infeasibility_reason": "mandatory_route_failure",
            "topology_family": "hybrid_free",
            "score_final": 91.2,
            "total_cost": 10.5,
            "winner_reason_summary": "O ranking segue liderado por custo total e cobertura mínima.",
            "runner_up_candidate_id": "cand-02",
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Winner inviável" in panel_text
    assert "Winner oficial" in panel_text
    assert "Inviável" in panel_text
    assert "rota obrigatória não conseguiu fechar" in panel_text
    assert "use o motivo de inviabilidade e o runner-up" in panel_text.lower()
    assert "Leitura humana" in panel_text


def test_decision_contrast_panel_guides_when_runner_up_is_missing() -> None:
    panel = render_decision_contrast_panel(
        {
            "candidate_id": "cand-01",
            "profile_views": [
                {"profile_id": "balanced", "candidate_id": "cand-01", "runner_up_candidate_id": None, "technical_tie": False, "feasible": True, "topology_family": "hybrid_free", "score_margin_delta": 0.8},
            ],
            "decision_status": "winner_clear",
            "technical_tie": False,
            "feasible": True,
        }
    )
    panel_text = _collect_text_content(panel)

    assert "winner, mas ainda não existe runner-up comparável" in panel_text.lower()
    assert "Relaxe filtros ou recupere uma execução com contraste suficiente" in panel_text


def test_decision_contrast_panel_explains_profile_tradeoffs_without_replacing_official_reference() -> None:
    panel = render_decision_contrast_panel(
        {
            "candidate_id": "cand-01",
            "runner_up_candidate_id": "cand-02",
            "active_profile_id": "min_cost",
            "official_profile_id": "balanced",
            "official_product_candidate_id": "cand-03",
            "decision_status": "winner_clear",
            "technical_tie": False,
            "runner_up_topology_family": "hybrid_loop",
            "runner_up_score_final": 90.8,
            "runner_up_total_cost": 11.0,
            "total_cost": 10.5,
            "score_margin_delta": 0.3,
            "profile_views": [
                {"profile_id": "min_cost", "candidate_id": "cand-01", "runner_up_candidate_id": "cand-02", "technical_tie": False, "feasible": True, "topology_family": "loop_ring", "score_margin_delta": 0.3},
                {"profile_id": "balanced", "candidate_id": "cand-03", "runner_up_candidate_id": "cand-02", "technical_tie": True, "feasible": True, "topology_family": "hybrid_free", "score_margin_delta": 0.0},
                {"profile_id": "robust_quality", "candidate_id": "cand-03", "runner_up_candidate_id": "cand-02", "technical_tie": True, "feasible": True, "topology_family": "hybrid_free", "score_margin_delta": 0.0},
            ],
            "key_factors": [{"summary": "o perfil de menor custo aceita um circuito mais barato, enquanto o equilibrado preserva robustez e empate técnico."}],
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Trade-offs por perfil" in panel_text
    assert "Menor custo" in panel_text
    assert "Equilibrado" in panel_text
    assert "Robustez primeiro" in panel_text
    assert "Perfis diferentes estão puxando winners diferentes" in panel_text
    assert _find_component_by_id(panel, "decision-profile-tradeoff-panel") is not None


def test_decision_export_cta_tracks_manual_choice_without_overwriting_official_reference() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    callback = _get_callback(app, input_id="official-candidate-summary", output_prefix="export-selected-button.children")

    official_result = callback(
        json.dumps({"candidate_id": "cand-03"}, ensure_ascii=False),
        json.dumps({"candidate_id": "cand-03", "official_product_candidate_id": "cand-03"}, ensure_ascii=False),
    )
    profile_result = callback(
        json.dumps({"candidate_id": "cand-01"}, ensure_ascii=False),
        json.dumps({"candidate_id": "cand-01", "official_product_candidate_id": "cand-03"}, ensure_ascii=False),
    )
    manual_result = callback(
        json.dumps({"candidate_id": "cand-09"}, ensure_ascii=False),
        json.dumps({"candidate_id": "cand-01", "official_product_candidate_id": "cand-03"}, ensure_ascii=False),
    )
    blocked_result = callback(
        json.dumps({"candidate_id": "cand-01"}, ensure_ascii=False),
        json.dumps(
            {
                "candidate_id": "cand-01",
                "official_product_candidate_id": "cand-01",
                "decision_status": "winner_clear",
                "technical_tie": False,
                "feasible": False,
            },
            ensure_ascii=False,
        ),
    )
    tie_result = callback(
        json.dumps({"candidate_id": "cand-03"}, ensure_ascii=False),
        json.dumps(
            {
                "candidate_id": "cand-01",
                "official_product_candidate_id": "cand-03",
                "decision_status": "technical_tie",
                "technical_tie": True,
                "feasible": True,
            },
            ensure_ascii=False,
        ),
    )
    no_result = callback(
        json.dumps({"candidate_id": "cand-03"}, ensure_ascii=False),
        json.dumps({}, ensure_ascii=False),
    )

    assert official_result == ("Exportar referência oficial (cand-03)", False)
    assert profile_result == ("Exportar winner do perfil atual (cand-01)", False)
    assert manual_result == ("Exportar escolha manual atual (cand-09)", False)
    assert blocked_result == ("Exportação bloqueada: winner atual inviável", True)
    assert tie_result == ("Exportar decisão assistida atual (cand-03)", False)
    assert no_result == ("Exportação bloqueada até existir decisão utilizável", True)


def test_candidate_summary_panel_surfaces_primary_blocker_and_next_action() -> None:
    panel = render_candidate_summary_panel(
        {
            "candidate_id": "cand-01",
            "topology_family": "hybrid_free",
            "feasible": False,
            "install_cost": 10.0,
            "fallback_cost": 0.5,
            "score_final": 91.2,
            "fallback_component_count": 1,
            "engine_used": "julia",
            "infeasibility_reason": "mandatory_route_failure",
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Bloqueio principal" in panel_text
    assert "Inviável agora" in panel_text
    assert "rota obrigatória não conseguiu fechar" in panel_text
    assert "Próxima ação" in panel_text


def test_build_render_payload_keeps_only_business_circuit_surface_when_internal_hubs_dominate() -> None:
    bundle = SimpleNamespace(
        nodes=pd.DataFrame(
            [
                {"node_id": "W", "label": "Tanque de agua", "node_type": "water_tank", "x_m": 0.1, "y_m": 0.9, "zone": ""},
                {"node_id": "P1", "label": "Produto 1", "node_type": "product_tank", "x_m": 0.9, "y_m": 0.8, "zone": ""},
                {"node_id": "P3", "label": "Produto 3", "node_type": "product_tank", "x_m": 0.8, "y_m": 0.2, "zone": ""},
                {"node_id": "HS", "label": "Hub estrela sucao", "node_type": "junction", "x_m": 0.4, "y_m": 0.5, "zone": "hub"},
                {"node_id": "HD", "label": "Hub estrela descarga", "node_type": "junction", "x_m": 0.6, "y_m": 0.5, "zone": "hub"},
            ]
        ),
        route_requirements=pd.DataFrame(
            [
                {"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True, "measurement_required": False, "notes": "Abastecer produto 1"},
            ]
        ),
    )
    candidate = {
        "installed_link_ids": ["L1", "L2", "L3"],
        "installed_links": {
            "L1": {"from_node": "W", "to_node": "HS", "archetype": "star_tap"},
            "L2": {"from_node": "HS", "to_node": "HD", "archetype": "star_trunk"},
            "L3": {"from_node": "HD", "to_node": "P1", "archetype": "star_tap"},
        },
    }
    metrics = {"route_metrics": [{"route_id": "R001", "feasible": True, "path_link_ids": ["L1", "L2", "L3"]}]}

    payload = build_render_payload(candidate, bundle, metrics)
    element_ids = {element["data"]["id"] for element in payload["cytoscape_elements"]}
    node_labels = {
        element["data"]["id"]: element["data"].get("label")
        for element in payload["cytoscape_elements"]
        if "source" not in element["data"]
    }

    assert "W" in element_ids
    assert "P1" in element_ids
    assert "route:R001" in element_ids
    assert "P3" not in element_ids
    assert "HS" not in element_ids
    assert "HD" not in element_ids
    assert "L1" not in element_ids
    assert node_labels["W"] == "Tanque de agua"
    assert payload["route_highlights"]["R001"] == ["L1", "L2", "L3"]


def test_audit_bundle_panel_preserves_technical_space_but_explains_next_step() -> None:
    panel = render_bundle_io_panel(
        {
            "status": "idle",
            "bundle_version": "2026.04",
            "canonical_scenario_root": "data/decision_platform/maquete_v2",
            "bundle_manifest": "data/decision_platform/maquete_v2/scenario_bundle.yaml",
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Bundle canônico pronto para auditoria e persistência." in panel_text
    assert "Pronto" in panel_text
    assert "Objetivo desta área" in panel_text
    assert "Estado do bundle" in panel_text
    assert "Próxima ação" in panel_text
    assert "Use este espaço quando precisar salvar, reabrir ou reconciliar o bundle canônico" in panel_text
    assert _component_id_is_inside_details(panel, "bundle-io-address-list") is True


def test_audit_workspace_panel_relegates_auditoria_to_advanced_path() -> None:
    panel = render_audit_workspace_panel(
        {
            "status": "idle",
            "bundle_version": "2026.04",
            "bundle_manifest": "data/decision_platform/maquete_v2/scenario_bundle.yaml",
        },
        {
            "selected_candidate_id": "cand-01",
            "error": None,
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Trilha avançada" in panel_text
    assert "O que esta área resolve" in panel_text
    assert "Estado atual" in panel_text
    assert "Quando entrar aqui" in panel_text
    assert "Quando não entrar aqui" in panel_text
    assert "não bastar para reconciliar bundle" in panel_text.lower()
    assert getattr(_find_component_by_id(panel, "audit-workspace-return-primary-link"), "href", None) == "?tab=decision"
    assert getattr(_find_component_by_id(panel, "audit-workspace-open-studio-link"), "href", None) == "?tab=studio"


def test_studio_projection_panel_explains_business_layer_boundary() -> None:
    panel = render_studio_projection_panel(
        {
            "status": "partial",
            "headline": "Projeção de negócio parcial",
            "projected_route_count": 2,
            "route_metadata_count": 3,
            "covered_node_count": 2,
            "business_node_count": 4,
            "guidance": ["A visualização principal cobre parte do cenário e esconde a malha interna por design."],
            "uncovered_nodes": ["Misturador"],
            "invalid_routes": [],
            "technical_trail_message": "Campos avançados do Studio e Auditoria guardam a estrutura técnica completa sem recolocar nós internos na superfície principal.",
        }
    )
    panel_text = _collect_text_content(panel)

    assert "Objetivo desta área" in panel_text
    assert "Quando abrir Auditoria" in panel_text
    assert "Rotas declaradas" in panel_text
    assert "Entidades sem rota projetada: Misturador" in panel_text


def test_audit_tab_holds_bundle_editors_and_technical_surfaces() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    audit_tab = _find_tab_by_label(app.layout, "Auditoria")
    assert audit_tab is not None
    assert _find_component_by_id(audit_tab, "audit-workspace-panel") is not None
    assert _find_component_by_id(audit_tab, "audit-context-detailed-panels") is not None
    assert _find_component_by_id(audit_tab, "bundle-io-summary-panel") is not None
    assert _find_component_by_id(audit_tab, "topology-rules-editor") is not None
    assert _find_component_by_id(audit_tab, "scenario-settings-editor") is not None
    assert _find_component_by_id(audit_tab, "nodes-grid") is not None
    assert _find_component_by_id(audit_tab, "audit-bundle-tables-details") is not None


def test_primary_tabs_keep_debug_json_in_progressive_disclosure() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    for component_id in [
        "node-studio-summary",
        "edge-studio-summary",
        "run-jobs-summary",
        "run-job-detail",
        "execution-summary",
        "selected-candidate-summary",
        "official-candidate-summary",
        "candidate-breakdown",
        "catalog-state-summary",
        "bundle-io-summary",
    ]:
        assert _component_id_is_inside_details(app.layout, component_id) is True


@pytest.mark.slow
def test_dash_app_uses_pipeline_result_when_fallback_is_allowed(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    scenario_dir = maquete_v2_fallback_runtime["scenario_dir"]
    result = maquete_v2_fallback_runtime["result"]
    with diagnostic_runtime_test_mode():
        app = build_app(scenario_dir)
    assert hasattr(app, "layout")
    assert app.layout is not None
    detail = build_candidate_detail(result, result["selected_candidate_id"])
    assert "breakdown" in detail
    assert detail["summary"]["candidate_id"] == result["selected_candidate_id"]
    assert detail["route_rows"]


@pytest.mark.slow
def test_ui_view_state_uses_official_selected_candidate_instead_of_catalog_first(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    manipulated = {**result, "catalog": list(reversed(result["catalog"]))}
    view_state = build_catalog_view_state(
        manipulated,
        profile_id=manipulated["default_profile_id"],
    )
    detail = build_candidate_detail(result, view_state["selected_candidate_id"])
    assert view_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert view_state["selected_candidate_id"] != manipulated["catalog"][0]["candidate_id"]
    assert detail["cytoscape_elements"] == result["selected_candidate"]["render"]["cytoscape_elements"]
    assert detail["summary"]["generation_source"] == result["selected_candidate"]["generation_source"]


@pytest.mark.slow
def test_ui_save_reopen_flow_persists_bundle_and_refreshes_pipeline() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_save_reopen_source",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_save_reopen_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)
        nodes_rows = bundle.nodes.to_dict("records")
        components_rows = bundle.components.to_dict("records")
        candidate_links_rows = bundle.candidate_links.to_dict("records")
        edge_component_rules_rows = bundle.edge_component_rules.to_dict("records")
        route_rows = bundle.route_requirements.to_dict("records")
        layout_constraints_rows = bundle.layout_constraints.to_dict("records")
        nodes_rows[0]["label"] = "W salvo na UI"
        components_rows[0]["cost"] = 321.0
        candidate_links_rows[0]["notes"] = "Tap salvo na UI"
        edge_component_rules_rows[0]["max_series_pumps"] = 1
        route_rows[0]["weight"] = 55.0
        layout_constraints_rows[0]["value"] = 1.5
        topology_rules = {
            **bundle.topology_rules,
            "families": {
                **bundle.topology_rules["families"],
                "hybrid_free": {
                    **bundle.topology_rules["families"]["hybrid_free"],
                    "max_active_pumps_per_route": 3,
                },
            },
        }
        scenario_settings = bundle.scenario_settings | {
            "ui": {
                **bundle.scenario_settings.get("ui", {}),
                "default_layout_mode": "save_reopen_ui",
            }
        }

        with diagnostic_runtime_test_mode():
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=nodes_rows,
                components_rows=components_rows,
                candidate_links_rows=candidate_links_rows,
                edge_component_rules_rows=edge_component_rules_rows,
                route_rows=route_rows,
                layout_constraints_rows=layout_constraints_rows,
                topology_rules_text=yaml.safe_dump(topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
            )

        assert saved["scenario_dir"] == str(output_dir.resolve())
        assert saved["bundle"].nodes.iloc[0]["label"] == "W salvo na UI"
        assert float(saved["bundle"].components.iloc[0]["cost"]) == 321.0
        assert saved["bundle"].candidate_links.iloc[0]["notes"] == "Tap salvo na UI"
        assert int(saved["bundle"].edge_component_rules.iloc[0]["max_series_pumps"]) == 1
        assert float(saved["bundle"].route_requirements.iloc[0]["weight"]) == 55.0
        assert float(saved["bundle"].layout_constraints.iloc[0]["value"]) == 1.5
        assert saved["bundle"].topology_rules["families"]["hybrid_free"]["max_active_pumps_per_route"] == 3
        assert saved["bundle"].scenario_settings["ui"]["default_layout_mode"] == "save_reopen_ui"
        assert saved["bundle"].scenario_settings["storage"]["bundle_manifest"] == "scenario_bundle.yaml"
        assert saved["bundle"].scenario_settings["storage"]["component_catalog"] == "component_catalog.csv"
        assert saved["result"] is not None
        assert saved["result"]["scenario_bundle_root"] == str(output_dir.resolve())
        assert saved["result"]["scenario_bundle_version"] == saved["bundle"].bundle_version
        assert saved["result"]["scenario_bundle_files"]["components.csv"] == "component_catalog.csv"
        assert saved["result"]["scenario_provenance"]["requested_dir_matches_bundle_root"] is True
        assert saved["bundle_io_summary"]["canonical_scenario_root"] == str(output_dir.resolve())
        assert saved["bundle_io_summary"]["requested_output_dir"] == str(output_dir.resolve())
        assert saved["bundle_io_summary"]["requested_dir_matches_bundle_root"] is True
        assert saved["bundle_io_summary"]["execution_scenario_provenance"]["scenario_root"] == str(output_dir.resolve())
        assert saved["pipeline_error"] is None
    finally:
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_ui_save_reopen_rejects_legacy_source_without_manifest() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_save_reopen_legacy_source",
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_save_reopen_legacy_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)
        (Path(scenario_dir) / "scenario_bundle.yaml").unlink()

        with pytest.raises(OfficialRuntimeConfigError, match="Decision Platform UI save/reopen requires a canonical scenario bundle"):
            save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=bundle.nodes.to_dict("records"),
                components_rows=bundle.components.to_dict("records"),
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(
                    bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )

        assert not output_dir.exists()
    finally:
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_ui_save_reopen_fails_closed_without_partial_bundle_when_storage_mapping_diverges() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_save_reopen_invalid_storage",
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_save_reopen_invalid_storage_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)
        scenario_settings = {
            **bundle.scenario_settings,
            "storage": {
                **bundle.scenario_settings["storage"],
                "component_catalog": "components.csv",
            },
        }

        with pytest.raises(ValueError, match="canonical component catalog filename"):
            save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=bundle.nodes.to_dict("records"),
                components_rows=bundle.components.to_dict("records"),
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(scenario_settings, sort_keys=False, allow_unicode=True),
            )

        assert not (output_dir / "scenario_bundle.yaml").exists()
        assert not (output_dir / "component_catalog.csv").exists()
    finally:
        cleanup_scenario_copy(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.slow
def test_ui_rebuilds_from_saved_bundle_after_source_cleanup() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_rebuild_saved_bundle",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_rebuild_saved_bundle")
    try:
        bundle = load_scenario_bundle(scenario_dir)

        with diagnostic_runtime_test_mode():
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=bundle.nodes.to_dict("records"),
                components_rows=bundle.components.to_dict("records"),
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(
                    bundle.scenario_settings,
                    sort_keys=False,
                    allow_unicode=True,
                ),
            )

        cleanup_scenario_copy(scenario_dir)
        scenario_dir = None

        with diagnostic_runtime_test_mode():
            app = build_app(saved["scenario_dir"])

        assert hasattr(app, "layout")
        assert app.layout is not None
        assert saved["scenario_dir"] == str(output_dir.resolve())
        assert load_scenario_bundle(saved["scenario_dir"]).bundle_manifest_path is not None
        execution_summary = _find_component_by_id(app.layout, "execution-summary")
        assert execution_summary is not None
        summary_payload = json.loads(execution_summary.children)
        assert summary_payload["scenario_bundle_root"] == str(output_dir.resolve())
        assert summary_payload["scenario_provenance"]["requested_dir_matches_bundle_root"] is True
    finally:
        if scenario_dir is not None and Path(scenario_dir).exists():
            cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_studio_callbacks_fail_closed_for_invalid_structural_actions() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    delete_node_callback = _get_callback(app, input_id="node-studio-delete-button")
    apply_edge_callback = _get_callback(app, input_id="edge-studio-apply-button")

    nodes_rows = bundle.nodes.to_dict("records")
    candidate_links_rows = bundle.candidate_links.to_dict("records")
    route_rows = bundle.route_requirements.to_dict("records")
    edge_component_rules_rows = bundle.edge_component_rules.to_dict("records")

    next_nodes_rows, next_selected_node_id, node_status = delete_node_callback(
        1,
        nodes_rows,
        "P1",
        candidate_links_rows,
        route_rows,
    )
    assert next_nodes_rows == nodes_rows
    assert next_selected_node_id == "P1"
    assert "requires explicit reconciliation" in node_status

    next_links_rows, next_selected_link_id, edge_status = apply_edge_callback(
        1,
        candidate_links_rows,
        "L013",
        "L013_INVALID",
        "J1",
        "UNKNOWN_NODE",
        "vertical_link",
        0.33,
        [],
        "loop",
        nodes_rows,
        edge_component_rules_rows,
    )
    assert next_links_rows == candidate_links_rows
    assert next_selected_link_id == "L013"
    assert "references unknown nodes" in edge_status


@pytest.mark.fast
def test_ui_save_reopen_callback_rejects_legacy_layout_without_manifest() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_callback_legacy_source",
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_callback_legacy_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)
        (Path(scenario_dir) / "scenario_bundle.yaml").unlink()

        with diagnostic_runtime_test_mode():
            app = build_app(scenario_dir)

        save_callback = _get_callback(app, input_id="save-reopen-bundle-button")
        callback_result = save_callback(
            1,
            str(scenario_dir),
            str(output_dir),
            bundle.nodes.to_dict("records"),
            bundle.components.to_dict("records"),
            bundle.candidate_links.to_dict("records"),
            bundle.edge_component_rules.to_dict("records"),
            bundle.route_requirements.to_dict("records"),
            bundle.layout_constraints.to_dict("records"),
            yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
            yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True),
        )
        bundle_io_summary = json.loads(callback_result[1])
        execution_summary = json.loads(callback_result[10])

        assert callback_result[0] == str(scenario_dir)
        assert bundle_io_summary["status"] == "error"
        assert "canonical scenario bundle" in bundle_io_summary["error"]
        assert execution_summary["error"] == bundle_io_summary["error"]
        assert not output_dir.exists()
    finally:
        cleanup_scenario_copy(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.slow
def test_studio_callbacks_round_trip_structural_edits_through_ui_flow() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_ui_callback_structural_source",
        scenario_overrides={
            "candidate_generation": {
                "population_size": 12,
                "generations": 3,
                "keep_top_n_per_family": 6,
            },
            "hydraulic_engine": {"fallback": "python_emulated_julia"},
        },
    )
    created_output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_callback_structural_created")
    final_output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_callback_structural_final")
    try:
        with diagnostic_runtime_test_mode():
            app = build_app(scenario_dir)

        bundle = load_scenario_bundle(scenario_dir)
        create_node_callback = _get_callback(app, input_id="node-studio-create-button")
        quick_move_callback = _get_callback(app, input_id="studio-focus-recommended-move-right-button")
        quick_duplicate_node_callback = _get_callback(app, input_id="studio-focus-duplicate-node-button")
        apply_node_callback = _get_callback(app, input_id="node-studio-apply-button")
        delete_node_callback = _get_callback(app, input_id="node-studio-delete-button")
        sync_node_callback = _get_callback(app, output_prefix="..node-studio-selected-id.data")
        create_edge_callback = _get_callback(app, input_id="edge-studio-create-button")
        apply_edge_callback = _get_callback(app, input_id="edge-studio-apply-button")
        quick_delete_edge_callback = _get_callback(app, input_id="studio-focus-recommended-delete-edge-button")
        open_workbench_callback = _get_callback(app, input_id="studio-focus-open-workbench-button")
        sync_edge_callback = _get_callback(app, output_prefix="..edge-studio-selected-id.data")
        refresh_studio_elements_callback = _get_callback(app, output_prefix="node-studio-elements-store.data")
        refresh_studio_callback = _get_callback(app, output_prefix="..node-studio-cytoscape.stylesheet")
        save_callback = _get_callback(app, input_id="save-reopen-bundle-button")

        nodes_rows = bundle.nodes.to_dict("records")
        candidate_links_rows = bundle.candidate_links.to_dict("records")
        edge_component_rules_rows = bundle.edge_component_rules.to_dict("records")
        route_rows = bundle.route_requirements.to_dict("records")
        layout_constraints_rows = bundle.layout_constraints.to_dict("records")
        components_rows = bundle.components.to_dict("records")
        topology_rules_text = yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True)
        scenario_settings_text = yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True)

        nodes_rows, created_node_id, status = create_node_callback(1, nodes_rows, "J4")
        assert status == ""
        synced_created_node = sync_node_callback(nodes_rows, {"id": created_node_id}, "J4")
        assert synced_created_node[0] == created_node_id
        assert synced_created_node[1] == created_node_id

        nodes_rows, created_node_id, status = apply_node_callback(
            1,
            nodes_rows,
            created_node_id,
            created_node_id,
            "Studio callback node",
            "junction",
            0.81,
            0.28,
            ["allow_inbound"],
            ["allow_outbound"],
            candidate_links_rows,
            route_rows,
        )
        assert status == ""

        nodes_rows, moved_node_id, status = quick_move_callback(
            0,
            1,
            0,
            0,
            0,
            0,
            nodes_rows,
            created_node_id,
            "right",
            0.02,
        )
        assert status == ""
        moved_row = next(row for row in nodes_rows if row["node_id"] == created_node_id)
        assert moved_node_id == created_node_id
        assert moved_row["x_m"] == pytest.approx(0.83)

        nodes_rows, duplicated_node_id, status = quick_duplicate_node_callback(0, 1, nodes_rows, created_node_id)
        assert status == ""
        synced_duplicated_node = sync_node_callback(nodes_rows, {"id": duplicated_node_id}, created_node_id)
        assert synced_duplicated_node[0] == duplicated_node_id
        assert synced_duplicated_node[2].endswith("copia")

        candidate_links_rows, created_link_id, status = create_edge_callback(
            1,
            candidate_links_rows,
            "L013",
            created_node_id,
            duplicated_node_id,
            "vertical_link",
            0.19,
            [],
            "loop,hybrid",
            nodes_rows,
            edge_component_rules_rows,
        )
        assert status == ""
        synced_created_edge = sync_edge_callback(candidate_links_rows, {"link_id": created_link_id}, "L013")
        assert synced_created_edge[0] == created_link_id
        assert synced_created_edge[2] == created_node_id
        assert synced_created_edge[3] == duplicated_node_id

        candidate_links_rows, created_link_id, status = apply_edge_callback(
            1,
            candidate_links_rows,
            created_link_id,
            f"{created_link_id}_EDITED",
            created_node_id,
            duplicated_node_id,
            "upper_bypass_segment",
            0.27,
            ["bidirectional"],
            "loop",
            nodes_rows,
            edge_component_rules_rows,
        )
        assert status == ""

        elements = refresh_studio_elements_callback(
            nodes_rows,
            candidate_links_rows,
            route_rows,
            {"source_node_id": created_node_id, "sink_node_id": duplicated_node_id, "intent": "mandatory"},
        )
        _, node_summary_text, edge_summary_text, studio_status = refresh_studio_callback(
            elements,
            nodes_rows,
            candidate_links_rows,
            route_rows,
            created_node_id,
            created_link_id,
            status,
        )
        node_summary = json.loads(node_summary_text)
        edge_summary = json.loads(edge_summary_text)
        assert studio_status == ""
        visible_primary_node_ids = {element["data"].get("id") for element in elements if "source" not in element["data"]}
        assert created_node_id not in visible_primary_node_ids
        assert duplicated_node_id not in visible_primary_node_ids
        assert node_summary["selected_node_id"] != created_node_id
        assert edge_summary["selected_link_id"] == created_link_id
        assert any(str(element["data"].get("id", "")).startswith("route:") for element in elements if "source" in element["data"])
        assert open_workbench_callback(0, 0, 0, 0, 1) is True

        created_callback_result = save_callback(
            1,
            str(scenario_dir),
            str(created_output_dir),
            nodes_rows,
            components_rows,
            candidate_links_rows,
            edge_component_rules_rows,
            route_rows,
            layout_constraints_rows,
            topology_rules_text,
            scenario_settings_text,
        )
        created_bundle_summary = json.loads(created_callback_result[1])
        created_execution_summary = json.loads(created_callback_result[10])
        assert created_callback_result[0] == str(created_output_dir.resolve())
        assert created_bundle_summary["bundle_files"]["components.csv"] == "component_catalog.csv"
        assert created_bundle_summary["requested_dir_matches_bundle_root"] is True
        assert created_execution_summary["error"] is None
        assert created_execution_summary["scenario_bundle_manifest"].endswith("scenario_bundle.yaml")
        assert created_execution_summary["scenario_provenance"]["requested_dir_matches_bundle_root"] is True

        created_bundle = load_scenario_bundle(created_output_dir)
        assert created_node_id in created_bundle.nodes["node_id"].tolist()
        assert duplicated_node_id in created_bundle.nodes["node_id"].tolist()
        assert created_link_id in created_bundle.candidate_links["link_id"].tolist()

        blocked_delete_rows, blocked_selected_node_id, blocked_delete_status = delete_node_callback(
            1,
            created_callback_result[2],
            created_node_id,
            created_callback_result[4],
            created_callback_result[6],
        )
        assert blocked_delete_rows == created_callback_result[2]
        assert blocked_selected_node_id == created_node_id
        assert "requires explicit reconciliation" in blocked_delete_status

        candidate_links_rows, next_edge_selected_id, status = quick_delete_edge_callback(
            0,
            1,
            0,
            created_callback_result[4],
            created_link_id,
        )
        assert status == ""
        assert next_edge_selected_id != created_link_id
        nodes_rows, next_selected_node_id, status = delete_node_callback(
            1,
            created_callback_result[2],
            duplicated_node_id,
            candidate_links_rows,
            created_callback_result[6],
        )
        assert status == ""
        assert next_selected_node_id != duplicated_node_id
        nodes_rows, next_selected_node_id, status = delete_node_callback(
            1,
            nodes_rows,
            created_node_id,
            candidate_links_rows,
            created_callback_result[6],
        )
        assert status == ""
        assert next_selected_node_id != created_node_id

        final_callback_result = save_callback(
            1,
            created_callback_result[0],
            str(final_output_dir),
            nodes_rows,
            created_callback_result[3],
            candidate_links_rows,
            created_callback_result[5],
            created_callback_result[6],
            created_callback_result[7],
            created_callback_result[8],
            created_callback_result[9],
        )
        final_bundle_summary = json.loads(final_callback_result[1])
        final_execution_summary = json.loads(final_callback_result[10])
        assert final_callback_result[0] == str(final_output_dir.resolve())
        assert final_bundle_summary["bundle_files"]["components.csv"] == "component_catalog.csv"
        assert final_execution_summary["error"] is None
        assert final_execution_summary["scenario_bundle_root"] == str(final_output_dir.resolve())

        final_bundle = load_scenario_bundle(final_output_dir)
        assert created_node_id not in final_bundle.nodes["node_id"].tolist()
        assert duplicated_node_id not in final_bundle.nodes["node_id"].tolist()
        assert created_link_id not in final_bundle.candidate_links["link_id"].tolist()
    finally:
        cleanup_scenario_copy(final_output_dir)
        cleanup_scenario_copy(created_output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_primary_node_studio_elements_use_business_labels_and_hide_internal_nodes() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    elements = build_primary_node_studio_elements(
        bundle.nodes.to_dict("records"),
        bundle.candidate_links.to_dict("records"),
        bundle.route_requirements.to_dict("records"),
    )

    node_ids = {element["data"]["id"] for element in elements if "source" not in element["data"]}
    route_ids = {element["data"]["id"] for element in elements if "source" in element["data"]}
    water_node = next(element for element in elements if element["data"].get("id") == "W")
    supply_route = next(element for element in elements if element["data"].get("id") == "route:R001")

    assert node_ids.isdisjoint({"HS", "HD", "J1", "J2", "J3", "J4", "U1", "U2", "U3"})
    assert water_node["data"]["label"] == "Tanque de água"
    assert ":" not in water_node["data"]["label"]
    assert "route:R001" in route_ids
    assert "route:R009" in route_ids
    assert supply_route["data"]["label"] == "Água para misturador"
    assert supply_route["data"]["source"] == "W"
    assert supply_route["data"]["target"] == "M"


@pytest.mark.fast
def test_studio_projection_summary_reports_complete_partial_and_degraded_states() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    nodes_rows = bundle.nodes.to_dict("records")
    candidate_links_rows = bundle.candidate_links.to_dict("records")
    route_rows = bundle.route_requirements.to_dict("records")

    complete = build_studio_projection_summary(nodes_rows, candidate_links_rows, route_rows)
    partial = build_studio_projection_summary(
        nodes_rows,
        candidate_links_rows,
        [row for row in route_rows if str(row["route_id"]) not in {"R001", "R002", "R003", "R009"}],
    )
    degraded = build_studio_projection_summary(nodes_rows, candidate_links_rows, [])

    assert complete["status"] == "complete"
    assert complete["projected_route_count"] == len(route_rows)
    assert partial["status"] == "partial"
    assert "Tanque de água" in partial["uncovered_nodes"]
    assert degraded["status"] == "degraded"
    assert degraded["projected_route_count"] == 0
    assert "Auditoria" in degraded["technical_trail_message"]


@pytest.mark.fast
def test_node_studio_helpers_update_layout_and_properties() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    nodes_rows = bundle.nodes.to_dict("records")
    moved_rows, selected_id = move_node_studio_selection(
        nodes_rows,
        selected_node_id="W",
        direction="right",
        step=0.05,
    )
    edited_rows, edited_selected_id = apply_node_studio_edit(
        moved_rows,
        selected_node_id=selected_id,
        node_id="W_STUDIO",
        label="Tanque movido",
        node_type="water_tank",
        x_m=0.12,
        y_m=0.33,
        allow_inbound=False,
        allow_outbound=True,
    )
    elements = build_node_studio_elements(edited_rows, bundle.candidate_links.to_dict("records"))

    selected_row = next(row for row in edited_rows if row["node_id"] == "W_STUDIO")
    selected_node = next(element for element in elements if element["data"].get("id") == "W_STUDIO")
    assert edited_selected_id == "W_STUDIO"
    assert selected_row["label"] == "Tanque movido"
    assert float(selected_row["x_m"]) == 0.12
    assert float(selected_row["y_m"]) == 0.33
    assert bool(selected_row["allow_inbound"]) is False
    assert bool(selected_row["allow_outbound"]) is True
    assert selected_node["position"]["x"] == 120.0
    assert selected_node["position"]["y"] == 198.0


@pytest.mark.fast
def test_node_studio_rejects_node_rename_with_unreconciled_references() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")

    with pytest.raises(ValueError, match="requires explicit reconciliation"):
        apply_node_studio_edit(
            bundle.nodes.to_dict("records"),
            selected_node_id="P1",
            node_id="P1_RENAMED",
            label="Produto 1 renomeado",
            node_type="product_tank",
            x_m=0.15,
            y_m=0.08,
            allow_inbound=True,
            allow_outbound=True,
            candidate_links_rows=bundle.candidate_links.to_dict("records"),
            route_rows=bundle.route_requirements.to_dict("records"),
        )


@pytest.mark.fast
def test_edge_studio_helpers_update_link_properties() -> None:
    bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    edited_links, selected_link_id = apply_edge_studio_edit(
        bundle.candidate_links.to_dict("records"),
        selected_link_id="L013",
        link_id="L013_STUDIO",
        from_node="J1",
        to_node="J2",
        archetype="upper_bypass_segment",
        length_m=0.44,
        bidirectional=False,
        family_hint="loop",
        nodes_rows=bundle.nodes.to_dict("records"),
        edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
    )
    elements = build_node_studio_elements(bundle.nodes.to_dict("records"), edited_links)

    selected_edge = next(row for row in edited_links if row["link_id"] == "L013_STUDIO")
    selected_element = next(element for element in elements if element["data"].get("id") == "L013_STUDIO")
    assert selected_link_id == "L013_STUDIO"
    assert selected_edge["archetype"] == "upper_bypass_segment"
    assert float(selected_edge["length_m"]) == 0.44
    assert bool(selected_edge["bidirectional"]) is False
    assert selected_edge["family_hint"] == "loop"
    assert selected_element["data"]["source"] == "J1"
    assert selected_element["data"]["target"] == "J2"
    assert selected_element["data"]["label"] == "L013_STUDIO: upper_bypass_segment"


@pytest.mark.slow
def test_node_studio_round_trip_persists_visual_node_edits() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_node_studio_round_trip",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_node_studio_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)
        nodes_rows, selected_id = move_node_studio_selection(
            bundle.nodes.to_dict("records"),
            selected_node_id="P1",
            direction="down",
            step=0.04,
        )
        nodes_rows, selected_id = apply_node_studio_edit(
            nodes_rows,
            selected_node_id=selected_id,
            label="Produto 1 studio",
            node_type="product_tank",
            x_m=0.21,
            y_m=0.17,
            allow_inbound=True,
            allow_outbound=True,
        )

        with diagnostic_runtime_test_mode():
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=nodes_rows,
                components_rows=bundle.components.to_dict("records"),
                candidate_links_rows=bundle.candidate_links.to_dict("records"),
                edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )

        saved_row = saved["bundle"].nodes.loc[saved["bundle"].nodes["node_id"] == "P1"].iloc[0]
        assert saved["scenario_dir"] == str(output_dir.resolve())
        assert saved_row["label"] == "Produto 1 studio"
        assert float(saved_row["x_m"]) == 0.21
        assert float(saved_row["y_m"]) == 0.17
        assert bool(saved_row["allow_outbound"]) is True
        assert saved["pipeline_error"] is None
    finally:
        cleanup_scenario_copy(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.slow
def test_edge_studio_round_trip_persists_visual_edge_edits() -> None:
    scenario_dir = prepare_scenario_copy(
        "data/decision_platform/maquete_v2",
        "maquete_v2_edge_studio_round_trip",
        scenario_overrides={"hydraulic_engine": {"fallback": "python_emulated_julia"}},
    )
    output_dir = prepare_isolated_tmp_dir("maquete_v2_edge_studio_saved")
    try:
        bundle = load_scenario_bundle(scenario_dir)
        candidate_links_rows, selected_link_id = apply_edge_studio_edit(
            bundle.candidate_links.to_dict("records"),
            selected_link_id="L013",
            link_id="L013_STUDIO",
            from_node="J1",
            to_node="U1",
            archetype="vertical_link",
            length_m=0.41,
            bidirectional=False,
            family_hint="loop,hybrid",
            nodes_rows=bundle.nodes.to_dict("records"),
            edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
        )

        with diagnostic_runtime_test_mode():
            saved = save_and_reopen_local_bundle(
                current_scenario_dir=scenario_dir,
                output_dir=output_dir,
                nodes_rows=bundle.nodes.to_dict("records"),
                components_rows=bundle.components.to_dict("records"),
                candidate_links_rows=candidate_links_rows,
                edge_component_rules_rows=bundle.edge_component_rules.to_dict("records"),
                route_rows=bundle.route_requirements.to_dict("records"),
                layout_constraints_rows=bundle.layout_constraints.to_dict("records"),
                topology_rules_text=yaml.safe_dump(bundle.topology_rules, sort_keys=False, allow_unicode=True),
                scenario_settings_text=yaml.safe_dump(bundle.scenario_settings, sort_keys=False, allow_unicode=True),
            )

        saved_row = saved["bundle"].candidate_links.loc[saved["bundle"].candidate_links["link_id"] == "L013_STUDIO"].iloc[0]
        assert selected_link_id == "L013_STUDIO"
        assert saved["scenario_dir"] == str(output_dir.resolve())
        assert saved_row["from_node"] == "J1"
        assert saved_row["to_node"] == "U1"
        assert saved_row["archetype"] == "vertical_link"
        assert float(saved_row["length_m"]) == 0.41
        assert bool(saved_row["bidirectional"]) is False
        assert saved_row["family_hint"] == "loop,hybrid"
        assert saved["pipeline_error"] is None
    finally:
        cleanup_scenario_copy(output_dir)
        cleanup_scenario_copy(scenario_dir)


@pytest.mark.fast
def test_ui_save_reopen_reports_fail_closed_probe_override_on_official_bundle(monkeypatch) -> None:
    monkeypatch.setenv("DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE", "1")
    source_bundle = load_scenario_bundle("data/decision_platform/maquete_v2")
    output_dir = prepare_isolated_tmp_dir("maquete_v2_ui_probe_override_saved")
    try:
        saved = save_and_reopen_local_bundle(
            current_scenario_dir="data/decision_platform/maquete_v2",
            output_dir=output_dir,
            nodes_rows=source_bundle.nodes.to_dict("records"),
            components_rows=source_bundle.components.to_dict("records"),
            candidate_links_rows=source_bundle.candidate_links.to_dict("records"),
            edge_component_rules_rows=source_bundle.edge_component_rules.to_dict("records"),
            route_rows=source_bundle.route_requirements.to_dict("records"),
            layout_constraints_rows=source_bundle.layout_constraints.to_dict("records"),
            topology_rules_text=yaml.safe_dump(source_bundle.topology_rules, sort_keys=False, allow_unicode=True),
            scenario_settings_text=yaml.safe_dump(source_bundle.scenario_settings, sort_keys=False, allow_unicode=True),
        )

        assert saved["result"] is None
        assert "invalid for the official Julia-only gate" in saved["pipeline_error"]
        assert saved["bundle_io_summary"]["canonical_scenario_root"] == str(output_dir.resolve())
        assert saved["bundle_io_summary"]["execution_scenario_provenance"] is None
    finally:
        cleanup_scenario_copy(output_dir)


@pytest.mark.slow
def test_catalog_filters_include_quality_resilience_flow_and_fallback(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    ranked = rerank_catalog(result, "balanced")
    filtered = filter_catalog_records(
        ranked,
        family="ALL",
        feasible_only=True,
        max_cost=1000,
        min_quality=50,
        min_flow=5,
        min_resilience=10,
        min_cleaning=0,
        min_operability=0,
        top_n_per_family=2,
        fallback_filter="WITH_FALLBACK",
    )
    assert filtered
    assert all(record["feasible"] for record in filtered)
    assert all(float(record["quality_score_raw"]) >= 50 for record in filtered)
    assert all(float(record["flow_out_score"]) >= 5 for record in filtered)
    assert all(float(record["resilience_score"]) >= 10 for record in filtered)
    assert all(int(record["fallback_component_count"]) > 0 for record in filtered)


@pytest.mark.slow
def test_catalog_filters_include_infeasibility_reason_and_family_summary(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    ranked = rerank_catalog(result, "balanced")
    target_reason = next(
        str(record["infeasibility_reason"])
        for record in ranked
        if record.get("infeasibility_reason") not in (None, "")
    )
    filtered = filter_catalog_records(
        ranked,
        infeasibility_reason=target_reason,
    )
    view_state = build_catalog_view_state(
        result,
        profile_id=result["default_profile_id"],
        infeasibility_reason=target_reason,
    )
    assert filtered
    assert all(str(record["infeasibility_reason"]) == target_reason for record in filtered)
    assert view_state["family_summary_records"]
    assert all("viability_rate" in row for row in view_state["family_summary_records"])


@pytest.mark.slow
def test_reranking_changes_visible_selected_candidate_when_weights_change(
    maquete_v2_fallback_runtime: dict[str, object],
) -> None:
    result = maquete_v2_fallback_runtime["result"]
    default_state = build_catalog_view_state(result, profile_id=result["default_profile_id"])
    reranked_state = build_catalog_view_state(
        result,
        profile_id=result["default_profile_id"],
        weight_overrides={
            "cost_weight": 1.0,
            "quality_weight": 0.0,
            "flow_weight": 0.0,
            "resilience_weight": 0.0,
            "cleaning_weight": 0.0,
            "operability_weight": 0.0,
        },
    )
    assert default_state["selected_candidate_id"] == result["selected_candidate_id"]
    assert reranked_state["selected_candidate_id"] == reranked_state["ranked_records"][0]["candidate_id"]


@pytest.mark.slow
def test_ui_summary_and_comparison_records_expose_decision_fields(maquete_v2_fallback_runtime: dict[str, object]) -> None:
    result = maquete_v2_fallback_runtime["result"]
    official = build_official_candidate_summary(
        result,
        profile_id=result["default_profile_id"],
        candidate_id=result["selected_candidate_id"],
    )
    comparison = build_comparison_records(
        result,
        [record["candidate_id"] for record in result["ranked_profiles"]["balanced"][:2]],
        profile_id=result["default_profile_id"],
        active_selected_id=result["selected_candidate_id"],
    )
    assert official["candidate_id"] == result["selected_candidate_id"]
    assert "critical_routes" in official
    assert "winner_reason_summary" in official
    assert official["runner_up_candidate_id"] == result["ranked_profiles"]["balanced"][1]["candidate_id"]
    assert comparison
    assert any(row["comparison_role"] in {"official,selected", "official"} for row in comparison)
    assert all("score_final" in row for row in comparison)
