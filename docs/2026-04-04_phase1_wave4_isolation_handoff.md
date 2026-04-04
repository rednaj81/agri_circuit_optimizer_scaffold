# Phase 1 Wave 4 Handoff

## Objective

Estabilizar o gate de saída da phase 1 removendo acoplamento de estado entre fixtures temporárias, save/reopen da UI e paths relativos compartilhados.

## Delivered

- `tests/decision_platform/scenario_utils.py` agora cria diretórios temporários únicos sob `tests/_tmp` para cenários copiados e saídas auxiliares de teste, sem depender do temp global do host.
- `src/decision_platform/ui_dash/app.py` normaliza `scenario_dir` e `output_dir` para paths absolutos e determinísticos no build do app, no rerun local da pipeline e no save/reopen.
- Os testes de persistência, UI e CLI que ainda usavam diretórios fixos passaram a usar paths únicos por execução.
- Foi adicionado um teste de regressão que reconstrói a UI a partir de um bundle salvo depois da limpeza do cenário-fonte, provando que o app não depende de arquivos já removidos.

## Validations

- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_scenario_persistence.py tests\decision_platform\test_scenario_contract_validation.py tests\decision_platform\test_ui_smoke.py tests\decision_platform\test_run_pipeline_cli.py -q -p no:cacheprovider`
- O mesmo comando acima foi executado uma segunda vez, novamente verde.
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q -p no:cacheprovider`

## Notes

- Nenhuma validação de domínio foi relaxada.
- Nenhuma semântica do caminho oficial Julia-only foi alterada.
- A estabilização ficou restrita a isolamento de paths temporários e reconstrução local da UI/save-reopen.
