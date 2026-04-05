# Fases definidas para evolução

## Fase 0 — baseline e truthfulness
- confirmar branch e baseline
- remover ambiguidades de runtime
- garantir Julia only no caminho oficial
- consolidar fail-closed

## Fase 1 — domínio e persistência
- normalizar modelo de cenário
- normalizar banco de componentes
- normalizar rotas obrigatórias
- criar storage confiável para cenários, runs e artefatos

## Fase 2 — studio de nós e arestas
- editor visual
- criação de nós
- criação de arestas
- grupos de conflito
- propriedades visuais e técnicas
- salvar/reabrir cenário

## Fase 3 — fila e background runs
- orquestrador de jobs
- monitoramento de fila
- status por run
- logs
- artefatos
- isolamento entre execuções

## Fase 4 — engine Julia forte
- bridge robusto
- execução real
- métricas por rota
- classificação de inviabilidade
- comparação entre engines de referência, se necessário
- remover dependências residuais de fallback no caminho oficial

## Fase 5 — decisão humana assistida
- ranking multicritério
- perfis de peso
- filtros
- comparação lado a lado
- vencedor vs runner-up
- explicabilidade

## Fase 6 — estabilização
- erros
- UX
- performance
- documentação
- handoff limpo
