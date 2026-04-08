# Phase UX Refinement Wave 1 Handoff

## Escopo executado

- Reorientei a primeira dobra do Studio para um fluxo route-first.
- Mantive o canvas como superfície principal e preservei hubs/internals fora da camada primária.
- Adicionei edição local de rota no primeiro fold para intenção, vazão mínima, dosagem, medição direta e observação visível.
- Reforcei a leitura "quem supre quem" e a contagem de rotas obrigatórias, desejáveis e opcionais no Studio.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - introduz helpers de intenção de rota (`mandatory`, `desirable`, `optional`)
  - adiciona `render_studio_route_editor_panel` com edição direta perto do canvas
  - ajusta o command center para abrir pela definição das rotas a servir
  - projeta intenção de rota no Cytoscape com estilos distintos
  - expõe métricas de rotas desejáveis e opcionais no readiness do Studio
- `tests/decision_platform/test_studio_structure.py`
  - cobre o painel local de rotas e a mutação da intenção
  - cobre a marcação visual de rotas desejáveis na projeção principal
- `tests/decision_platform/test_ui_smoke.py`
  - valida a presença do editor local de rotas e a copy route-first do command center

## Validação executada

- `python -m py_compile src\decision_platform\ui_dash\app.py`
- `python -m pytest -q tests/decision_platform/test_studio_structure.py::test_dash_app_exposes_structural_studio_controls tests/decision_platform/test_studio_structure.py::test_route_focus_edit_updates_intent_and_measurement_flags tests/decision_platform/test_studio_structure.py::test_primary_studio_projection_marks_desirable_routes_in_canvas_classes tests/decision_platform/test_ui_smoke.py::test_studio_primary_surface_exposes_business_command_center`

Resultado:

- `4 passed in 0.53s`

## Limites honestos

- Não gerei nova evidência Playwright nesta onda; a validação visual ficou limitada à estrutura Dash e aos testes.
- A edição route-first ficou concentrada na revisão e no ajuste das rotas existentes ligadas ao foco atual; a criação explícita de novos registros em `route_requirements.csv` ainda permanece no trilho avançado/canônico.
- A suite completa dos dois arquivos de teste continuou excedendo o tempo disponível no ambiente, então registrei e usei a validação direcionada dos comportamentos alterados.

## Próximo passo sugerido

- Fechar a próxima onda no fluxo de fila/Runs sem reabrir shell ou arquitetura, aproveitando o novo readiness route-first já visível no Studio.
