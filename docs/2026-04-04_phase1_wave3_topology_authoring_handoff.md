# Phase 1 Wave 3 Handoff

## Objective

Fechar a autoria tabular do bundle canônico para os artefatos topológicos centrais, preservando o fluxo único de save/reopen local e endurecendo o contrato fail-closed para links semanticamente ambíguos.

## Delivered

- `save_authored_scenario_bundle(...)` e `bundle_authoring_payload(...)` agora incluem:
  - `candidate_links.csv`
  - `edge_component_rules.csv`
  - `layout_constraints.csv`
  - `topology_rules.yaml`
- A aba `Dados` da UI local passou a editar e reabrir esses artefatos pelo mesmo botão `Salvar e reabrir bundle`, sem criar um fluxo paralelo de persistência.
- `load_scenario_bundle(...)` passou a falhar fechado para:
  - `candidate_links.csv` com `link_id` vazio
  - `candidate_links.csv` com `link_id` duplicado
  - self-loop (`from_node == to_node`)
  - `archetype` sem regra correspondente em `edge_component_rules.csv`
  - `family_hint` fora das famílias declaradas em `topology_rules.yaml` ou fora das `enabled_families`
- Os testes de persistência/UI/contrato agora cobrem round-trip e rejeição dessas invariantes.

## Validations

- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_scenario_persistence.py tests\decision_platform\test_scenario_contract_validation.py tests\decision_platform\test_ui_smoke.py tests\decision_platform\test_run_pipeline_cli.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-wave3`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-wave3-accept`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-wave3-fast`

## Notes

- O caminho oficial Julia-only não foi alterado.
- Studio visual, fila/background runs e decisão UI continuam fora desta onda.
- A persistência continua local em filesystem; não há versionamento multiusuário nem workflow remoto.
