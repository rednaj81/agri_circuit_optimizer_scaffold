# Phase UX Refinement Wave 5 Handoff

## Escopo executado

- Consolidei guard-rails automatizados de saída da `ux_phase_2` para impedir retorno de IDs crus e setas técnicas no primeiro fold do Studio.
- Gereei um snapshot final de transição da fase com o baseline route-first, business graph only e readiness preventivo já estabilizados.
- Revalidei o Studio no estado atual com foco em command center, dropdown de rotas, foco contextual, conectividade e readiness antes da passagem para Runs.

## Mudanças principais

- `tests/decision_platform/test_studio_structure.py`
  - adiciona regressão direta para garantir que `_route_choice_options(...)` prefira rótulos de negócio em vez de `R001` ou `->`
- `tests/decision_platform/test_ui_smoke.py`
  - adiciona regressão no app montado para garantir que o dropdown primário de rotas e o painel de readiness não recaiam para IDs crus ou setas técnicas
- `output/ux_refinement_wave5_phase_exit_snapshot.json`
  - registra o estado de saída da fase com checklist objetivo de transição para `ux_phase_3`

## Validação executada

- `$env:PYTHONPATH='C:\d\dev\agri_circuit_optimizer_scaffold'; python -m pytest -q tests/decision_platform/test_studio_structure.py::test_dash_app_exposes_structural_studio_controls tests/decision_platform/test_studio_structure.py::test_route_choice_options_use_business_labels_before_technical_ids tests/decision_platform/test_studio_structure.py::test_create_route_between_business_nodes_adds_visible_route tests/decision_platform/test_studio_structure.py::test_apply_route_intent_from_edge_context_updates_matching_route tests/decision_platform/test_studio_structure.py::test_context_menu_action_starts_route_draft_from_selected_node tests/decision_platform/test_ui_smoke.py::test_studio_primary_surface_exposes_business_command_center tests/decision_platform/test_ui_smoke.py::test_studio_primary_workspace_avoids_technical_internal_terms tests/decision_platform/test_ui_smoke.py::test_studio_route_focus_dropdown_keeps_business_language_in_primary_surface tests/decision_platform/test_ui_smoke.py::test_studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas tests/decision_platform/test_ui_smoke.py::test_studio_focus_panel_uses_canvas_selection_as_primary_context tests/decision_platform/test_ui_smoke.py::test_studio_readiness_panel_humanizes_primary_blockers_and_warnings tests/decision_platform/test_ui_smoke.py::test_studio_workspace_panel_unifies_focus_connectivity_and_runs_gate tests/decision_platform/test_ui_smoke.py::test_studio_connectivity_panel_previews_reverse_action_in_business_language`

Resultado:

- `13 passed in 1.54s`

## Evidência gerada

- `output/ux_refinement_wave5_phase_exit_snapshot.json`
  - confirma a baseline obrigatória da fase: business graph only, criação/edição contextual de rotas, supply-flow legível e readiness preventivo
  - registra um checklist explícito de transição para `ux_phase_3`

## Encerramento de fase

- A baseline de `ux_phase_2` fica consolidada como obrigatória para as próximas ondas:
  - Studio abre em linguagem de negócio
  - canvas principal mantém apenas o business graph editável
  - criação e edição de rotas permanecem contextuais e próximas ao grafo
  - leitura `quem supre quem` permanece visível no primeiro fold
  - readiness preventivo continua antes da passagem para Runs

## Limites honestos

- Não consegui anexar `output/playwright/studio-fullhd-wave5.png`.
- A exigência de screenshot bitmap Full HD continua bloqueada pelo ambiente atual.
- Nesta onda, novas tentativas com navegador headless do sistema não geraram PNG verificável do Studio.
- Assim, `ux_phase_2` fica tecnicamente consolidada por testes e snapshot estruturado, mas ainda sem prova rasterizada honesta neste runtime.

## Próximo passo sugerido

- Avançar para `ux_phase_3` somente se o supervisor aceitar o bloqueio ambiental da evidência bitmap como exceção operacional documentada; caso contrário, tratar a captura rasterizada como impedimento externo verificável e não como lacuna de fluxo do produto.
