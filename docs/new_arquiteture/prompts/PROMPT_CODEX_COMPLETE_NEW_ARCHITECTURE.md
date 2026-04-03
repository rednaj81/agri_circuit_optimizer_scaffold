Leia primeiro, nesta ordem:
1. docs/new_arquiteture/README.md
2. docs/new_arquiteture/00_branch_strategy.md
3. docs/new_arquiteture/01_product_goal.md
4. docs/new_arquiteture/02_final_architecture.md
5. docs/new_arquiteture/03_frozen_definitions.md
6. docs/new_arquiteture/04_data_contract.md
7. docs/new_arquiteture/05_processing_pipeline.md
8. docs/new_arquiteture/06_scoring_filters_weights.md
9. docs/new_arquiteture/07_ui_and_rendering.md
10. docs/new_arquiteture/08_watermodels_and_julia_bridge.md
11. docs/new_arquiteture/09_complete_execution_plan.md
12. docs/new_arquiteture/10_acceptance_criteria.md
13. docs/new_arquiteture/11_repo_target_tree.md
14. docs/new_arquiteture/12_manual_table_editing_guide.md
15. docs/new_arquiteture/tasks/
16. docs/new_arquiteture/data_samples/maquete/

Objetivo:
implementar COMPLETAMENTE a nova arquitetura da plataforma de geração, validação, ranking e visualização de circuitos hidráulicos, em novo branch, usando:
- Python para orquestração, geração de topologias, ranking e UI;
- Julia + WaterModels.jl + JuMP como engine hidráulico/otimizador;
- Dash + AG Grid + Cytoscape como interface.

Decisões congeladas:
- manter o projeto no mesmo repositório, em novo branch;
- não quebrar o baseline legado;
- a nova arquitetura é uma plataforma paralela e maior;
- o produto principal é um catálogo de soluções viáveis com ranking dinâmico;
- custo é métrica central, mas não única;
- score final deve combinar custo, qualidade, fluxo, resiliência, limpeza e operabilidade;
- fluxômetros devem ter hard range e confidence range;
- bombas e fluxômetros fallback devem existir no catálogo e no cenário da maquete;
- limpeza por rota deve existir como métrica;
- caminho hidráulico possível deve ser encontrado sem impor topologia fixa;
- a UI deve permitir filtros, pesos, comparação e renderização 2D.

Instruções de execução:
1. crie o novo branch sugerido, ou equivalente, e registre isso no resumo;
2. implemente TODAS as fases da nova arquitetura neste branch;
3. preserve o código antigo e deixe a nova arquitetura em módulos/pastas próprias;
4. use integração Python -> Julia por JSON/CLI, não por bindings frágeis;
5. implemente o cenário `maquete_v2` usando os dados em docs/new_arquiteture/data_samples/maquete/ como base;
6. implemente geração de topologias candidatas por:
   - famílias base (star, bus, loop, hybrid)
   - mutações/recombinação
7. implemente avaliação via WaterModels/JuMP;
8. gere catálogo de soluções viáveis e inviáveis;
9. implemente score multicritério com pesos dinâmicos;
10. implemente UI Dash completa:
   - edição/importação de tabelas
   - tela de execução
   - catálogo
   - filtros
   - comparação
   - renderização 2D
   - export BOM/relatório
11. crie testes completos:
   - unitários
   - integração Python/Julia
   - aceitação do cenário maquete_v2
   - smoke test de UI
12. atualize README e documentação principal;
13. no final, execute testes e deixe instruções reproduzíveis.

Regras de modelagem importantes:
- separar viabilidade de ranking;
- separar topologia instalada de operação por rota;
- permitir múltiplos componentes instalados, mas selecionar só os relevantes por rota;
- permitir fluxo reverso por bomba desligada como caso viável penalizado, se a regra da família permitir;
- dar bônus de qualidade quando a rota usa um fluxômetro dentro da faixa de confiabilidade;
- aplicar penalidade quando o fluxo fica só no hard range, fora da confidence range;
- série de bombas não precisa ser proibida por padrão, mas deve influenciar limpeza, qualidade e operabilidade;
- fallback mantém o espaço de soluções aberto, mas deve piorar custo/qualidade;
- o sistema deve permitir decisão humana assistida por filtros e pesos antes da escolha computacional final.

Entregáveis obrigatórios:
- código implementado;
- cenário maquete_v2 funcional;
- UI funcional;
- integração Julia funcional;
- testes passando;
- documentação atualizada;
- resumo final com:
  - branch criado
  - arquivos principais alterados
  - decisões tomadas
  - limitações remanescentes
  - próximos passos recomendados

Não pare em uma etapa intermediária.
Implemente o pacote completo.
Comece por um plano curto de implementação e depois execute.
