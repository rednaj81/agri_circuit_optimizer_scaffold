from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest
import yaml

from decision_platform.api.run_pipeline import OfficialRuntimeConfigError
from decision_platform.data_io.loader import load_scenario_bundle
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
    render_candidate_breakdown_panel,
    render_candidate_summary_panel,
    render_decision_contrast_panel,
    render_decision_signal_panel,
    render_decision_summary_panel,
    render_execution_summary_panel,
    render_run_job_detail_panel,
    render_runs_flow_panel,
    render_studio_connectivity_panel,
    render_studio_readiness_panel,
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


def test_studio_tab_surfaces_readiness_and_selection_context() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    studio_tab = _find_tab_by_label(app.layout, "Studio")
    assert studio_tab is not None
    assert _find_component_by_id(studio_tab, "studio-readiness-panel") is not None
    assert _find_component_by_id(studio_tab, "studio-status-banner") is not None
    assert _find_component_by_id(studio_tab, "studio-projection-coverage-panel") is not None
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

    assert open_guide_callback(1, False) is True
    assert open_navigation_callback("?tab=runs", 30, 20, 10, "studio") == "audit"
    assert open_navigation_callback("?tab=decision", 0, 40, 0, "studio") == "runs"
    assert open_navigation_callback("?tab=decision", 0, 40, 50, "runs") == "studio"
    assert open_navigation_callback("?tab=decision", 0, 0, 0, "studio") == "decision"


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
    assert _find_component_by_id(decision_tab, "decision-summary-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-contrast-panel") is not None
    assert _find_component_by_id(decision_tab, "decision-signal-panel") is not None
    assert _find_component_by_id(decision_tab, "compare-candidates-dropdown") is not None
    assert _find_component_by_id(decision_tab, "comparison-figure") is not None
    assert _find_component_by_id(decision_tab, "selected-candidate-dropdown") is not None
    assert _find_component_by_id(decision_tab, "candidate-breakdown-panel") is not None


def test_runs_tab_combines_queue_and_execution_summary() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    runs_tab = _find_tab_by_label(app.layout, "Runs")
    assert runs_tab is not None
    assert _find_component_by_id(runs_tab, "run-jobs-overview-panel") is not None
    assert _find_component_by_id(runs_tab, "runs-flow-panel") is not None
    assert _find_component_by_id(runs_tab, "execution-summary-panel") is not None
    assert _find_component_by_id(runs_tab, "runs-open-studio-button") is not None
    assert _find_component_by_id(runs_tab, "run-button") is not None


def test_studio_readiness_panel_surfaces_runs_transition_with_real_readiness() -> None:
    summary = build_studio_readiness_summary(
        nodes_rows=[{"node_id": "W"}, {"node_id": "P1"}],
        candidate_links_rows=[],
        route_rows=[{"route_id": "R001", "source": "W", "sink": "P1", "mandatory": True}],
    )
    panel = render_studio_readiness_panel(summary)
    panel_text = _collect_text_content(panel)

    assert "Passagem para Runs" in panel_text
    assert "bloqueios ou avisos" in panel_text.lower()
    assert _find_component_by_id(panel, "studio-open-runs-button") is not None


def test_studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas() -> None:
    panel = render_studio_connectivity_panel(
        {
            "blocker_count": 1,
            "warning_count": 2,
            "mandatory_route_count": 3,
            "measurement_route_count": 1,
            "next_steps": [
                "Corrigir bloqueios estruturais antes de enfileirar uma nova run.",
                "Salvar e reabrir o bundle canonico quando a revisao estiver pronta.",
            ],
        },
        [
            {"route_id": "R001", "source": "W", "sink": "M", "mandatory": True, "measurement_required": False},
            {"route_id": "R002", "source": "I", "sink": "M", "mandatory": True, "measurement_required": True},
        ],
    )
    panel_text = _collect_text_content(panel)

    assert "Conectividade do grafo" in panel_text
    assert "R001: W -> M (obrigatória)" in panel_text
    assert "R002: I -> M (obrigatória, medição direta)" in panel_text
    assert "Corrigir bloqueios estruturais" in panel_text


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
        },
    )
    panel_text = _collect_text_content(panel)

    assert "Passagem Studio -> Runs" in panel_text
    assert "Voltar ao Studio" in panel_text
    assert "run-003" in panel_text
    assert "conectividade" in panel_text.lower()


def test_primary_runs_panels_hide_raw_backend_keys_in_main_surface() -> None:
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
    detail_text = _collect_text_content(detail_panel)
    execution_text = _collect_text_content(execution_panel)

    assert "official_gate_valid:" not in detail_text
    assert "policy_mode:" not in detail_text
    assert "duracao_s:" not in detail_text
    assert "Erro operacional:" in execution_text
    assert "Próxima ação" in detail_text
    assert "Próxima ação" in execution_text


def test_primary_decision_panels_hide_raw_metric_keys_in_main_surface() -> None:
    decision_summary_panel = render_decision_summary_panel(
        {
            "candidate_id": "cand-01",
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
    assert "Runner-up e contraste" in contrast_text
    assert "cand-02" in contrast_text
    assert "Empate técnico" in contrast_text
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


def test_audit_tab_holds_bundle_editors_and_technical_surfaces() -> None:
    with diagnostic_runtime_test_mode():
        app = build_app("data/decision_platform/maquete_v2")

    audit_tab = _find_tab_by_label(app.layout, "Auditoria")
    assert audit_tab is not None
    assert _find_component_by_id(audit_tab, "bundle-io-summary-panel") is not None
    assert _find_component_by_id(audit_tab, "topology-rules-editor") is not None
    assert _find_component_by_id(audit_tab, "scenario-settings-editor") is not None
    assert _find_component_by_id(audit_tab, "nodes-grid") is not None


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
        duplicate_node_callback = _get_callback(app, input_id="node-studio-duplicate-button")
        apply_node_callback = _get_callback(app, input_id="node-studio-apply-button")
        delete_node_callback = _get_callback(app, input_id="node-studio-delete-button")
        sync_node_callback = _get_callback(app, output_prefix="..node-studio-selected-id.data")
        create_edge_callback = _get_callback(app, input_id="edge-studio-create-button")
        apply_edge_callback = _get_callback(app, input_id="edge-studio-apply-button")
        delete_edge_callback = _get_callback(app, input_id="edge-studio-delete-button")
        sync_edge_callback = _get_callback(app, output_prefix="..edge-studio-selected-id.data")
        refresh_studio_callback = _get_callback(app, output_prefix="..node-studio-cytoscape.elements")
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

        nodes_rows, duplicated_node_id, status = duplicate_node_callback(1, nodes_rows, created_node_id)
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

        elements, _, node_summary_text, edge_summary_text, studio_status = refresh_studio_callback(
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

        candidate_links_rows, next_edge_selected_id, status = delete_edge_callback(
            1,
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
