# Phase 2 Wave 1 Handoff

## Objective

Abrir a phase 2 com o menor corte funcional do studio de nós e arestas, limitado nesta onda à edição visual mínima de nós sobre o bundle canônico já congelado.

## Delivered

- O app ganhou uma aba `Studio` com:
  - inspeção visual dos nós do cenário
  - seleção por clique
  - edição básica de `node_id`, `label`, `node_type`, `x_m`, `y_m`, `allow_inbound` e `allow_outbound`
  - movimento visual mínimo por `nudge` (`left/right/up/down`) sobre a malha de nós
- O studio continua usando `nodes.csv` como única fonte de verdade e não cria formato novo de artefato.
- O fluxo existente de `Salvar e reabrir bundle` continua sendo o único caminho de persistência do cenário editado.
- O loader passou a falhar fechado para `nodes.csv` com `node_id` vazio/duplicado e `node_type` ou `label` em branco.

## Validations

- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_scenario_persistence.py tests\decision_platform\test_ui_smoke.py -q -p no:cacheprovider`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase1_exit_acceptance.py tests\decision_platform\test_scenario_persistence.py tests\decision_platform\test_scenario_contract_validation.py tests\decision_platform\test_ui_smoke.py tests\decision_platform\test_run_pipeline_cli.py -q -p no:cacheprovider`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q -p no:cacheprovider`

## Notes

- Esta onda não reabre persistência, topologia, fila nem o caminho oficial Julia-only.
- O studio visual ainda não edita arestas; o corte desta onda é apenas o layout/propriedades básicas de nós com round-trip via bundle canônico.
