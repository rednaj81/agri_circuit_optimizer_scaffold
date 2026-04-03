# Integração com WaterModels.jl + Julia

## Decisão
Usar **Julia + WaterModels.jl + JuMP** como núcleo de avaliação hidráulica e otimização.

## Estratégia de integração
Não usar binding em memória na primeira fase.
Usar:

1. Python gera `candidate_network.json`
2. Python chama CLI Julia
3. Julia lê JSON, monta rede e resolve
4. Julia escreve `result_metrics.json`
5. Python importa resultado no catálogo

## Estrutura sugerida do lado Julia
- `julia/Project.toml`
- `julia/bin/run_scenario.jl`
- `julia/src/DecisionEngine.jl`
- `julia/src/ScenarioBuilder.jl`
- `julia/src/RouteMetrics.jl`
- `julia/src/ExportResults.jl`

## O que o engine Julia precisa entregar
- viabilidade global
- métricas por rota
- métricas por componente
- métricas de limpeza por rota
- métricas de vazão
- alerta de uso fora da faixa de confiabilidade
- resumo BOM/custo

## O que não precisa travar a primeira implementação
- física perfeita de todos os casos;
- otimização global livre final;
- UX refinada.

## Mas precisa existir agora
- ponte Python/Julia funcionando;
- cenário maquete_v2 rodando;
- métrica de custo, qualidade, vazão, limpeza e resiliência;
- catálogo viável/inviável.
