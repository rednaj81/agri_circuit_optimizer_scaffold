# Arquitetura final proposta

## Visão geral
A plataforma terá 4 camadas principais:

1. **Entrada de dados editável**
   - tabelas CSV/Parquet e YAML
   - edição posterior pela UI

2. **Geração de topologias**
   - famílias conhecidas (estrela, barramento, loop, híbrido)
   - mutações livres de grafo
   - criação de candidatos

3. **Avaliação hidráulica e operacional**
   - Julia + WaterModels.jl + JuMP
   - avaliação de viabilidade
   - cálculo de métricas técnicas

4. **Catálogo + UI de decisão**
   - Dash
   - tabela interativa
   - ranking por pesos
   - comparação lado a lado
   - renderização 2D do circuito

## Decisão importante
A integração Python <-> Julia deve ser feita por **arquivos JSON/Parquet + chamada CLI**,
não por acoplamento Python-Julia em memória na primeira versão.

## Componentes do sistema

### Camada Python
- `scenario_io/`
- `graph_generation/`
- `candidate_catalog/`
- `ranking/`
- `rendering/`
- `decision_api/`
- `ui_dash/`
- `julia_bridge/`

### Camada Julia
- `wm_bridge/`
- `NetworkBuilder.jl`
- `ScenarioSolver.jl`
- `RouteMetrics.jl`
- `ExportResults.jl`

## Fluxo
1. usuário edita tabelas;
2. Python gera candidatos;
3. Python exporta payloads de rede;
4. Julia avalia cada candidato;
5. Python monta catálogo de soluções;
6. UI aplica filtros/pesos e mostra ranking;
7. usuário compara e escolhe;
8. sistema exporta BOM + layout + justificativa.

## Princípio de liberdade topológica
- não forçar estrela;
- não forçar barramento;
- não forçar loop;
- permitir famílias e mutações livres;
- exigir apenas:
  - viabilidade;
  - custo;
  - operabilidade;
  - métricas de qualidade/limpeza.
