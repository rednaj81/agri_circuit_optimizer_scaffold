from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.catalog.pipeline import resolve_selected_candidate
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.ranking.scoring import apply_dynamic_weights
from decision_platform.rendering.circuit import build_solution_comparison_figure
from decision_platform.ui_dash._compat import DASH_AVAILABLE, Dash, Input, Output, State, cyto, dag, dcc, html


def build_app(scenario_dir: str | Path = "data/decision_platform/maquete_v2") -> Dash:
    bundle = load_scenario_bundle(scenario_dir)
    result, pipeline_error = _safe_run_pipeline(scenario_dir)
    profile_id = bundle.scenario_settings["ranking"]["default_profile"]
    initial_state = build_catalog_view_state(
        result,
        profile_id=profile_id,
        current_selected_id=result.get("selected_candidate_id") if result else None,
    )
    candidate_details = build_candidate_detail(result, initial_state["selected_candidate_id"]) if result else {}

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
                            _table("nodes-grid", bundle.nodes),
                            _table("components-grid", bundle.components),
                            _table("routes-grid", bundle.route_requirements),
                        ],
                    ),
                    dcc.Tab(
                        label="Execução",
                        children=[
                            html.H2("Execução"),
                            html.Button("Reexecutar pipeline", id="run-button"),
                            html.Pre(
                                json.dumps(
                                    {
                                        "candidate_count": len(result["catalog"]) if result else 0,
                                        "feasible_count": sum(1 for item in result["catalog"] if item["metrics"]["feasible"]) if result else 0,
                                        "default_profile_id": result.get("default_profile_id") if result else None,
                                        "selected_candidate_id": result.get("selected_candidate_id") if result else None,
                                        "error": pipeline_error,
                                    },
                                    indent=2,
                                    ensure_ascii=False,
                                ),
                                id="execution-summary",
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Catálogo",
                        children=[
                            html.H2("Soluções"),
                            dcc.Dropdown(
                                id="profile-dropdown",
                                options=[{"label": profile, "value": profile} for profile in bundle.weight_profiles["profile_id"].tolist()],
                                value=profile_id,
                            ),
                            dcc.Dropdown(
                                id="family-dropdown",
                                options=[{"label": family, "value": family} for family in sorted(bundle.scenario_settings["enabled_families"])],
                                value="ALL",
                            ),
                            dcc.Checklist(
                                id="feasible-only-checklist",
                                options=[{"label": "Apenas viáveis", "value": "feasible_only"}],
                                value=["feasible_only"] if bundle.scenario_settings["ranking"].get("keep_only_feasible", True) else [],
                            ),
                            dcc.Input(id="max-cost-input", type="number", value=None),
                            dcc.Input(id="min-quality-input", type="number", value=None),
                            dcc.Input(id="min-resilience-input", type="number", value=None),
                            dcc.Dropdown(
                                id="fallback-filter-dropdown",
                                options=[
                                    {"label": "Todos", "value": "ALL"},
                                    {"label": "Sem fallback", "value": "NO_FALLBACK"},
                                    {"label": "Com fallback", "value": "WITH_FALLBACK"},
                                ],
                                value="ALL",
                            ),
                            _weight_inputs(bundle),
                            _table("catalog-grid", pd.DataFrame(initial_state["ranked_records"])),
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
                            ),
                            dcc.Graph(
                                id="comparison-figure",
                                figure=build_solution_comparison_figure(_lookup_candidates(result, initial_state["comparison_ids"]))
                                if result
                                else build_solution_comparison_figure([]),
                            ),
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
                            ),
                            html.Button("Exportar candidato selecionado", id="export-selected-button"),
                            dcc.Download(id="selected-candidate-download"),
                            cyto.Cytoscape(
                                id="circuit-cytoscape",
                                elements=candidate_details.get("cytoscape_elements", []),
                                layout={"name": "preset"},
                                style={"width": "100%", "height": "520px"},
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="Escolha final",
                        children=[
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
        Output("execution-summary", "children"),
        Input("run-button", "n_clicks"),
        State("scenario-dir", "data"),
    )
    def _run_pipeline(n_clicks: Any, current_scenario_dir: str) -> str:
        if not n_clicks:
            return json.dumps({"status": "idle"}, ensure_ascii=False)
        rerun, rerun_error = _safe_run_pipeline(current_scenario_dir)
        return json.dumps(
            {
                "candidate_count": len(rerun["catalog"]) if rerun else 0,
                "feasible_count": sum(1 for item in rerun["catalog"] if item["metrics"]["feasible"]) if rerun else 0,
                "default_profile_id": rerun.get("default_profile_id") if rerun else None,
                "selected_candidate_id": rerun.get("selected_candidate_id") if rerun else None,
                "error": rerun_error,
            },
            indent=2,
            ensure_ascii=False,
        )

    @app.callback(
        Output("catalog-grid", "rowData"),
        Output("selected-candidate-dropdown", "options"),
        Output("selected-candidate-dropdown", "value"),
        Output("compare-candidates-dropdown", "options"),
        Output("compare-candidates-dropdown", "value"),
        Input("profile-dropdown", "value"),
        Input("family-dropdown", "value"),
        Input("feasible-only-checklist", "value"),
        Input("max-cost-input", "value"),
        Input("min-quality-input", "value"),
        Input("min-resilience-input", "value"),
        Input("fallback-filter-dropdown", "value"),
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
        profile: str,
        family: str,
        feasible_only: list[str],
        max_cost: Any,
        min_quality: Any,
        min_resilience: Any,
        fallback_filter: str,
        cost_weight: Any,
        quality_weight: Any,
        flow_weight: Any,
        resilience_weight: Any,
        cleaning_weight: Any,
        operability_weight: Any,
        current_selected_id: str | None,
        current_compare_ids: Any,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, list[dict[str, Any]], list[str]]:
        if not result:
            return [], [], None, [], []
        weights = {
            "cost_weight": cost_weight,
            "quality_weight": quality_weight,
            "flow_weight": flow_weight,
            "resilience_weight": resilience_weight,
            "cleaning_weight": cleaning_weight,
            "operability_weight": operability_weight,
        }
        view_state = build_catalog_view_state(
            result,
            profile_id=profile,
            weight_overrides=weights,
            family=family,
            feasible_only="feasible_only" in (feasible_only or []),
            max_cost=max_cost,
            min_quality=min_quality,
            min_resilience=min_resilience,
            fallback_filter=fallback_filter,
            current_selected_id=current_selected_id,
            current_compare_ids=current_compare_ids,
        )
        return (
            view_state["ranked_records"],
            view_state["selected_options"],
            view_state["selected_candidate_id"],
            view_state["comparison_options"],
            view_state["comparison_ids"],
        )

    @app.callback(
        Output("circuit-cytoscape", "elements"),
        Output("candidate-breakdown", "children"),
        Input("selected-candidate-dropdown", "value"),
    )
    def _update_selected_candidate(candidate_id: str) -> tuple[list[dict[str, Any]], str]:
        if not result or not candidate_id:
            return [], json.dumps({}, ensure_ascii=False)
        detail = build_candidate_detail(result, candidate_id)
        return detail["cytoscape_elements"], json.dumps(detail["breakdown"], indent=2, ensure_ascii=False)

    @app.callback(
        Output("comparison-figure", "figure"),
        Input("compare-candidates-dropdown", "value"),
    )
    def _update_comparison(candidate_ids: Any) -> Any:
        if not result:
            return build_solution_comparison_figure([])
        return build_solution_comparison_figure(_lookup_candidates(result, _normalize_compare_ids(candidate_ids)))

    @app.callback(
        Output("catalog-download", "data"),
        Input("export-catalog-button", "n_clicks"),
        State("profile-dropdown", "value"),
        State("family-dropdown", "value"),
        State("feasible-only-checklist", "value"),
        State("max-cost-input", "value"),
        State("min-quality-input", "value"),
        State("min-resilience-input", "value"),
        State("fallback-filter-dropdown", "value"),
        State("weight-cost", "value"),
        State("weight-quality", "value"),
        State("weight-flow", "value"),
        State("weight-resilience", "value"),
        State("weight-cleaning", "value"),
        State("weight-operability", "value"),
        prevent_initial_call=True,
    )
    def _export_catalog(
        n_clicks: Any,
        profile: str,
        family: str,
        feasible_only: list[str],
        max_cost: Any,
        min_quality: Any,
        min_resilience: Any,
        fallback_filter: str,
        cost_weight: Any,
        quality_weight: Any,
        flow_weight: Any,
        resilience_weight: Any,
        cleaning_weight: Any,
        operability_weight: Any,
    ) -> Any:
        if not n_clicks or not result:
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
            result,
            profile_id=profile,
            weight_overrides=weights,
            family=family,
            feasible_only="feasible_only" in (feasible_only or []),
            max_cost=max_cost,
            min_quality=min_quality,
            min_resilience=min_resilience,
            fallback_filter=fallback_filter,
        )
        return _send_text_download(
            json.dumps(view_state["ranked_records"], indent=2, ensure_ascii=False),
            "ranked_catalog.json",
        )

    @app.callback(
        Output("selected-candidate-download", "data"),
        Input("export-selected-button", "n_clicks"),
        State("selected-candidate-dropdown", "value"),
        prevent_initial_call=True,
    )
    def _export_selected_candidate(n_clicks: Any, candidate_id: str) -> Any:
        if not n_clicks or not result or not candidate_id:
            return None
        detail = build_candidate_detail(result, candidate_id)
        candidate = next(item for item in result["catalog"] if item["candidate_id"] == candidate_id)
        payload = {
            "candidate_id": candidate_id,
            "topology_family": candidate["topology_family"],
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
    min_resilience: Any = None,
    fallback_filter: str | None = None,
    current_selected_id: str | None = None,
    current_compare_ids: list[str] | str | None = None,
) -> dict[str, Any]:
    if not result:
        return {
            "ranked_records": [],
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
        min_resilience=min_resilience,
        fallback_filter=fallback_filter,
    )
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
            min_resilience=min_resilience,
            fallback_filter=fallback_filter,
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
        comparison_ids = [record["candidate_id"] for record in filtered_records[:4]]
    comparison_options = selected_options[:8]
    return {
        "ranked_records": filtered_records,
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
    min_resilience: Any = None,
    fallback_filter: str | None = None,
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
    if min_resilience not in (None, ""):
        filtered = [record for record in filtered if float(record["resilience_score"]) >= float(min_resilience)]
    if fallback_filter == "NO_FALLBACK":
        filtered = [record for record in filtered if int(record["fallback_component_count"]) == 0]
    if fallback_filter == "WITH_FALLBACK":
        filtered = [record for record in filtered if int(record["fallback_component_count"]) > 0]
    return filtered


def build_candidate_detail(result: dict[str, Any] | None, candidate_id: str | None) -> dict[str, Any]:
    if not result or not candidate_id:
        return {"cytoscape_elements": [], "breakdown": {}}
    candidate = next(item for item in result["catalog"] if item["candidate_id"] == candidate_id)
    metrics = candidate["metrics"]
    return {
        "cytoscape_elements": candidate["render"]["cytoscape_elements"],
        "breakdown": {
            "candidate_id": candidate_id,
            "topology_family": candidate["topology_family"],
            "engine_requested": metrics.get("engine_requested"),
            "engine_used": metrics.get("engine_used"),
            "engine_mode": metrics.get("engine_mode"),
            "install_cost": metrics["install_cost"],
            "quality_score_raw": metrics["quality_score_raw"],
            "resilience_score": metrics["resilience_score"],
            "operability_score": metrics["operability_score"],
            "cleaning_score": metrics["cleaning_score"],
            "fallback_component_count": metrics["fallback_component_count"],
            "quality_score_breakdown": metrics.get("quality_score_breakdown", []),
            "quality_flags": metrics.get("quality_flags", []),
            "rules_triggered": metrics.get("rules_triggered", []),
            "selection_log": candidate["payload"].get("selection_log", []),
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


def _safe_run_pipeline(scenario_dir: str | Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return run_decision_pipeline(scenario_dir), None
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


def _table(component_id: str, frame: pd.DataFrame) -> Any:
    return dag.AgGrid(
        id=component_id,
        columnDefs=[{"field": column} for column in frame.columns],
        rowData=frame.to_dict("records"),
        dashGridOptions={"pagination": True, "animateRows": True},
    )


def _weight_inputs(bundle: Any) -> Any:
    profile = bundle.weight_profiles.loc[
        bundle.weight_profiles["profile_id"] == bundle.scenario_settings["ranking"]["default_profile"]
    ].iloc[0]
    return html.Div(
        children=[
            html.H3("Pesos dinâmicos"),
            dcc.Input(id="weight-cost", type="number", value=float(profile["cost_weight"])),
            dcc.Input(id="weight-quality", type="number", value=float(profile["quality_weight"])),
            dcc.Input(id="weight-flow", type="number", value=float(profile["flow_weight"])),
            dcc.Input(id="weight-resilience", type="number", value=float(profile["resilience_weight"])),
            dcc.Input(id="weight-cleaning", type="number", value=float(profile["cleaning_weight"])),
            dcc.Input(id="weight-operability", type="number", value=float(profile["operability_weight"])),
        ],
    )


def _send_text_download(content: str, filename: str) -> Any:
    sender = getattr(dcc, "send_string", None)
    if callable(sender):  # pragma: no branch
        return sender(content, filename)
    return {"content": content, "filename": filename}


def _weight_overrides_active(weight_overrides: dict[str, Any] | None) -> bool:
    return bool(weight_overrides) and any(value not in (None, "") for value in weight_overrides.values())


def _filters_active(
    *,
    family: str | None,
    feasible_only: bool,
    max_cost: Any,
    min_quality: Any,
    min_resilience: Any,
    fallback_filter: str | None,
) -> bool:
    return any(
        [
            family not in (None, "", "ALL"),
            feasible_only,
            max_cost not in (None, ""),
            min_quality not in (None, ""),
            min_resilience not in (None, ""),
            fallback_filter not in (None, "", "ALL"),
        ]
    )


def _normalize_compare_ids(current_compare_ids: list[str] | str | None) -> list[str]:
    if current_compare_ids is None:
        return []
    if isinstance(current_compare_ids, str):
        return [current_compare_ids]
    return list(current_compare_ids)


def main() -> None:
    app = build_app()
    if DASH_AVAILABLE:  # pragma: no cover
        app.run(debug=False)
        return
    raise RuntimeError("Dash dependencies are not installed. The app layout was built successfully.")


if __name__ == "__main__":
    main()
