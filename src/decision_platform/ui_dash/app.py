from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from decision_platform.api.run_pipeline import OfficialRuntimeConfigError, run_decision_pipeline
from decision_platform.catalog.explanation import build_selected_candidate_explanation
from decision_platform.catalog.pipeline import resolve_selected_candidate
from decision_platform.data_io.loader import BUNDLE_MANIFEST_FILENAME, SCENARIO_BUNDLE_VERSION, load_scenario_bundle
from decision_platform.data_io.storage import bundle_authoring_payload, save_authored_scenario_bundle
from decision_platform.ranking.scoring import apply_dynamic_weights
from decision_platform.rendering.circuit import build_solution_comparison_figure
from decision_platform.ui_dash._compat import DASH_AVAILABLE, Dash, Input, Output, State, cyto, dag, dcc, html


def build_app(scenario_dir: str | Path = "data/decision_platform/maquete_v2") -> Dash:
    scenario_dir = _normalize_scenario_dir(scenario_dir)
    bundle = load_scenario_bundle(scenario_dir)
    result, pipeline_error = _safe_run_pipeline(scenario_dir)
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
    initial_bundle_output_dir = str(Path(scenario_dir).parent / f"{Path(scenario_dir).name}_saved")
    initial_bundle_io_summary = json.dumps(
        {
            "source_scenario_dir": str(Path(scenario_dir)),
            "bundle_manifest": str(bundle.bundle_manifest_path) if bundle.bundle_manifest_path else None,
            "bundle_version": bundle.bundle_version,
            "status": "idle",
        },
        indent=2,
        ensure_ascii=False,
    )

    app = Dash(__name__)
    app.layout = html.Div(
        children=[
            html.H1("Decision Platform - Circuitos Hidráulicos"),
            dcc.Store(id="scenario-dir", data=str(Path(scenario_dir))),
            dcc.Tabs(
                children=[
                    dcc.Tab(
                        label="Dados",
                        children=[
                            html.H2("Tabelas"),
                            html.P("Diretório do bundle salvo"),
                            dcc.Input(
                                id="bundle-output-dir-input",
                                type="text",
                                value=initial_bundle_output_dir,
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Button("Salvar e reabrir bundle", id="save-reopen-bundle-button"),
                            html.Pre(initial_bundle_io_summary, id="bundle-io-summary"),
                            html.H3("nodes.csv"),
                            _table("nodes-grid", bundle.nodes, editable=True),
                            html.H3("component_catalog.csv"),
                            _table("components-grid", bundle.components, editable=True),
                            html.H3("candidate_links.csv"),
                            _table("candidate-links-grid", bundle.candidate_links, editable=True),
                            html.H3("edge_component_rules.csv"),
                            _table("edge-component-rules-grid", bundle.edge_component_rules, editable=True),
                            html.H3("route_requirements.csv"),
                            _table("routes-grid", bundle.route_requirements, editable=True),
                            html.H3("layout_constraints.csv"),
                            _table("layout-constraints-grid", bundle.layout_constraints, editable=True),
                            html.H3("topology_rules.yaml"),
                            dcc.Textarea(
                                id="topology-rules-editor",
                                value=authoring_payload["topology_rules_text"],
                                style={"width": "100%", "height": "260px"},
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.H3("scenario_settings.yaml"),
                            dcc.Textarea(
                                id="scenario-settings-editor",
                                value=authoring_payload["scenario_settings_text"],
                                style={"width": "100%", "height": "260px"},
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Execução",
                        children=[
                            html.H2("Execução"),
                            html.Button("Reexecutar pipeline", id="run-button"),
                            html.Pre(initial_execution_summary, id="execution-summary"),
                        ],
                    ),
                    dcc.Tab(
                        label="Catálogo",
                        children=[
                            html.H2("Soluções"),
                            dcc.Dropdown(
                                id="profile-dropdown",
                                options=_profile_dropdown_options(bundle),
                                value=profile_id,
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Dropdown(
                                id="family-dropdown",
                                options=family_options,
                                value="ALL",
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Checklist(
                                id="feasible-only-checklist",
                                options=[{"label": "Apenas viáveis", "value": "feasible_only"}],
                                value=["feasible_only"] if bundle.scenario_settings["ranking"].get("keep_only_feasible", True) else [],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(id="max-cost-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Input(id="min-quality-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Input(id="min-flow-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Input(id="min-resilience-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Input(id="min-cleaning-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Input(id="min-operability-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Input(id="top-n-family-input", type="number", value=None, persistence=True, persistence_type="session"),
                            dcc.Dropdown(
                                id="fallback-filter-dropdown",
                                options=[
                                    {"label": "Todos", "value": "ALL"},
                                    {"label": "Sem fallback", "value": "NO_FALLBACK"},
                                    {"label": "Com fallback", "value": "WITH_FALLBACK"},
                                ],
                                value="ALL",
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Dropdown(
                                id="infeasibility-reason-dropdown",
                                options=_infeasibility_reason_options(result),
                                value="ALL",
                                persistence=True,
                                persistence_type="session",
                            ),
                            _weight_inputs(bundle),
                            html.Pre(initial_catalog_summary, id="catalog-state-summary"),
                            _catalog_grid(initial_state["ranked_records"]),
                            html.H3("Resumo por família"),
                            _family_summary_grid(initial_state.get("family_summary_records", [])),
                            html.Button("Exportar catálogo ranqueado", id="export-catalog-button"),
                            dcc.Download(id="catalog-download"),
                        ],
                    ),
                    dcc.Tab(
                        label="Comparação",
                        children=[
                            html.H2("Comparação"),
                            dcc.Dropdown(
                                id="compare-candidates-dropdown",
                                options=initial_state["comparison_options"],
                                value=initial_state["comparison_ids"],
                                multi=True,
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Graph(
                                id="comparison-figure",
                                figure=build_solution_comparison_figure(_lookup_candidates(result, initial_state["comparison_ids"]))
                                if result
                                else build_solution_comparison_figure([]),
                            ),
                            _comparison_grid(initial_comparison_records),
                            html.Button("Exportar comparação", id="export-comparison-button"),
                            dcc.Download(id="comparison-download"),
                            html.Button("Exportar comparação JSON", id="export-comparison-json-button"),
                            dcc.Download(id="comparison-json-download"),
                        ],
                    ),
                    dcc.Tab(
                        label="Circuito",
                        children=[
                            html.H2("Renderização 2D"),
                            dcc.Dropdown(
                                id="selected-candidate-dropdown",
                                options=initial_state["selected_options"],
                                value=initial_state["selected_candidate_id"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Dropdown(
                                id="route-highlight-dropdown",
                                options=_route_dropdown_options(candidate_details.get("route_rows", [])),
                                value=_default_route_highlight(candidate_details.get("route_rows", [])),
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Pre(
                                json.dumps(candidate_details.get("summary", {}), indent=2, ensure_ascii=False),
                                id="selected-candidate-summary",
                            ),
                            html.Button("Exportar candidato selecionado", id="export-selected-button"),
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
                        ],
                    ),
                    dcc.Tab(
                        label="Escolha final",
                        children=[
                            html.H2("Candidato oficial"),
                            html.Pre(
                                json.dumps(initial_official_summary, indent=2, ensure_ascii=False),
                                id="official-candidate-summary",
                            ),
                            html.H2("Justificativa"),
                            html.Pre(
                                json.dumps(candidate_details.get("breakdown", {}), indent=2, ensure_ascii=False),
                                id="candidate-breakdown",
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
    runner_up = explanation.get("runner_up") or {}
    return {
        "candidate_id": official_candidate_id,
        "active_profile_id": profile_id,
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
    return {
        "scenario_dir": str(normalized_output_dir),
        "bundle": reloaded_bundle,
        "result": result,
        "pipeline_error": pipeline_error,
        "bundle_io_summary": {
            "status": "saved_and_reopened",
            "source_scenario_dir": str(normalized_source_dir),
            "saved_scenario_dir": str(normalized_output_dir),
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
            "pipeline_error": pipeline_error,
        },
}


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
            "scenario_bundle_version": result.get("scenario_bundle_version") if result else None,
            "scenario_bundle_manifest": result.get("scenario_bundle_manifest") if result else None,
            "scenario_bundle_files": result.get("scenario_bundle_files") if result else None,
            "error": error,
        },
        indent=2,
        ensure_ascii=False,
    )


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
        {"selector": "node", "style": {"background-color": "#1f77b4", "label": "data(id)", "color": "#ffffff"}},
        {"selector": "edge", "style": {"line-color": "#9aa4af", "width": 3, "curve-style": "bezier"}},
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
