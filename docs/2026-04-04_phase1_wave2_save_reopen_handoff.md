# Handoff phase_1 wave_2

## Objetivo

Consumir o bundle persistido no fluxo real de autoria/reabertura local e fechar a cobertura dos metadados do bundle nos exports da pipeline.

## Entregue

- fluxo único de `Salvar e reabrir bundle` na aba `Dados` da UI local
- persistência determinística de `nodes`, `components`, `route_requirements` e `scenario_settings.yaml` no bundle canônico
- recarga do bundle salvo com validação fail-closed preservada
- execução da pipeline após reabertura do bundle salvo, com suporte explícito a cenários diagnósticos já configurados no bundle
- testes cobrindo:
  - round-trip de autoria com mudança real em nó, rota, componente e `scenario_settings`
  - falha fechada para rota inválida salva via fluxo de autoria
  - fluxo UI save/reopen com recarga do bundle e rerun da pipeline
  - metadados `scenario_bundle_version`, `scenario_bundle_manifest` e `scenario_bundle_files` em `summary.json` e no resumo do CLI

## Arquivos principais

- `src/decision_platform/data_io/storage.py`
- `src/decision_platform/ui_dash/app.py`
- `src/decision_platform/ui_dash/_compat.py`
- `src/decision_platform/api/run_pipeline.py`
- `tests/decision_platform/test_scenario_persistence.py`
- `tests/decision_platform/test_ui_smoke.py`
- `tests/decision_platform/test_run_pipeline_cli.py`
- `tests/decision_platform/test_maquete_v2_acceptance.py`

## Testes executados

- `python -m pytest tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_run_pipeline_cli.py -q -p no:cacheprovider`
- `python -m pytest tests/decision_platform/test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q -p no:cacheprovider`
- `python -m pytest tests/decision_platform -m fast -q -p no:cacheprovider`

## Limites e riscos honestos

- a UI ainda não é um studio completo; este fluxo só salva as tabelas já expostas e o `scenario_settings.yaml`
- a rerank/comparação na UI agora recarrega a pipeline a partir de `scenario-dir`, o que privilegia coerência do cenário salvo, não performance
- `official_preflight`, `official`, `diagnostic` e `diagnostic_comparison` não mudaram de significado; o opt-in diagnóstico continua restrito ao runtime quando o bundle já declara engine diagnóstico
