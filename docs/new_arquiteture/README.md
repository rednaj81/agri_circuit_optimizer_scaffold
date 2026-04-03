# Nova arquitetura: plataforma de geração, validação e decisão de circuitos

Este pacote deve ser descompactado em `docs/new_arquiteture/` de um **novo branch** do repositório atual.

## Decisão recomendada
**Novo branch, não novo repositório.**

Motivos:
- reaproveita cenários, testes, baseline e histórico;
- mantém comparabilidade com a arquitetura atual;
- reduz risco de perder conhecimento já consolidado;
- facilita auditoria futura da implementação.

### Nome sugerido do branch
`feature/new-architecture-watermodels-decision-platform`

## Objetivo
Substituir a lógica restrita a superestruturas fixas por uma plataforma que:
1. gera topologias candidatas livres;
2. valida hidráulica e operabilidade;
3. monta um catálogo de cenários viáveis;
4. aplica ranking multicritério dinâmico;
5. renderiza os circuitos em 2D;
6. apoia decisão humana por filtros, pesos e comparação;
7. só depois, se desejado, escolhe a melhor solução computacional.

## Núcleo técnico alvo
- **Python**: orquestração, geração de topologias, ranking, API, UI
- **Julia + WaterModels.jl + JuMP**: avaliação/otimização hidráulica
- **Dash + AG Grid + Cytoscape**: interface interativa

## Como usar este pacote
1. crie um novo branch no repositório atual;
2. descompacte este pacote em `docs/new_arquiteture/`;
3. peça ao Codex para ler os arquivos nesta ordem:
   - `README.md`
   - `02_final_architecture.md`
   - `03_frozen_definitions.md`
   - `04_data_contract.md`
   - `05_processing_pipeline.md`
   - `06_scoring_filters_weights.md`
   - `07_ui_and_rendering.md`
   - `08_watermodels_and_julia_bridge.md`
   - `09_complete_execution_plan.md`
   - `10_acceptance_criteria.md`
   - `11_repo_target_tree.md`
   - `12_manual_table_editing_guide.md`
   - `tasks/`
   - `data_samples/maquete/`
4. use o prompt completo em `prompts/` para a implementação.
