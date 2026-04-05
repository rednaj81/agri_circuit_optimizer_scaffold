# Phase 1 Wave 1 Handoff

## Objective

Fechar o caminho canônico `save -> reopen -> run` para que `scenario_bundle.yaml` governe a reabertura e a execução do cenário, com `component_catalog.csv` como persistência oficial do catálogo e proveniência explícita no runtime, CLI, UI e artefatos exportados.

## Delivered

- O runtime oficial agora publica a proveniência mínima do cenário em `scenario_provenance`, incluindo `scenario_root`, `requested_scenario_dir`, `requested_dir_matches_bundle_root`, `bundle_version`, `bundle_manifest`, `bundle_files` e `output_dir`.
- O `summary.json` exportado e o resumo impresso pela CLI passaram a carregar esses mesmos sinais, além de `scenario_bundle_root`, sem reabrir fallback implícito.
- A UI expõe a raiz canônica do bundle salvo, os arquivos efetivamente persistidos e a proveniência da execução após `save_and_reopen_local_bundle`.
- Os testes de persistência, CLI, UI smoke e gate de saída da phase 1 foram endurecidos para cobrir bundle inválido, manifesto ausente, precedência do `component_catalog.csv` e rastreabilidade do bundle executado.
- Os testes lentos que exercitam o caminho canônico em modo diagnóstico agora desabilitam explicitamente o probe real de Julia para validar contrato e proveniência sem custo operacional desnecessário.

## Validations

- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_run_pipeline_cli.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase1_exit_acceptance.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_scenario_persistence.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -q`

## Notes

- Nenhuma regra funcional de V2/V3 foi tocada.
- O caminho oficial continua fail-closed para manifesto ausente, `bundle_version` inválido e layout legado fora de fluxos explícitos de migração/teste.
- A trilha Julia-only do runtime oficial foi preservada; o modo diagnóstico permanece explícito e marcado no resultado.
