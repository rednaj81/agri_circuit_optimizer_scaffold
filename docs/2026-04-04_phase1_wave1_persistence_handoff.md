# Handoff phase_1 wave_1

## Objetivo

Abrir a phase 1 com persistência local versionada de cenário e catálogo de componentes, sem reabrir o gate Julia-only da phase 0.

## Entregue

- `scenario_bundle.yaml` como manifesto canônico com `bundle_version: decision_platform_scenario_bundle/v1`
- `component_catalog.csv` como arquivo canônico do catálogo persistido
- compatibilidade retroativa do loader com layout legado e precedência explícita do manifesto quando presente
- `save_scenario_bundle(...)` para salvar e reabrir bundles locais de forma determinística
- metadados do bundle persistido exportados no resultado/resumo do pipeline
- testes cobrindo round-trip, precedência do catálogo canônico e falhas claras para manifesto inválido

## Arquivos principais

- `src/decision_platform/data_io/loader.py`
- `src/decision_platform/data_io/storage.py`
- `src/decision_platform/catalog/pipeline.py`
- `data/decision_platform/maquete_v2/scenario_bundle.yaml`
- `data/decision_platform/maquete_v2/component_catalog.csv`
- `tests/decision_platform/test_scenario_persistence.py`

## Testes executados

- `python -m pytest tests/decision_platform/test_loaders.py tests/decision_platform/test_scenario_persistence.py -q -p no:cacheprovider`
- `python -m pytest tests/decision_platform -m fast -q -p no:cacheprovider`
- `python -m pytest tests/decision_platform/test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q -p no:cacheprovider`

## Limites e riscos honestos

- o studio visual ainda não grava cenários editáveis; esta onda entrega só o formato/base de persistência local
- `components.csv` segue existindo apenas como alias legado; o caminho canônico agora é `component_catalog.csv`
- ainda não há versionamento transacional de runs, artefatos ou histórico de edição multiusuário

## Risco provisório

Baixo a moderado. A mudança é localizada no data layer e coberta por round-trip + aceite da pipeline, mas a próxima onda ainda precisa decidir como o studio e a futura fila vão consumir esse bundle sem criar divergências de autoria.
