# Phase UX Refinement Wave 2 Handoff

## Escopo executado

- Desloquei a criação de rota para um gesto direto no canvas: o operador pode iniciar a rota em uma entidade visível pelo menu contextual e concluir a criação ao selecionar a entidade de destino no grafo.
- Mantive a edição de intenção e particularidades de rota perto do canvas, com ações rápidas para `obrigatória`, `desejável` e `opcional`.
- Reforcei o menu contextual do Studio para incluir ações explícitas de rota no próprio grafo, sem recolocar o workbench técnico como caminho principal.
- Mantive o Studio na camada de negócio e preservei internals fora da superfície primária.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - adiciona `start-route-from-node` ao menu contextual do canvas
  - adiciona `studio-route-draft-source-id` e o fluxo `origem -> clique no destino` para criar rotas direto no canvas
  - adiciona ações rápidas locais para marcar intenção de rota sem depender do dropdown como caminho normal
  - amplia o menu contextual de aresta com ações de intenção de rota
  - endurece a superfície primária para esconder `junction` como foco técnico inicial do Studio
- `tests/decision_platform/test_studio_structure.py`
  - cobre criação de rota entre entidades de negócio
  - cobre início de draft de rota via menu contextual do canvas
  - cobre intenção de rota aplicada a partir de contexto local
- `tests/decision_platform/test_ui_smoke.py`
  - valida os novos controles locais de rota e as ações contextuais no Studio

## Validação executada

- `python -m py_compile src\decision_platform\ui_dash\app.py`
- `$env:PYTHONPATH='C:\d\dev\agri_circuit_optimizer_scaffold'; python -m pytest -q tests/decision_platform/test_studio_structure.py::test_dash_app_exposes_structural_studio_controls tests/decision_platform/test_studio_structure.py::test_create_route_between_business_nodes_adds_visible_route tests/decision_platform/test_studio_structure.py::test_apply_route_intent_from_edge_context_updates_matching_route tests/decision_platform/test_studio_structure.py::test_context_menu_action_starts_route_draft_from_selected_node tests/decision_platform/test_ui_smoke.py::test_studio_primary_surface_exposes_business_command_center`

Resultado:

- `5 passed in 0.64s`

## Evidência gerada

- `output/ux_refinement_wave2_studio_snapshot.json`
  - snapshot estrutural do Studio já montado pelo Dash
  - registra textos da primeira dobra, ações locais de rota, IDs do menu contextual e presença do store de draft de rota

## Limites honestos

- Não consegui produzir screenshot real em navegador nesta onda: o runtime local de Playwright/Chromium falhou com `spawn EPERM` e as ferramentas MCP de browser retornaram cancelamento no ambiente atual.
- A evidência visual desta onda ficou, portanto, em snapshot estruturado do layout Dash, não em captura bitmap Full HD.
- A ação contextual `create-route-from-edge` permanece útil apenas quando o trecho selecionado ainda não possui rota registrada; o caminho principal recomendado para criação agora é `iniciar rota daqui` no nó de origem e concluir no nó de destino.

## Próximo passo sugerido

- Fechar a próxima iteração do Studio na leitura imediata da rota em foco e na coerência entre projeção de rota e contexto local, antes de avançar para a fase de Runs.
