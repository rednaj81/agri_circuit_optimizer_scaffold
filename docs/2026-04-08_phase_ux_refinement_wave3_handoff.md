# Phase UX Refinement Wave 3 Handoff

## Escopo executado

- Fechei o principal vazamento de internals na primeira dobra do Studio: a seleção inicial não cai mais em `candidate_links` técnicas invisíveis.
- Mantive o Studio como business graph only na superfície primária, sem `Junção`, `Tap` ou hubs como foco textual dominante.
- Preservei a criação/edição contextual de rotas no canvas introduzida na onda anterior.
- Atualizei a cobertura de UI para garantir que termos técnicos internos não reapareçam nas superfícies primárias do Studio.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - `_build_edge_studio_summary(...)` agora respeita ausência real de seleção em vez de cair na primeira aresta técnica do bundle
  - `render_studio_command_center_panel(...)` limpa a linguagem quando não existe trecho selecionado e evita `-` como foco aparente
  - `_studio_quick_link_defaults(...)` passou a tolerar `selected_edge = None` no fluxo limpo do Studio
  - o Studio continua ocultando `junction`/internals da superfície primária
- `tests/decision_platform/test_ui_smoke.py`
  - adiciona guard-rails explícitos para garantir ausência de `Tap`, `Junção` e `Hub estrela` na primeira dobra do Studio
- `output/ux_refinement_wave3_studio_snapshot.json`
  - snapshot estrutural do Studio já limpo, mostrando foco inicial em entidade de negócio e ações contextuais de rota

## Validação executada

- `python -m py_compile src\decision_platform\ui_dash\app.py`
- `$env:PYTHONPATH='C:\d\dev\agri_circuit_optimizer_scaffold'; python -m pytest -q tests/decision_platform/test_studio_structure.py::test_dash_app_exposes_structural_studio_controls tests/decision_platform/test_studio_structure.py::test_create_route_between_business_nodes_adds_visible_route tests/decision_platform/test_studio_structure.py::test_apply_route_intent_from_edge_context_updates_matching_route tests/decision_platform/test_studio_structure.py::test_context_menu_action_starts_route_draft_from_selected_node tests/decision_platform/test_ui_smoke.py::test_studio_primary_surface_exposes_business_command_center tests/decision_platform/test_ui_smoke.py::test_studio_primary_workspace_avoids_technical_internal_terms`

Resultado:

- `6 passed in 1.14s`

## Evidência gerada

- `output/ux_refinement_wave3_studio_snapshot.json`
  - mostra a dobra principal sem foco técnico inicial
  - registra ações contextuais locais de rota no canvas
  - registra o texto do Studio já limpo de `Tap` e `Junção` na superfície primária

## Limites honestos

- Não consegui anexar `output/playwright/studio-fullhd-wave3.png`: a captura rasterizada em Full HD continuou bloqueada pelo ambiente.
- Tentativas com Playwright falharam com `spawn EPERM`.
- Tentativas com navegador real + screenshot de janela do sistema ficaram bloqueadas pela política local ao abrir a GUI do browser.
- Por isso, a evidência desta onda ficou em snapshot estrutural rastreável e não em screenshot bitmap.

## Próximo passo sugerido

- Seguir para `ux_phase_3` com o Studio já limpo na camada primária e usar o mesmo padrão de business-language + progressive disclosure em Runs.
