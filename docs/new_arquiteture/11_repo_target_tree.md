# Árvore alvo do repositório

```text
repo/
  src/
    decision_platform/
      api/
      catalog/
      data_io/
      graph_generation/
      graph_repair/
      ranking/
      rendering/
      scenario_engine/
      ui_dash/
      julia_bridge/
      utils/

  julia/
    Project.toml
    Manifest.toml   # opcional
    bin/
      run_scenario.jl
    src/
      DecisionEngine.jl
      ScenarioBuilder.jl
      RouteMetrics.jl
      ExportResults.jl
    test/

  data/
    decision_platform/
      maquete_v2/
        nodes.csv
        components.csv
        candidate_links.csv
        edge_component_rules.csv
        route_requirements.csv
        quality_rules.csv
        weight_profiles.csv
        layout_constraints.csv
        topology_rules.yaml
        scenario_settings.yaml

  tests/
    decision_platform/
      test_loaders.py
      test_graph_generation.py
      test_julia_bridge.py
      test_catalog_ranking.py
      test_ui_smoke.py
      test_maquete_v2_acceptance.py
```

## Regra
A nova arquitetura deve coexistir com o baseline.
Não remover o legado nesta rodada.
