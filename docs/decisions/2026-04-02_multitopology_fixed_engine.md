# 2026-04-02 - engine multitopologia por topologia fixa

## Contexto

O projeto precisava evoluir da estrela endurecida para um modo multitopologia sem reescrever o núcleo V1/V2/V3 nem abrir cedo demais o espaço combinatório de síntese livre.

## Decisões

1. A primeira entrega multitopologia entrou como engine de topologia fixa baseado em `edges.csv` e `topology_rules.yaml`.
2. A família existente `star_manifolds` foi preservada no pipeline atual:
   - preprocessamento por opções
   - Pyomo/fallback
   - seletividade por ramos
3. A nova família `bus_with_pump_islands` usa:
   - topologia instalada explícita por arestas
   - operação por rota validada por caminho ativo
   - seleção de bomba ativa e medidor de leitura por rota
   - grupos de conflito por caminho
4. A separação `core/service` foi aplicada no resumo do solve:
   - rotas `service` podem falhar sem tornar o cenário inviável se todas as rotas obrigatórias `core` forem atendidas
5. A comparação entre famílias foi implementada no nível de solução/relatório, não como problema único de otimização conjunta.

## Trade-offs

- O caminho estrela não foi migrado para arestas nesta rodada.
  Isso foi intencional para evitar regressão no que já estava estabilizado.
- O modo `bus_with_pump_islands` ainda não faz síntese estrutural.
  Ele valida e compara topologias fixas.
- A seletividade por caminho foi implementada com heurística conservadora para ramais/taps laterais.
  Segmentos lineares do barramento fora do caminho não são tratados automaticamente como conflito.

## Impacto prático

- `maquete_core` continua sendo a referência da estrela.
- `maquete_bus_manual` passa a demonstrar:
  - menor BOM de válvulas
  - separação entre topologia instalada e operação por rota
  - relatórios de caminho ativo
  - cobertura parcial/infeasibilidade explícita quando a topologia fixa não atende toda a demanda core

## Limitações remanescentes

- O motor multitopologia ainda não entra no Pyomo.
- A hidráulica no barramento continua simplificada por capacidade/perda equivalente.
- O comparador entre famílias ainda é pós-processado; não existe ainda um meta-solver escolhendo a melhor família sozinho.
- A estrela ainda não expõe internamente um grafo equivalente para comparação estrutural mais profunda.

## Próximos passos

1. adicionar mais cenários fixos de barramento/loop
2. enriquecer o validador de caminho com regras de inatividade neutra por família
3. criar adaptador interno da estrela para payload de arestas
4. só depois disso considerar síntese livre sobre supergrafo multitopologia
