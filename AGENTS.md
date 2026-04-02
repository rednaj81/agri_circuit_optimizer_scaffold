# AGENTS.md

Este projeto foi estruturado para execução com Codex 5.4 em modo incremental.

## Regra de ouro

O agente não deve reabrir o escopo conceitual. O problema já está congelado na documentação.
A implementação deve seguir a ordem:

1. V1 — topologia + custo + vazão mínima
2. V2 — medição direta + dosagem
3. V3 — bitolas + perdas + folga hidráulica

## Regras operacionais

- Não modelar simultaneidade no MVP.
- Não permitir rotas entrando em `W`.
- Não permitir rotas saindo de `S`.
- Exigir medição direta em rotas com dosagem.
- Usar superestrutura em camadas.
- Preservar o contrato de dados descrito em `docs/05_data_contract.md`.
- Antes de adicionar complexidade, fazer os testes de aceite passarem.
- Evitar refatorações destrutivas entre V1, V2 e V3.

## Papéis sugeridos

- `agents/codex-5.4-orchestrator.md`
- `agents/codex-5.4-data-contract-agent.md`
- `agents/codex-5.4-model-engineer.md`
- `agents/codex-5.4-test-engineer.md`
- `agents/codex-5.4-reporting-agent.md`

## Entregáveis mínimos

- parser e validação de cenário
- geração de opções/ramais
- modelo Pyomo montado por módulos
- runner de cenário
- relatórios de BOM, rotas, hidráulica e medição
- testes cobrindo aceite mínimo
