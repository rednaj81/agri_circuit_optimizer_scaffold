# Pipeline de processamento

## Etapa 0 — carga de dados
- validar tabelas;
- normalizar tipos;
- checar consistência mínima.

## Etapa 1 — geração de topologias candidatas
Fontes:
- famílias conhecidas;
- mutações de grafos;
- recombinação/crossover;
- templates mínimos de construção.

## Etapa 2 — reparo / normalização
- remover desconexões óbvias;
- respeitar regras de nó;
- ajustar sentidos;
- garantir payload válido.

## Etapa 3 — avaliação hidráulica/operacional
Executada em Julia + WaterModels.jl:
- construir a rede;
- verificar viabilidade;
- calcular métricas de fluxo;
- avaliar caminhos ativos por rota;
- calcular medição e limpeza por rota.

## Etapa 4 — extração de métricas
Cada candidato precisa sair com:
- `feasible`
- `install_cost`
- `fallback_cost`
- `quality_score_raw`
- `flow_out_score`
- `resilience_score`
- `cleaning_score`
- `operability_score`
- `bom_summary`
- `route_metrics`

## Etapa 5 — catálogo de soluções
Persistir:
- topologia;
- métricas;
- layout;
- BOM;
- relatório por rota.

## Etapa 6 — ranking dinâmico
A UI recalcula score final por pesos.

## Etapa 7 — visualização/exportação
- render 2D;
- tabela comparativa;
- export BOM;
- export relatório da solução final.

## Observação importante
O processamento deve suportar:
- topologias fixas manuais;
- topologias geradas automaticamente;
- comparação entre famílias;
- comparação entre soluções do mesmo cenário.
