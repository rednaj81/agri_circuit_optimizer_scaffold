# UX Phase 3 Open

## Estado

- `ux_phase_3` aberta.

## Transição recebida

- `ux_phase_2` foi encerrada com Studio estabilizado em:
  - business graph only;
  - route-first suficiente;
  - edição direta comum no canvas;
  - readiness legível;
  - ausência de internos técnicos na superfície principal.

## Foco operacional inicial

- Tornar Runs compreensível como superfície de produto para:
  - fila atual;
  - execução em foco;
  - histórico recente;
  - passagem para Decisão;
  - retorno ao Studio só quando a limitação ainda for do cenário.

## Decisão desta abertura

- A primeira dobra de Runs passa a separar explicitamente:
  - o que está na fila;
  - qual execução merece atenção agora;
  - o que o histórico recente já liberou ou ainda bloqueia.

## Restrições mantidas

- Não usar logs brutos, paths ou payloads crus como leitura primária.
- Manter Studio fora da frente principal, salvo correção de regressão.
- Preservar arquitetura atual, caminho oficial Julia-only e comportamento fail-closed.

## Próximos passos sugeridos

- Refinar recuperação direta de fila e run em foco.
- Tornar mais clara a diferença entre bloqueio operacional, cancelamento, rerun e resultado utilizável.
- Preparar a transição Runs -> Decisão com winner, runner-up e technical tie legíveis na fase seguinte.

