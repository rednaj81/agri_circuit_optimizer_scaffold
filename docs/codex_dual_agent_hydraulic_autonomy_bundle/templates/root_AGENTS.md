# AGENTS.md — hydraulic decision platform

Este repositório opera com um loop controlado de evolução:

- Architect
- Developer
- Auditor

## Regra principal
Não reabrir arquitetura sem justificativa objetiva.
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

## Estado-alvo do produto
- editor visual de nós e arestas
- banco de componentes
- queue/background runs
- cenários isolados
- ranking multicritério
- UI de decisão
- export completo do candidato oficial

## Regra de honestidade
Nunca mascarar fallback.
Se o caminho oficial depende de Julia e Julia não estiver realmente operando, falhar fechado e documentar.
