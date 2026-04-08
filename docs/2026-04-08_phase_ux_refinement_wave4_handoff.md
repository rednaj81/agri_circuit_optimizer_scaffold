# Phase UX Refinement Wave 4 Handoff

## Escopo executado

- Simplifiquei o estado do fluxo route-first do Studio para operar a partir do `studio-route-composer-state`, removendo a dependência do draft legado como trilha principal.
- Mantive a edição comum de rota perto do canvas: intenção, medição direta, vazão mínima, dosagem mínima e observação curta continuam acessíveis no fluxo local.
- Reforcei o preview da rota em preparo no painel local e no canvas com leitura explícita de origem, destino, intenção e readiness.
- Fechei a onda com uma evidência estrutural verificável da primeira dobra do Studio em `docs/2026-04-08_phase_ux_refinement_wave4_ui_snapshot.json`, extraída do layout servido pelo próprio app.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - centraliza o fluxo de composição de rota em `studio-route-composer-state`;
  - remove a dependência do store legado `studio-route-draft-source-id` da superfície principal;
  - adiciona helpers dedicados para normalizar o composer e montar o preview local da rota;
  - projeta uma aresta temporária `route-composer-preview` no canvas quando origem e destino já existem no grafo de negócio visível;
  - confirma a rota já aplicando intenção e particularidades preventivas diretamente no fluxo local.
- `tests/decision_platform/test_ui_smoke.py`
  - valida o composer explícito e o fluxo local de iniciar, completar, editar, confirmar e limpar a rota sem depender do workbench avançado.
- `tests/decision_platform/test_studio_structure.py`
  - valida a presença estrutural do composer e da aresta de preview no canvas primário.
- `docs/2026-04-08_phase_ux_refinement_wave4_ui_snapshot.json`
  - registra a leitura da primeira dobra do Studio a partir do layout servido pelo app, incluindo grid principal, painéis críticos e seus textos.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q`

Resultado:

- `98 passed, 1 skipped in 461.69s`

## Evidência gerada

- `docs/2026-04-08_phase_ux_refinement_wave4_ui_snapshot.json`
  - captura estrutural da primeira dobra do Studio a partir de `/_dash-layout` via `build_app().server.test_client()`;
  - registra o grid principal `minmax(0, 1.75fr) minmax(360px, 430px)`, confirmando o canvas como coluna dominante em Full HD;
  - registra os textos reais de `studio-command-center-panel`, `studio-route-editor-panel`, `studio-route-composer-preview-panel`, `studio-business-flow-panel`, `studio-readiness-panel`, `studio-focus-panel` e `studio-canvas-guidance-panel`.

## Limites honestos

- Não consegui gerar uma captura bitmap nova da primeira dobra nesta onda.
- A tentativa de abrir o app local via MCP Playwright foi cancelada pelo ambiente e as tentativas de captura headless locais falharam com restrições de execução do navegador.
- Por isso, a evidência final desta onda é estrutural e verificável, mas não rasterizada.

## Próximo passo sugerido

- A próxima onda pode sair do Studio e atacar `ux_phase_3`, focando runs/fila com a mesma regra: leitura operacional primeiro, logs e detalhes técnicos apenas por disclosure progressivo.
