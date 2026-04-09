# Phase UX Refinement Wave 5 Handoff

## Escopo executado

- Transformei a readiness do Studio em uma fila local de correção orientada por negócio, com itens acionáveis que levam o operador de volta ao trecho certo do canvas.
- Fechei o round-trip entre blocker e edição local: o item da readiness agora reposiciona o foco do Studio em conexão ou entidade relevante, mantendo a correção no fluxo principal sem workbench obrigatório.
- Reforcei a explicação de impacto operacional na primeira dobra, mostrando quem deixa de suprir quem, por que Runs continua travado e qual é o próximo gesto recomendado no canvas.
- Mantive a superfície principal no grafo de negócio e adicionei evidência estrutural nova da dobra principal com a fila acionável em `docs/2026-04-08_phase_ux_refinement_wave5_ui_snapshot.json`.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - adiciona helpers para derivar itens acionáveis da readiness a partir de bloqueios e avisos reais;
  - introduz a seção `Fila local de correção` no `studio-readiness-panel`, com cards de bloqueio/aviso, impacto em Runs e próximo gesto no canvas;
  - conecta os botões `Trazer para o canvas` ao foco atual do Studio, selecionando o trecho relevante no grafo e atualizando a mensagem operacional local;
  - amplia o painel de readiness com `Impacto operacional`, sem reexpor hubs, nós internos ou JSON cru.
- `tests/decision_platform/test_ui_smoke.py`
  - cobre a nova fila acionável, o texto preventivo da readiness e o callback que leva um bloqueio estrutural direto ao foco do canvas.
- `tests/decision_platform/test_studio_structure.py`
  - protege a presença estrutural da fila de correção e dos botões acionáveis do painel de readiness.
- `docs/2026-04-08_phase_ux_refinement_wave5_ui_snapshot.json`
  - registra o estado real da primeira dobra do Studio com a fila de correção acionável e o bloqueio honesto de captura rasterizada.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q`

Resultado:

- `99 passed, 1 skipped in 485.41s`

## Evidência gerada

- `docs/2026-04-08_phase_ux_refinement_wave5_ui_snapshot.json`
  - snapshot estrutural extraído do layout servido pelo próprio app;
  - registra o texto real do `studio-readiness-panel`, da `studio-readiness-action-queue`, do `studio-focus-panel` e do `studio-route-editor-panel`;
  - confirma que a primeira dobra agora mostra a fila local de correção com impacto em Runs e ação direta `Trazer para o canvas`.

## Limites honestos

- Não consegui gerar `output/playwright/studio-wave5-fullhd.png`.
- O Chrome headless local falhou repetidamente com `CreateFile: Acesso negado. (0x5)` ao tentar lançar o fluxo de captura neste ambiente.
- A evidência desta onda ficou estrutural e verificável, mas não rasterizada.

## Encerramento de fase

- Do ponto de vista funcional, `ux_phase_2` fica pronta para transição:
  - Studio abre com grafo de negócio como superfície principal;
  - fluxo route-first segue local ao canvas;
  - readiness deixou de ser leitura passiva e virou trilha acionável de correção;
  - as correções mais comuns continuam possíveis sem retorno obrigatório ao workbench.

## Próximo passo sugerido

- Migrar para `ux_phase_3` e aplicar o mesmo padrão em Runs: fila legível, próxima ação operacional clara e logs técnicos apenas por disclosure progressivo.
