# Phase UX Refinement Wave 2 - Primary Flow CTA Reanchor

## Objective

Entregar um delta real de UX na `decision_platform` que reancore a limpeza de navegação e IA no código alterado, deixando o caminho principal mais explícito em `Studio`, `Runs` e `Decisão` e empurrando a leitura técnica para disclosure secundário.

## Delivered

- Reforcei o gate de `Studio` com um bloco explícito de `Fluxo principal`, mostrando etapa atual, sinal de passagem e destino seguinte sem exigir leitura técnica para entender o que fazer.
- Adicionei CTAs diretos por link nas superfícies primárias: `Studio -> Runs`, `Studio -> Auditoria`, `Runs -> Studio`, `Runs -> Decisão`, `Decisão -> Runs` e `Decisão -> Auditoria`.
- Reancorei `Runs` para abrir com o board de passagem `Studio -> Runs` acima dos painéis paralelos, em vez de deixar o fluxo principal competir com fila, execução e operações no mesmo nível visual.
- Reancorei `Decisão` para abrir com o board `Runs -> Decisão` antes de winner, runner-up e sinais, deixando explícito o estado do fluxo e o próximo destino.
- Mantive a evidência técnica existente em `Details` e `Auditoria`; a wave não reabriu arquitetura, não mexeu no solver, ranking ou no caminho oficial Julia-only.
- Ampliei os smoke tests para provar a nova hierarquia e os links de fluxo principal nas três superfícies.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_tab_surfaces_readiness_and_selection_context or studio_readiness_panel_surfaces_runs_transition_with_real_readiness or runs_tab_combines_queue_and_execution_summary or runs_flow_panel_reflects_studio_gate_and_queue_state or decision_tab_contains_advanced_sections_without_extra_primary_tabs or decision_flow_panel_makes_transition_and_next_action_explicit" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-full-current
```

Result:

- `6 passed, 45 deselected in 1.34s`
- `51 passed in 475.86s (0:07:55)`

## Evidence

- Structured UI snapshot: `docs/2026-04-06_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash/Cytoscape.
- No change to Julia-only official execution, fail-closed semantics, queue contract, ranking logic or solver behavior.
- No exposure of hubs internos ou nós técnicos como superfície principal do Studio.
- No reintroduction of `html.Pre`, raw JSON or audit payloads as the main reading mechanism in the first fold.

## Honest Handoff

Esta wave finalmente deixa um delta de produto pequeno, mas atribuível, nos arquivos centrais de UI e smoke tests. A melhoria não está em backend novo nem em microcopy isolada: a mudança mensurável é a hierarquia da primeira dobra. `Runs` e `Decisão` agora começam pelo fluxo principal e seus destinos imediatos, enquanto `Studio` deixa explícita a saída para `Runs` e `Auditoria` dentro do próprio gate de readiness. A superfície técnica continua disponível, mas perdeu prioridade visual no caminho principal.
