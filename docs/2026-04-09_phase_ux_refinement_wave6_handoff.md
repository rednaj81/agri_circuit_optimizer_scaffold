# Phase UX Refinement Wave 6 Handoff

## Escopo executado

- Abri a frente principal de `ux_phase_3` pela área Runs, sem reabrir arquitetura nem reverter a baseline do Studio.
- Reorganizei a primeira dobra de Runs para separar cenário pronto, fila pendente, execução em andamento, histórico recente e próximo gesto do operador em linguagem de produto.
- Ampliei a leitura da run em foco com resumo operacional, eventos relevantes, artefatos/resultados e contexto técnico apenas por disclosure secundário, sem usar log bruto como superfície principal.
- Mantive explícita a transição Studio -> Runs, diferenciando quando o bloqueio está no cenário ainda não pronto e quando o foco já está na fila ou na execução.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - adiciona `run-jobs-operational-lanes` ao overview de Runs, separando fila pendente, execução agora, histórico recente e próximo gesto do operador;
  - amplia `render_runs_workspace_panel(...)` com a leitura `Limitação agora`, deixando explícito se o problema ainda está no Studio ou já está na execução;
  - transforma `render_run_job_detail_panel(...)` em uma leitura operacional da run em foco com resumo, eventos relevantes, artefatos/resultados e contexto técnico apenas por `Details`;
  - preserva logs e campos técnicos como disclosure secundário, fora da superfície primária de Runs.
- `tests/decision_platform/test_ui_smoke.py`
  - cobre a nova primeira dobra de Runs, a separação entre bloqueio de cenário e bloqueio de execução e a leitura operacional da run em foco sem log bruto.
- `tests/decision_platform/test_phase3_queue_acceptance.py`
  - adiciona cobertura direta da linguagem operacional de fila e detalhe de run, alinhando a frente de UX com a aceitação funcional de phase 3.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py tests/decision_platform/test_phase3_queue_acceptance.py -q`

Resultado:

- `111 passed, 1 skipped in 542.03s`

## Ganho real desta onda

- A área Runs agora deixa claro, na primeira leitura:
  - o que está pendente na fila;
  - o que está executando agora;
  - o que já virou histórico recente;
  - qual é a próxima ação recomendada para o operador.
- A run em foco passou a ser compreensível sem abrir logs:
  - resumo operacional;
  - eventos mais relevantes;
  - artefatos e resultados disponíveis;
  - contexto técnico só por disclosure.
- A transição Studio -> Runs ficou explícita:
  - se o cenário ainda trava, a UI diz isso;
  - se o cenário já passou no gate principal, o foco migra claramente para a fila e a execução.

## Limites honestos

- Não gerei screenshot bitmap nova nesta onda.
- A captura visual ficou fora da frente principal de trabalho porque o ganho principal foi funcional na área Runs e o runtime segue inconsistente para prova rasterizada honesta.
- Decision e technical tie continuam fora do foco principal desta wave, como definido pelo handoff.

## Próximo passo sugerido

- Prosseguir em `ux_phase_3` refinando leitura de histórico, progresso e ações locais de runs sem recair em backend plumbing ou logs como UI primária.
