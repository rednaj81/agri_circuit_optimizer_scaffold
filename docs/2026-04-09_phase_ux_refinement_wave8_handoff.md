# Phase UX Refinement Wave 8 Handoff

## Escopo executado

- Abri a frente principal de `ux_phase_4` pela área `Decisão`, sem reabrir ranking, solver ou arquitetura.
- Transformei a primeira dobra de Decisão em leitura orientada por perfis explícitos já existentes no produto: `Menor custo`, `Equilibrado`, `Robustez primeiro` e `Higienização primeiro`.
- Preservei o candidato oficial como referência explícita do produto mesmo quando a leitura atual muda de perfil, evitando sobrescrita silenciosa da decisão oficial.
- Tornei winner, runner-up e technical tie mais legíveis na superfície primária e adicionei um resumo de trade-offs por perfil sem usar tabelas densas, JSON ou engine comparison como interface principal.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - adiciona apresentação em linguagem de produto para os perfis de ranking já existentes;
  - amplia `build_official_candidate_summary(...)` com `official_profile_id`, `official_product_candidate_id` e `profile_views`, preservando a referência oficial ao mesmo tempo em que expõe a leitura do perfil ativo;
  - evolui `render_decision_workspace_panel(...)` com `decision-profile-views-panel`, colocando os perfis explícitos de seleção na primeira dobra;
  - evolui `render_decision_summary_panel(...)` para distinguir `Winner oficial` de `Winner do perfil atual`, mantendo a referência oficial visível;
  - evolui `render_decision_contrast_panel(...)` com `decision-profile-tradeoff-panel`, resumindo por perfil quais famílias/candidatos passam a liderar e por quê;
  - evolui `render_decision_flow_panel(...)` para deixar explícito qual perfil está em leitura e qual continua sendo a referência oficial do produto;
  - melhora os rótulos do `profile-dropdown` para nomes de produto em vez de IDs crus.
- `tests/decision_platform/test_ui_smoke.py`
  - cobre a nova leitura por perfil na superfície principal de Decisão;
  - protege a preservação da referência oficial quando o perfil ativo muda;
  - protege o novo painel de trade-offs por perfil e a manutenção de disclosure progressivo nas superfícies primárias.
- `docs/2026-04-09_phase_ux_refinement_wave8_decision_snapshot.json`
  - registra a evidência estrutural da dobra principal de Decisão servida pelo app.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py tests/decision_platform/test_phase3_queue_acceptance.py -q`

Resultado:

- `113 passed, 1 skipped in 448.78s`

## Ganho real desta onda

- A primeira dobra de Decisão agora deixa explícito:
  - qual perfil está governando a leitura atual;
  - qual continua sendo o perfil/candidato oficial do produto;
  - se há vencedor claro, empate técnico ou contraste fraco;
  - como perfis diferentes podem preferir winners diferentes sem reabrir o ranking.
- O operador consegue comparar, na superfície principal:
  - `winner atual`;
  - `runner-up`;
  - `technical tie`;
  - `trade-offs por perfil`;
  - `referência oficial do produto`.
- A UI deixa de sugerir silenciosamente que o winner do perfil alternativo substitui o candidato oficial exportado.

## Evidência registrada

- Snapshot estrutural: `docs/2026-04-09_phase_ux_refinement_wave8_decision_snapshot.json`

Sinais verificáveis nesse snapshot:

- `decision-workspace-panel` mostra `Perfil em leitura`, `Referência oficial do produto` e `Perfis explícitos de seleção`;
- `decision-summary-panel` preserva `Winner oficial` quando o perfil oficial está ativo;
- `decision-contrast-panel` mostra `Trade-offs por perfil` e winners diferentes entre custo e equilíbrio;
- `decision-flow-panel` torna explícita a referência oficial enquanto o perfil ativo muda.

## Limites honestos

- Não consegui gerar `output/playwright/decision-wave8-fullhd.png` de forma honesta neste ambiente.
- A evidência visual desta onda ficou estrutural, não bitmap, embora derive do layout real servido pelo app Dash.
- Esta wave não reabriu engine comparison, technical tie detalhado de auditoria ou ranking backend; ela só melhorou a leitura de UX sobre perfis já existentes.

## Próximo passo sugerido

- Aprofundar `ux_phase_4` na comparação assistida final entre winner, runner-up e technical tie, mantendo export, decisão humana e trilha técnica secundária coerentes com o perfil selecionado.
