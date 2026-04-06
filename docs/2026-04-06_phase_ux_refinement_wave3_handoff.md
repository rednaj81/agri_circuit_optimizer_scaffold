# Phase UX Refinement Wave 3 - Runs and Decision Shell Consolidation

## Objective

Fechar o recorte principal de `ux_phase_1` limpando o ruído residual da primeira dobra de `Runs` e `Decisão`, reduzindo caminhos concorrentes e consolidando um padrão único de abertura orientado por estado atual, objetivo da tela e próxima ação.

## Delivered

- Consolidei `Runs` e `Decisão` no mesmo padrão de abertura, usando o helper `_screen_opening_panel` para expor `Estado atual`, `Objetivo desta área`, `Próxima ação` e transições explícitas entre espaços primários.
- Removi dos shells de `Runs` e `Decisão` os botões redundantes que competiam com os links de fluxo principal adicionados na wave anterior.
- Simplifiquei o callback de navegação primária para refletir a redução real de caminhos internos concorrentes, mantendo apenas os gatilhos ainda necessários para `Studio` e para a abertura contextual de `Decisão` a partir do resumo executivo.
- Rebaixei o CTA contextual de execução para `Abrir Decisão desta execução`, deixando claro que ele é um atalho secundário, não mais um caminho primário concorrente.
- Mantive logs, JSON e artefatos avançados em disclosure secundário e em `Auditoria`, sem reintroduzir superfícies técnicas na primeira dobra.
- Atualizei os smoke tests para comprovar a remoção dos controles redundantes e a consistência do shell entre `Runs` e `Decisão`.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_discovery_callbacks_open_guide_and_audit_tab or decision_tab_contains_advanced_sections_without_extra_primary_tabs or runs_tab_combines_queue_and_execution_summary or runs_flow_panel_reflects_studio_gate_and_queue_state or primary_runs_panels_hide_raw_backend_keys_in_main_surface or decision_flow_panel_makes_transition_and_next_action_explicit" --basetemp tests/_tmp/pytest-basetemp-ux-wave3-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-full-current
```

Result:

- `6 passed, 46 deselected in 1.44s`
- `52 passed in 477.49s (0:07:57)`

## Evidence

- Structured UI snapshot: `docs/2026-04-06_phase_ux_refinement_wave3_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash/Cytoscape.
- No change to backend de runs, ranking, solver, caminho Julia-only ou contratos canônicos.
- No retorno de logs, JSON cru ou painéis de auditoria para a primeira dobra de `Runs` ou `Decisão`.
- No avanço prematuro para escopo de fases seguintes além da consolidação do shell primário.

## Honest Handoff

O ganho desta wave é de limpeza estrutural do shell, não de feature nova. `Runs` e `Decisão` já tinham fluxo explícito, mas ainda conviviam com CTAs duplicados e um callback de navegação inflado por compatibilidades que poluíam a leitura principal. Agora as duas telas abrem de forma homogênea, com menos ruído de navegação e um caminho primário mais claro. O atalho contextual de execução foi mantido, mas explicitamente rebaixado como secundário.
