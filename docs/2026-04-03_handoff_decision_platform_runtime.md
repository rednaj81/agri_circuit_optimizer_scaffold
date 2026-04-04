## Handoff — Decision Platform Runtime Real

Data: 2026-04-04  
Branch: `codex/new-architecture-platform`

## Estado de referência

Esta branch deve ser lida como fonte de verdade para o runtime atual da `decision_platform`.

Estado consolidado:

- `src/decision_platform/` é o runtime principal de decisão humana assistida
- `src/agri_circuit_optimizer/` permanece como baseline legado/histórico
- o bridge Julia real está ativo com `engine_used=watermodels_jl`
- o pipeline exporta artefatos finais, auditoria Julia vs Python e explicação explícita do vencedor
- a UI Dash trabalha com `selected_candidate` explícito, filtros de decisão e comparação lado a lado

## O que está implementado de fato

### 1. Candidato oficial e explicação auditável

O pipeline formaliza:

- `default_profile_id`
- `selected_candidate_id`
- `selected_candidate`
- `selected_candidate_explanation.json`
- `selected_candidate_explanation.md`

O artefato de explicação responde diretamente por que o vencedor superou o runner-up no perfil ativo, incluindo:

- vencedor e runner-up
- família topológica de ambos
- custo e score de ambos
- diferenças por dimensão de decisão
- fatores principais da vitória
- penalidades relevantes
- regras de qualidade acionadas
- rotas críticas
- conclusão curta em linguagem de engenharia

### 2. Comparação Julia vs Python útil para decisão

Arquivos principais:

- `src/decision_platform/audit/engine_comparison.py`
- `data/output/decision_platform/maquete_v2/engine_comparison.json`
- `data/output/decision_platform/maquete_v2/engine_comparison_candidates.csv`

O runtime agora exporta, por cenário comparado:

- `candidate_count` por engine
- `feasible_count` por engine
- top candidato por perfil
- `same_winner`
- `ranking_difference_observed`
- `decision_difference_observed`
- `route_metric_difference_observed`
- explicação vencedor vs runner-up em cada engine
- resumo textual de decisão por engine
- diff de candidatos e métricas por rota

Estado validado nesta máquina:

- cenário base `maquete_v2`:
  - Julia escolheu `bus_with_pump_islands__g18m1_1`
  - Python escolheu `loop_ring__g18m1_1`
  - `same_winner = false`
  - `ranking_difference_observed = true`
- variante `hybrid_free_focus_variant`:
  - Julia escolheu `hybrid_free__g14m2_2`
  - Python escolheu `hybrid_free__g11m2_2`

### 3. Viabilidade explícita e separada de score

Arquivos principais:

- `src/decision_platform/catalog/viability.py`
- `src/decision_platform/catalog/pipeline.py`

O catálogo e os exports agora distinguem claramente:

- `feasible`
- `infeasibility_reason`
- `constraint_failures`
- `constraint_failure_categories`
- `constraint_failure_reasons`
- `mandatory_failed_route_ids`

Agregados exportados:

- `viability_rate_by_family`
- `infeasible_candidate_rate_by_reason`
- `feasible_cost_distribution`
- `family_summary.csv`
- `infeasibility_summary.json`

No cenário validado nesta máquina, o motivo primário observado de inviabilidade ficou concentrado em `connectivity`.

### 4. UI fechada para decisão humana

Arquivo principal:

- `src/decision_platform/ui_dash/app.py`

Capacidades atuais:

- painel de candidato oficial com runner-up, fatores de vitória e penalidades
- comparação lado a lado entre oficial, runner-up e candidato selecionado manualmente
- filtros por família, viabilidade, fallback, custo máximo, score mínimo por dimensão, top N por família e motivo de inviabilidade
- resumo agregado por família no catálogo
- persistência em sessão para perfil, pesos, filtros e candidato selecionado
- destaque de rota selecionada e de componente crítico no Cytoscape
- export da comparação atual em CSV e JSON

Regra preservada:

- a UI não usa implicitamente `catalog[0]`
- o candidato exibido sempre é resolvido explicitamente a partir do estado visível

## Estado real do engine Julia

Arquivo principal:

- `julia/src/DecisionEngine.jl`

O que já usa o runtime Julia real:

- processo Julia real com ambiente controlado por `julia/Project.toml`
- checagem de disponibilidade de `WaterModels`, `JuMP` e `HiGHS`
- avaliação hidráulica/decisória em Julia real com payload compartilhado pelo bridge

O que ainda é simplificação própria:

- não há solve completo de rede hidráulica via API do `WaterModels`
- a avaliação de rota continua baseada em enumeração de caminhos, perdas equivalentes, gargalo por capacidade e métricas derivadas
- resiliência segue heurística

Conclusão prática:

- o Julia real não é apenas runtime alternativo; ele já altera a decisão final em `maquete_v2` e na variante focada
- ainda assim, a formulação hidráulica completa de rede permanece uma limitação assumida

## Artefatos finais relevantes

Em `data/output/decision_platform/maquete_v2/`:

- `summary.json`
- `catalog.csv`
- `catalog.json`
- `catalog_detailed.json`
- `ranked_profiles.json`
- `ranking_profiles.json`
- `catalog_summary.json`
- `engine_comparison.json`
- `engine_comparison_candidates.csv`
- `family_summary.csv`
- `infeasibility_summary.json`
- `selected_candidate.json`
- `selected_candidate_explanation.json`
- `selected_candidate_explanation.md`
- `selected_candidate_routes.json`
- `selected_candidate_bom.csv`
- `selected_candidate_score_breakdown.json`
- `selected_candidate_render.json`
- `selected_candidate.svg`
- `selected_candidate.png`

## Validação executada nesta rodada

### Pipeline real

Executado com sucesso:

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2
```

Resumo observado:

- `scenario_id = maquete_v2`
- `candidate_count = 76`
- `feasible_count = 49`
- `selected_candidate_id = bus_with_pump_islands__g18m1_1`
- runner-up do perfil `balanced` = `bus_with_pump_islands__g8m2_2`
- `engine_used = watermodels_jl`
- `engine_mode = real_julia`

### Testes

Executado com sucesso:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/decision_platform -m fast -q
.\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q
.\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -m "not requires_julia" -q
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests/decision_platform -m requires_julia -q
```

Estado consolidado:

- `24 tests collected` em `tests/decision_platform`
- `9 passed` em `-m fast`
- `1 passed` no aceite de export do pipeline
- `8 passed` em `test_ui_smoke.py`
- `2 passed` em `-m requires_julia`

Observação honesta:

- a execução completa `-m "not requires_julia"` estourou o timeout da ferramenta de automação desta sessão antes do fim, então o handoff registra apenas os slices efetivamente concluídos e a contagem coletada total.

## Comandos recomendados para validação local

Smoke rápido:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/decision_platform -m fast -q
```

Integração sem Julia real:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests/decision_platform -m "not requires_julia" -q
```

Integração com Julia real:

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests/decision_platform -m requires_julia -q
```

Pipeline principal:

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2
```

UI local:

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m decision_platform.ui_dash.app
```

## Limitações remanescentes

- `DecisionEngine.jl` ainda não resolve a rede completa pela API do `WaterModels`
- a exploração topológica continua heurística
- a UI é adequada para decisão local, mas não tem workflow colaborativo ou trilha de aprovação
- a ferramenta desta sessão não conseguiu concluir a corrida integral `not requires_julia` antes do timeout, embora os slices principais tenham passado
