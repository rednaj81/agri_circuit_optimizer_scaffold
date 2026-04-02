# Critérios de aceite

## Caso 1 — cenário mínimo viável
Deve ser possível validar as rotas básicas do cenário-exemplo:
- `W -> M`
- `W -> I`
- `P1 -> M`
- `I -> M`
- `I -> IR`
- `M -> S`

## Caso 2 — medição inadequada
Se a dose mínima e o erro máximo de uma rota forem incompatíveis com todos os fluxômetros,
o sistema deve marcar a combinação como inviável.

## Caso 3 — vazão mínima na saída
Se `M -> S` exigir vazão mínima, a solução deve atender `F_r >= q_min_delivered_lpm`.

## Caso 4 — bitola incompatível
O sistema deve rejeitar combinações inviáveis por bitola ou exigir adaptadores.

## Caso 5 — indisponibilidade
Componentes com `available_qty = 0` não podem ser usados.

## Caso 6 — proteção da água
Não pode existir rota válida entrando em `W`.
