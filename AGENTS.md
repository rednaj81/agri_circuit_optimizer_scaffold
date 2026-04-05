# AGENTS.md

Este repositório opera com um loop controlado de evolução:

- Architect
- Developer
- Auditor

## Regra principal

Não reabrir arquitetura sem justificativa objetiva.
O problema funcional já está congelado na documentação.

Priorizar:

- Julia only no caminho oficial
- studio visual
- banco de componentes
- rotas obrigatórias
- fila de cenários
- decisão humana assistida
- explicabilidade

## Política de ondas

- máximo de 10 ondas
- parada por 3 ondas consecutivas sem avanço relevante segundo o Auditor
- 1 onda final de polimento/estabilização
- commit obrigatório por onda
- handoff obrigatório por onda

## Ordem funcional congelada

A implementação do produto hidráulico deve respeitar a evolução incremental:

1. V1 — topologia + custo + vazão mínima
2. V2 — medição direta + dosagem
3. V3 — bitolas + perdas + folga hidráulica

## Estado-alvo do produto

- editor visual de nós e arestas
- banco de componentes
- queue/background runs
- cenários isolados
- ranking multicritério
- UI de decisão
- export completo do candidato oficial

## Regras operacionais

- Não modelar simultaneidade no MVP.
- Não permitir rotas entrando em `W`.
- Não permitir rotas saindo de `S`.
- Exigir medição direta em rotas com dosagem.
- Usar superestrutura em camadas.
- Preservar o contrato de dados descrito em `docs/05_data_contract.md`.
- Antes de adicionar complexidade, fazer os testes de aceite passarem.
- Evitar refatorações destrutivas entre V1, V2 e V3.
- Nunca mascarar fallback.
- Se o caminho oficial depender de Julia e Julia não estiver realmente operando, falhar fechado e documentar.

## Papéis sugeridos

- `Architect`: define fase, onda, critérios de aceite, arquivos-alvo e riscos
- `Developer`: implementa incrementalmente, valida, documenta e prepara commit
- `Auditor`: classifica a significância do avanço, detecta regressões e decide continuidade

## Entregáveis mínimos

- parser e validação de cenário
- geração de opções/ramais
- modelo Pyomo montado por módulos
- runner de cenário
- relatórios de BOM, rotas, hidráulica e medição
- testes cobrindo aceite mínimo

## Fontes de verdade para o loop autônomo

- `docs/codex_dual_agent_hydraulic_autonomy_bundle/overview/`
- `docs/codex_dual_agent_hydraulic_autonomy_bundle/product/`
- `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/`
- `docs/codex_dual_agent_hydraulic_autonomy_bundle/data_samples/`
