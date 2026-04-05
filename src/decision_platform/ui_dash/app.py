from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from decision_platform.api.run_pipeline import (
    DEFAULT_RUN_QUEUE_ROOT,
    OfficialRuntimeConfigError,
    cancel_run_job,
    inspect_run_job,
    rerun_run_job,
    run_decision_pipeline,
    summarize_run_jobs,
)
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
    initial_node_studio_selected_id = _default_node_studio_selection(authoring_payload["nodes_rows"])
    initial_node_studio_elements = build_node_studio_elements(
        authoring_payload["nodes_rows"],
        authoring_payload["candidate_links_rows"],
    )
    initial_edge_studio_selected_id = _default_edge_studio_selection(authoring_payload["candidate_links_rows"])
    initial_node_studio_summary = json.dumps(
        _build_node_studio_summary(authoring_payload["nodes_rows"], initial_node_studio_selected_id),
        indent=2,
        ensure_ascii=False,
    )
    initial_node_studio_form = _node_studio_form_values(authoring_payload["nodes_rows"], initial_node_studio_selected_id)
    initial_edge_studio_summary = json.dumps(
        _build_edge_studio_summary(authoring_payload["candidate_links_rows"], initial_edge_studio_selected_id),
        indent=2,
        ensure_ascii=False,
    )
    initial_edge_studio_form = _edge_studio_form_values(
        authoring_payload["candidate_links_rows"],
        initial_edge_studio_selected_id,
    )
    initial_run_jobs_snapshot = build_run_jobs_snapshot()
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

    app = Dash(__name__)
    app.layout = html.Div(
        children=[
            html.H1("Decision Platform - Circuitos Hidráulicos"),
            dcc.Store(id="scenario-dir", data=str(Path(scenario_dir))),
            dcc.Store(id="node-studio-selected-id", data=initial_node_studio_selected_id),
            dcc.Store(id="edge-studio-selected-id", data=initial_edge_studio_selected_id),
            dcc.Store(id="studio-status-message", data=""),
            dcc.Tabs(
                children=[
                    dcc.Tab(
                        label="Studio",
                        children=[
                            html.H2("Studio de Nós e Arestas"),
                            html.P("Edição visual mínima de nodes.csv e candidate_links.csv sobre o bundle canônico."),
                            cyto.Cytoscape(
                                id="node-studio-cytoscape",
                                elements=initial_node_studio_elements,
                                layout={"name": "preset"},
                                style={"width": "100%", "height": "520px"},
                                stylesheet=_build_node_studio_stylesheet(
                                    initial_node_studio_selected_id,
                                    initial_edge_studio_selected_id,
                                ),
                            ),
                            html.Pre("", id="studio-status"),
                            html.Pre(initial_node_studio_summary, id="node-studio-summary"),
                            dcc.Input(
                                id="node-studio-node-id",
                                type="text",
                                value=initial_node_studio_form["node_id"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="node-studio-label",
                                type="text",
                                value=initial_node_studio_form["label"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="node-studio-node-type",
                                type="text",
                                value=initial_node_studio_form["node_type"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="node-studio-x-m",
                                type="number",
                                value=initial_node_studio_form["x_m"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="node-studio-y-m",
                                type="number",
                                value=initial_node_studio_form["y_m"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Checklist(
                                id="node-studio-allow-inbound",
                                options=[{"label": "allow_inbound", "value": "allow_inbound"}],
                                value=initial_node_studio_form["allow_inbound"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Checklist(
                                id="node-studio-allow-outbound",
                                options=[{"label": "allow_outbound", "value": "allow_outbound"}],
                                value=initial_node_studio_form["allow_outbound"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Button("Aplicar propriedades do nó", id="node-studio-apply-button"),
                            html.Button("Criar nó", id="node-studio-create-button"),
                            html.Button("Duplicar nó", id="node-studio-duplicate-button"),
                            html.Button("Excluir nó selecionado", id="node-studio-delete-button"),
                            dcc.Dropdown(
                                id="node-studio-move-direction",
                                options=[
                                    {"label": "Esquerda", "value": "left"},
                                    {"label": "Direita", "value": "right"},
                                    {"label": "Cima", "value": "up"},
                                    {"label": "Baixo", "value": "down"},
                                ],
                                value="right",
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="node-studio-move-step",
                                type="number",
                                value=0.02,
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Button("Mover nó", id="node-studio-move-button"),
                            html.H3("Aresta selecionada"),
                            html.Pre(initial_edge_studio_summary, id="edge-studio-summary"),
                            dcc.Input(
                                id="edge-studio-link-id",
                                type="text",
                                value=initial_edge_studio_form["link_id"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="edge-studio-from-node",
                                type="text",
                                value=initial_edge_studio_form["from_node"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="edge-studio-to-node",
                                type="text",
                                value=initial_edge_studio_form["to_node"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="edge-studio-archetype",
                                type="text",
                                value=initial_edge_studio_form["archetype"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="edge-studio-length-m",
                                type="number",
                                value=initial_edge_studio_form["length_m"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Checklist(
                                id="edge-studio-bidirectional",
                                options=[{"label": "bidirectional", "value": "bidirectional"}],
                                value=initial_edge_studio_form["bidirectional"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id="edge-studio-family-hint",
                                type="text",
                                value=initial_edge_studio_form["family_hint"],
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Button("Aplicar propriedades da aresta", id="edge-studio-apply-button"),
                            html.Button("Criar aresta", id="edge-studio-create-button"),
                            html.Button("Excluir aresta selecionada", id="edge-studio-delete-button"),
                        ],
                    ),
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
                        label="Runs",
                        children=[
                            html.H2("Runs seriais"),
                            html.P("Inspeção mínima da fila serial local de run jobs."),
                            html.Button("Atualizar runs", id="run-jobs-refresh-button"),
                            dcc.Dropdown(
                                id="run-job-selected-id",
                                options=initial_run_job_options,
                                value=initial_run_job_selected_id,
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Button("Cancelar run selecionada", id="run-job-cancel-button"),
                            html.Button("Reexecutar run selecionada", id="run-job-rerun-button"),
                            html.Pre("", id="run-jobs-status"),
                            html.Pre(initial_run_jobs_summary, id="run-jobs-summary"),
                            html.Pre(initial_run_job_detail, id="run-job-detail"),
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
        Output("node-studio-cytoscape", "elements"),
        Output("node-studio-cytoscape", "stylesheet"),
        Output("node-studio-summary", "children"),
        Output("edge-studio-summary", "children"),
        Output("studio-status", "children"),
        Input("nodes-grid", "rowData"),
        Input("candidate-links-grid", "rowData"),
        Input("node-studio-selected-id", "data"),
        Input("edge-studio-selected-id", "data"),
        Input("studio-status-message", "data"),
    )
    def _refresh_node_studio(
        nodes_rows: list[dict[str, Any]] | None,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        selected_edge_id: str | None,
        studio_status_message: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, str, str]:
        normalized_nodes = nodes_rows or []
        normalized_links = candidate_links_rows or []
        selected_id = _default_node_studio_selection(normalized_nodes, preferred_node_id=selected_node_id)
        selected_link_id = _default_edge_studio_selection(normalized_links, preferred_link_id=selected_edge_id)
        return (
            build_node_studio_elements(normalized_nodes, normalized_links),
            _build_node_studio_stylesheet(selected_id, selected_link_id),
            json.dumps(_build_node_studio_summary(normalized_nodes, selected_id), indent=2, ensure_ascii=False),
            json.dumps(_build_edge_studio_summary(normalized_links, selected_link_id), indent=2, ensure_ascii=False),
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
        Input("node-studio-move-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        State("node-studio-move-direction", "value"),
        State("node-studio-move-step", "value"),
        prevent_initial_call=True,
    )
    def _move_node_studio_selection(
        n_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
        direction: str | None,
        step: Any,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return nodes_rows or [], selected_node_id, ""
        updated_rows, next_selected_id = move_node_studio_selection(
            nodes_rows or [],
            selected_node_id=selected_node_id,
            direction=direction,
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
        Input("node-studio-duplicate-button", "n_clicks"),
        State("nodes-grid", "rowData"),
        State("node-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _duplicate_node_studio_entry(
        n_clicks: Any,
        nodes_rows: list[dict[str, Any]] | None,
        selected_node_id: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
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
            selected_link_id = str(tap_edge_data.get("link_id") or tap_edge_data.get("id") or "").strip() or current_selected_link_id
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
        State("candidate-links-grid", "rowData"),
        State("edge-studio-selected-id", "data"),
        prevent_initial_call=True,
    )
    def _delete_edge_studio_entry(
        n_clicks: Any,
        candidate_links_rows: list[dict[str, Any]] | None,
        selected_link_id: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, str]:
        if not n_clicks:
            return candidate_links_rows or [], selected_link_id, ""
        updated_rows, next_selected_link_id = delete_edge_studio_selection(
            candidate_links_rows or [],
            selected_link_id=selected_link_id,
        )
        return updated_rows, next_selected_link_id, ""

    @app.callback(
        Output("run-jobs-summary", "children"),
        Output("run-job-selected-id", "options"),
        Output("run-job-selected-id", "value"),
        Output("run-job-detail", "children"),
        Output("run-jobs-status", "children"),
        Input("run-jobs-refresh-button", "n_clicks"),
        State("run-job-selected-id", "value"),
    )
    def _refresh_run_jobs_summary(
        n_clicks: Any,
        selected_run_id: str | None,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        if not n_clicks:
            return (
                initial_run_jobs_summary,
                initial_run_job_options,
                initial_run_job_selected_id,
                initial_run_job_detail,
                "",
            )
        snapshot = build_run_jobs_snapshot(preferred_run_id=selected_run_id)
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
        prevent_initial_call=True,
    )
    def _cancel_selected_run_job(
        n_clicks: Any,
        selected_run_id: str | None,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        status_message = ""
        preferred_run_id = selected_run_id
        if n_clicks:
            if not selected_run_id:
                status_message = "Nenhuma run selecionada para cancelamento."
            else:
                try:
                    job = cancel_run_job(selected_run_id)
                    preferred_run_id = job["run_id"]
                    status_message = f"run_job {job['run_id']} -> {job['status']}"
                except Exception as exc:
                    status_message = str(exc)
        snapshot = build_run_jobs_snapshot(preferred_run_id=preferred_run_id)
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
        prevent_initial_call=True,
    )
    def _rerun_selected_run_job(
        n_clicks: Any,
        selected_run_id: str | None,
    ) -> tuple[str, list[dict[str, str]], str | None, str, str]:
        status_message = ""
        preferred_run_id = selected_run_id
        if n_clicks:
            if not selected_run_id:
                status_message = "Nenhuma run selecionada para reexecução."
            else:
                try:
                    rerun_job = rerun_run_job(selected_run_id)
                    preferred_run_id = rerun_job["run_id"]
                    status_message = (
                        f"run_job {rerun_job['run_id']} enfileirada como re-run de {selected_run_id}"
                    )
                except Exception as exc:
                    status_message = str(exc)
        snapshot = build_run_jobs_snapshot(preferred_run_id=preferred_run_id)
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
        prevent_initial_call=True,
    )
    def _refresh_selected_run_job_detail(selected_run_id: str | None) -> str:
        return _serialize_json(build_run_job_detail_summary(selected_run_id))

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
        "selected_node_id": selected_id,
        "selected_node": selected_row,
    }


def _build_edge_studio_summary(
    candidate_links_rows: list[dict[str, Any]],
    selected_link_id: str | None,
) -> dict[str, Any]:
    selected_id = _default_edge_studio_selection(candidate_links_rows, preferred_link_id=selected_link_id)
    selected_row = next(
        (dict(item) for item in candidate_links_rows if str(item.get("link_id", "")).strip() == selected_id),
        None,
    )
    return {
        "edge_count": len(candidate_links_rows),
        "selected_link_id": selected_id,
        "selected_edge": selected_row,
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
        "source_bundle_root": job.get("source_bundle_root"),
        "source_bundle_version": job.get("source_bundle_version"),
        "source_bundle_manifest": job.get("source_bundle_manifest"),
        "source_bundle_files": job.get("source_bundle_files", {}),
        "result_summary_path": job.get("result_summary_path"),
        "error": job.get("error"),
        "artifacts": job.get("artifacts", {}),
        "events": job.get("events", []),
        "log_tail": job.get("log_tail", ""),
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
    return {
        "summary": summary,
        "options": options,
        "selected_run_id": selected_run_id,
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
