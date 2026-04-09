# Phase UX Refinement Wave 9 Handoff

## Escopo executado

- Aprofundei a UX de `Decisão` para a comparação final assistida, sem reabrir scoring, ranking ou arquitetura.
- Tornei explícita a diferença entre `referência oficial do produto`, `winner do perfil em leitura`, `runner-up comparável` e `escolha manual atual`.
- Dei ao `technical tie` um estado próprio e legível na superfície principal, com leitura humana assistida e razões resumidas do empate.
- Alinhei o CTA de export ao candidato efetivamente escolhido no contexto atual, sem sobrescrever silenciosamente a referência oficial.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - amplia `render_decision_workspace_panel(...)` com:
    - `decision-final-comparison-panel` para a comparação lado a lado entre referência oficial, winner do perfil, runner-up e escolha manual;
    - `decision-final-choice-panel` para expor a decisão manual atual e o impacto no export;
  - amplia `render_decision_contrast_panel(...)` com `decision-technical-tie-panel`, dando estado próprio ao empate técnico em linguagem de produto;
  - mantém o mapa de trade-offs por perfil como suporte da decisão assistida, sem trazer grids técnicos para a dobra principal;
  - adiciona `_refresh_decision_export_cta(...)` para que o botão `export-selected-button` reflita se o export atual seguirá:
    - a referência oficial;
    - o winner do perfil atual;
    - uma escolha manual alternativa.
- `tests/decision_platform/test_ui_smoke.py`
  - cobre a comparação final assistida na dobra principal;
  - cobre o estado explícito de `technical tie` como decisão humana assistida;
  - cobre a coerência do CTA de export com a escolha manual atual.
- `docs/2026-04-09_phase_ux_refinement_wave9_decision_snapshot.json`
  - registra a evidência estrutural da nova dobra principal de Decisão.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py tests/decision_platform/test_phase3_queue_acceptance.py -q`

Resultado:

- `114 passed, 1 skipped in 466.43s`

## Ganho real desta onda

- A primeira dobra de Decisão agora deixa explícito:
  - o que continua sendo a referência oficial do produto;
  - qual é o winner do perfil atual;
  - quem é o runner-up comparável;
  - qual candidato está manualmente escolhido para seguir;
  - qual candidato o export realmente seguirá.
- O `technical tie` deixou de ser apenas um rótulo e passou a explicar:
  - que não existe vencedor inequívoco;
  - que a escolha final depende de decisão humana assistida;
  - quais fatores resumidos sustentam o empate.
- O export deixou de ser um CTA genérico:
  - quando a escolha manual coincide com a referência oficial, o botão explicita isso;
  - quando coincide com o winner do perfil atual, isso também fica explícito;
  - quando a escolha é uma alternativa manual, o CTA deixa isso claro.

## Evidência registrada

- Snapshot estrutural: `docs/2026-04-09_phase_ux_refinement_wave9_decision_snapshot.json`

Sinais verificáveis no snapshot:

- `decision-final-comparison-panel` mostra lado a lado referência oficial, winner do perfil, runner-up e escolha manual;
- `decision-final-choice-panel` mostra o candidato manual atual e que o export não sobrescreve silenciosamente a referência oficial;
- `decision-technical-tie-panel` mostra o empate como estado próprio de decisão humana assistida;
- `decision-workspace-panel` reúne esses sinais na primeira dobra sem depender de grids ou payloads técnicos.

## Limites honestos

- Não consegui gerar `output/playwright/decision-wave9-fullhd.png` de forma honesta neste ambiente.
- A evidência desta onda ficou estrutural, não bitmap, embora derive do layout real servido pelo app Dash.
- A escolha manual continua apoiada no `selected-candidate-dropdown` já existente; esta wave expôs essa decisão na superfície principal, mas não criou um novo subsistema de aprovação persistente fora do estado atual da UI.

## Próximo passo sugerido

- Entrar na onda final de polimento/estabilização para consolidar consistência visual, linguagem e evidências honestas entre Studio, Runs, Decisão e Auditoria.
