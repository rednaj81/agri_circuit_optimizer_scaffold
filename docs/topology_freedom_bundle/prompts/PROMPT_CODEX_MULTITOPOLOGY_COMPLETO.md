# Prompt completo para Codex — evolução multitopologia

Leia primeiro, nesta ordem:
1. README.md do repositório
2. AGENTS.md
3. docs/decisions/
4. docs/topology_freedom_bundle/README.md
5. docs/topology_freedom_bundle/01_context_and_goal.md
6. docs/topology_freedom_bundle/02_key_definitions_frozen.md
7. docs/topology_freedom_bundle/03_target_architecture_multitopology.md
8. docs/topology_freedom_bundle/04_data_contract_extensions.md
9. docs/topology_freedom_bundle/05_modeling_and_solver_changes.md
10. docs/topology_freedom_bundle/06_execution_plan_codex.md
11. docs/topology_freedom_bundle/07_acceptance_tests.md
12. docs/topology_freedom_bundle/09_manual_proposal_interpretation.md

## Objetivo desta rodada

Evoluir o projeto de uma única superestrutura fixa em estrela para um modo **multitopologia**, preservando a família atual e adicionando capacidade de validar/comparar pelo menos uma nova família topológica inspirada nas propostas manuais do usuário: `bus_with_pump_islands`.

A grande mudança conceitual é:
- parar de forçar que toda rota seja explicada só pela estrela endurecida
- passar a validar se existe um **caminho hidráulico seletivo e mensurável** para cada rota, dentro de uma topologia instalada

## Decisões congeladas
- não adicionar novos tipos de válvula
- continuar usando os tipos físicos de componente já existentes
- separar:
  - topologia instalada
  - operação por rota
- manter `star_manifolds`
- implementar `bus_with_pump_islands`
- priorizar **topologia fixa validável** antes de síntese livre total
- não tratar o problema principal como CFD/pressão contínua

## O que implementar

### 1. Infraestrutura multitopologia
Adicionar suporte a:
- `topology_family`
- `edges.csv`
- `topology_rules.yaml`
- representação baseada em arestas para nova família
- adaptador gradual da família estrela para payload equivalente

### 2. Validador de rota por caminho
Criar uma camada que, para cada rota:
- encontre um caminho ativo entre source e sink
- respeite direção das arestas
- respeite grupos de conflito
- escolha bomba ativa válida
- escolha um único medidor de leitura válido quando exigido
- trate seletividade como propriedade do caminho ativo

### 3. Família nova: bus_with_pump_islands
Implementar uma família topológica baseada em:
- barramento principal
- taps valvulados dos tanques
- ilhas de bomba + medição em arestas específicas
- loops/bypasses superiores ou laterais
- possibilidade de bombas instaladas porém inativas para a rota corrente
- possibilidade de medidores instalados porém não usados como leitura na rota corrente

### 4. Separação entre rotas core e service
Permitir que rotas como `I -> IR` sejam marcadas como `service`, para que a comparação topológica principal não fique artificialmente distorcida por um serviço local que pode ser atendido por subcircuito dedicado.

### 5. Comparação entre famílias
Criar ou adaptar cenários para comparar:
- `star_manifolds`
- `bus_with_pump_islands`

No mesmo conjunto de demanda, com relatório comparativo de:
- válvulas
- T's
- mangueira
- bombas instaladas
- fluxômetros instalados
- caminhos ativos por rota
- rotas obrigatórias atendidas
- rotas opcionais atendidas
- seletividade
- gargalo/hidráulica simplificada

## Restrições técnicas importantes

### A. Não quebrar a família estrela
Os testes atuais de `example` e `maquete_core` precisam continuar válidos ou ser adaptados de modo controlado, sem regressão conceitual.

### B. Não reescrever tudo de uma vez
Implementar em etapas:
1. loader/contrato
2. validador de topologia fixa
3. nova família
4. comparação
5. eventual síntese livre depois

### C. Não assumir mais "uma bomba por rota" como dogma estrutural
No novo motor:
- pode haver várias bombas instaladas no circuito
- mas cada rota deve respeitar `max_active_pumps_per_route`, via regra da família
- padrão inicial recomendado: `<= 1`

O mesmo vale para medidores:
- podem existir vários instalados
- cada rota escolhe no máximo um medidor de leitura
- outros medidores instalados podem ficar operativamente neutros

### D. Seleção por caminho, não por sucção/descarga global
A regra "um ramo de sucção e um ramo de descarga" continua válida para a estrela, mas não deve ser imposta universalmente ao barramento.

## Entregáveis desta rodada
1. código implementado
2. cenários/arquivos novos necessários
3. testes novos e regressão passando
4. documentação atualizada em `docs/decisions/`
5. resumo final com:
   - arquivos alterados
   - decisões tomadas
   - diferenças entre famílias
   - limitações remanescentes
   - próximos passos recomendados

## Execução recomendada
Siga o plano técnico em:
- docs/topology_freedom_bundle/06_execution_plan_codex.md
- docs/topology_freedom_bundle/tasks/

Comece com um plano curto de implementação e depois execute.