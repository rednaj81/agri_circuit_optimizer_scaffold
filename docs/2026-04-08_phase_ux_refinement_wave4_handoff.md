# Phase UX Refinement Wave 4 Handoff

## Escopo executado

- Troquei os rótulos primários de rota no Studio de `R001 · W -> M` para leitura operacional em linguagem de negócio.
- Mantive IDs técnicos de rota apenas como detalhe secundário dentro do disclosure local das rotas em foco.
- Alinhei command center, editor local de rotas, resumo de fornecimento e readiness para descrever a mesma rota com o mesmo vocabulário de negócio.
- Fechei o último vazamento de `W` e `S` nas mensagens principais de readiness e no foco do canvas, convertendo essas regras para os nomes de negócio correspondentes.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - introduz helpers de leitura primária de rota em linguagem de negócio
  - atualiza dropdown, destaques locais e resumo do command center para usar origem/destino/intenção em vez de IDs crus
  - remove IDs de rota do resumo primário `quem supre quem`
  - humaniza blockers e warnings de readiness com rótulos de negócio quando o contexto do cenário está disponível
  - ajusta o foco do canvas para substituir `W`, `S` e `->` por linguagem operacional na superfície principal
- `tests/decision_platform/test_ui_smoke.py`
  - bloqueia regressão de `R001 ·`, `W ->` e outros rótulos crus na primeira dobra do Studio
  - atualiza expectativas de conectividade, foco e readiness para o novo vocabulário de negócio
- `output/ux_refinement_wave4_studio_snapshot.json`
  - snapshot estrutural atualizado com os textos reais do primeiro fold, incluindo labels do dropdown de rotas já limpos

## Validação executada

- `python -m py_compile src\decision_platform\ui_dash\app.py`
- `$env:PYTHONPATH='C:\d\dev\agri_circuit_optimizer_scaffold'; python -m pytest -q tests/decision_platform/test_studio_structure.py::test_dash_app_exposes_structural_studio_controls tests/decision_platform/test_studio_structure.py::test_create_route_between_business_nodes_adds_visible_route tests/decision_platform/test_studio_structure.py::test_apply_route_intent_from_edge_context_updates_matching_route tests/decision_platform/test_studio_structure.py::test_context_menu_action_starts_route_draft_from_selected_node tests/decision_platform/test_ui_smoke.py::test_studio_primary_surface_exposes_business_command_center tests/decision_platform/test_ui_smoke.py::test_studio_primary_workspace_avoids_technical_internal_terms tests/decision_platform/test_ui_smoke.py::test_studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas tests/decision_platform/test_ui_smoke.py::test_studio_focus_panel_uses_canvas_selection_as_primary_context tests/decision_platform/test_ui_smoke.py::test_studio_readiness_panel_humanizes_primary_blockers_and_warnings tests/decision_platform/test_ui_smoke.py::test_studio_workspace_panel_unifies_focus_connectivity_and_runs_gate tests/decision_platform/test_ui_smoke.py::test_studio_connectivity_panel_previews_reverse_action_in_business_language`

Resultado:

- `11 passed in 1.07s`

## Evidência gerada

- `output/ux_refinement_wave4_studio_snapshot.json`
  - registra o command center, o editor local de rotas, o workspace e o readiness já com labels de negócio
  - registra as opções reais do dropdown de rotas sem `R001 · W -> M` como rótulo primário

## Limites honestos

- Não consegui produzir `output/playwright/studio-fullhd-wave4.png` honestamente nesta onda.
- A tentativa com `Start-Process` para subir o app e capturar via navegador do sistema foi bloqueada pela política local do ambiente.
- A tentativa com Chrome headless usando `--screenshot` falhou sem gerar arquivo e registrou `CreateFile: Acesso negado. (0x5)` no stderr.
- Por isso, a evidência desta onda permanece estruturada e verificável, mas não rasterizada.

## Próximo passo sugerido

- Tratar esta fase como encerrada do ponto de vista de linguagem e surface cleanup do Studio e seguir para a próxima fase de UX concentrando o ganho operacional em Runs.
