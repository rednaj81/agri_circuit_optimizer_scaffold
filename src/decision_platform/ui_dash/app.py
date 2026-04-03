from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from decision_platform.api.run_pipeline import run_decision_pipeline
from decision_platform.data_io.loader import load_scenario_bundle
from decision_platform.rendering.circuit import build_solution_comparison_figure
from decision_platform.ui_dash._compat import DASH_AVAILABLE, Dash, Input, Output, State, cyto, dag, dcc, html


def build_app(scenario_dir: str | Path = "data/decision_platform/maquete_v2") -> Dash:
    bundle = load_scenario_bundle(scenario_dir)
    result = run_decision_pipeline(scenario_dir)
    profile_id = bundle.scenario_settings["ranking"]["default_profile"]
    ranked = result["ranked_profiles"][profile_id]
    top_candidate = result["catalog"][0]

    app = Dash(__name__)
    app.layout = html.Div(
        html.H1("Decision Platform - Circuitos Hidráulicos"),
        dcc.Store(id="scenario-dir", data=str(Path(scenario_dir))),
        dcc.Tabs(
            dcc.Tab(label="Dados", children=[html.H2("Tabelas"), _table("nodes-grid", bundle.nodes), _table("components-grid", bundle.components), _table("routes-grid", bundle.route_requirements)]),
            dcc.Tab(label="Execução", children=[html.H2("Execução"), html.Button("Reexecutar pipeline", id="run-button"), html.Pre(json.dumps({"candidate_count": len(result["catalog"]), "feasible_count": sum(1 for item in result["catalog"] if item["metrics"]["feasible"])}, indent=2, ensure_ascii=False), id="execution-summary")]),
            dcc.Tab(label="Catálogo", children=[html.H2("Soluções"), _table("catalog-grid", pd.DataFrame(ranked))]),
            dcc.Tab(label="Comparação", children=[html.H2("Comparação"), dcc.Graph(id="comparison-figure", figure=build_solution_comparison_figure(result["catalog"][:4]))]),
            dcc.Tab(label="Circuito", children=[html.H2("Renderização 2D"), cyto.Cytoscape(id="circuit-cytoscape", elements=top_candidate["render"]["cytoscape_elements"], layout={"name": "preset"}, style={"width": "100%", "height": "520px"})]),
            dcc.Tab(label="Escolha final", children=[html.H2("Justificativa"), html.Pre(json.dumps({"candidate_id": ranked[0]["candidate_id"], "topology_family": ranked[0]["topology_family"], "score_final": ranked[0]["score_final"]}, indent=2, ensure_ascii=False))]),
        ),
    )

    @app.callback(Output("execution-summary", "children"), Input("run-button", "n_clicks"), State("scenario-dir", "data"))
    def _run_pipeline(n_clicks: Any, current_scenario_dir: str) -> str:
        if not n_clicks:
            return app.layout.children[2].children[1].children[1] if False else json.dumps({"status": "idle"}, ensure_ascii=False)
        rerun = run_decision_pipeline(current_scenario_dir)
        return json.dumps({"candidate_count": len(rerun["catalog"]), "feasible_count": sum(1 for item in rerun["catalog"] if item["metrics"]["feasible"])}, indent=2, ensure_ascii=False)

    return app


def _table(component_id: str, frame: pd.DataFrame) -> Any:
    return dag.AgGrid(id=component_id, columnDefs=[{"field": column} for column in frame.columns], rowData=frame.to_dict("records"), dashGridOptions={"pagination": True, "animateRows": True})


def main() -> None:
    app = build_app()
    if DASH_AVAILABLE:  # pragma: no cover
        app.run(debug=False)
        return
    raise RuntimeError("Dash dependencies are not installed. The app layout was built successfully.")


if __name__ == "__main__":
    main()
