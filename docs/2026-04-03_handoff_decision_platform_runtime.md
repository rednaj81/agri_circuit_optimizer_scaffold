# Handoff — Decision Platform Runtime Real

Data: 2026-04-03
Branch: `codex/new-architecture-platform`

## Objetivo desta rodada

Fechar o runtime real da `decision_platform` sem reabrir escopo:

- Julia real ativo
- WaterModels/JuMP/HiGHS ativos
- bridge fail-closed preservado
- stack real do Dash ativo na `.venv`
- `maquete_v2` executando com `engine_used=watermodels_jl`
- artefatos finais de decisão exportados em disco

## O que foi implementado de fato

### 0. Candidato selecionado oficial

O pipeline agora formaliza explicitamente:

- `default_profile_id`
- `selected_candidate_id`
- `selected_candidate`

Esse candidato oficial é compartilhado por:

- CLI
- UI
- `summary.json`
- `selected_candidate.json`
- `selected_candidate_routes.json`
- `selected_candidate_bom.csv`
- `selected_candidate_score_breakdown.json`
- `selected_candidate_render.json`

### 1. Bridge Julia real consolidado

Arquivos principais:

- `src/decision_platform/julia_bridge/bridge.py`
- `julia/bin/run_scenario.jl`
- `julia/src/DecisionEngine.jl`
- `julia/Project.toml`
- `julia/Manifest.toml`

Mudanças:

- o bridge agora usa ambiente Julia controlado por `julia_runtime_env()`
- usa `julia_depot_runtime` local quando disponível
- força `--compiled-modules=no` para reduzir problemas de precompile no host atual
- preserva fail-closed quando `fallback: none`
- suporta avaliação em lote (`evaluate_candidates_via_bridge`) para evitar custo de startup Julia por candidato
- grava metadados de engine:
  - `engine_requested`
  - `engine_used`
  - `engine_mode`
  - `julia_available`
  - `watermodels_available`

### 2. Runtime Julia real ativado

O runtime foi validado com:

```powershell
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
& 'C:\Users\jande\.julia\juliaup\julia-1.12.5+0.x64.w64.mingw32\bin\julia.exe' --project=julia --compiled-modules=no -e 'using JuMP, HiGHS, WaterModels, JSON3; println("watermodels-ok")'
```

Resultado validado:

- Julia detectado
- JuMP ativo
- HiGHS ativo
- WaterModels ativo

Observação importante:

- o host apresentou bloqueio de download de artefatos Julia via `schannel`
- a ativação local foi concluída com depot de runtime preparado no workspace

### 3. Stack real do Dash ativado na `.venv`

Arquivos principais:

- `src/decision_platform/ui_dash/_compat.py`
- `src/decision_platform/ui_dash/app.py`

Status:

- `dash` ativo
- `dash_ag_grid` ativo
- `dash_cytoscape` ativo
- `DASH_AVAILABLE = True`

### 4. Export final de artefatos

Arquivo principal:

- `src/decision_platform/catalog/pipeline.py`

A exportação agora gera:

- `summary.json`
- `catalog.csv`
- `catalog.json`
- `catalog_detailed.json`
- `ranked_profiles.json`
- `ranking_profiles.json`
- `selected_candidate.json`
- `selected_candidate_routes.json`
- `selected_candidate_bom.csv`
- `selected_candidate_score_breakdown.json`
- `selected_candidate_render.json`
- `selected_candidate.svg`
- `selected_candidate.png` quando o ambiente permite render com `matplotlib`

Os exports finais agora carregam coerência explícita com o candidato selecionado:

- `summary.json` contém `default_profile_id` e `selected_candidate_id`
- `selected_candidate_routes.json` contém `candidate_id`
- `selected_candidate_render.json` contém `candidate_id`
- `selected_candidate_bom.csv` contém coluna `candidate_id`

### 5. UI mais fechada para decisão real

Arquivo principal:

- `src/decision_platform/ui_dash/app.py`

A UI agora suporta:

- filtros por família
- filtro de viabilidade
- custo máximo
- qualidade mínima
- flow mínimo
- resiliência mínima
- cleaning mínimo
- operability mínimo
- top N por família
- filtro por uso de fallback
- pesos editáveis
- reranking local
- seleção explícita do candidato
- resumo do candidato oficial com flags e rotas críticas
- comparação lado a lado em grid
- export de comparação em CSV
- persistência simples em sessão para perfil/filtros/pesos
- destaque de rota no Cytoscape ao trocar a rota visível
- export do catálogo filtrado
- export do candidato selecionado
- seleção inicial alinhada ao `selected_candidate_id` oficial
- troca explícita do selecionado quando perfil/filtros/pesos mudam

### 6. Evidência objetiva do papel do engine Julia real

Arquivo principal:

- `data/output/decision_platform/maquete_v2/engine_comparison.json`

O runtime agora exporta:

- auditoria estática do `DecisionEngine.jl`
- diff `maquete_v2` Julia vs Python
- diff de uma variante focada `hybrid_free`
- `candidate_count`
- `feasible_count`
- top candidato por perfil
- `score_breakdown`
- diferenças de métricas por rota

Estado validado nesta máquina:

- `DecisionEngine.jl` importa `WaterModels`, `JuMP` e `HiGHS`
- o solve hidráulico ainda é lógica própria em Julia, não formulação explícita de rede via API do `WaterModels`
- mesmo assim o Julia real altera a decisão final no `maquete_v2`
- no cenário base:
  - Julia seleciona `bus_with_pump_islands__g18m1_1`
  - Python seleciona `loop_ring__g18m1_1`
- na variante `hybrid_free_focus_variant`:
  - Julia seleciona `hybrid_free__g14m2_2`
  - Python seleciona `hybrid_free__g11m2_2`

## Validação executada

### Pipeline real

Executado com sucesso:

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2_real
```

Resumo observado:

- `scenario_id = maquete_v2`
- `candidate_count = 76`
- `feasible_count = 49`
- `engine_requested = watermodels_jl`
- `engine_used = watermodels_jl`
- `engine_mode = real_julia`
- `julia_available = true`
- `watermodels_available = true`
- `engine_comparison.json` exportado
- `summary.json` com `viability_rate_by_family`, `infeasible_candidate_rate_by_reason` e `feasible_cost_distribution`

Artefatos gerados em:

- `data/output/decision_platform/maquete_v2_real/summary.json`
- `data/output/decision_platform/maquete_v2_real/catalog.csv`
- `data/output/decision_platform/maquete_v2_real/catalog.json`
- `data/output/decision_platform/maquete_v2_real/ranked_profiles.json`
- `data/output/decision_platform/maquete_v2_real/selected_candidate.json`
- `data/output/decision_platform/maquete_v2_real/selected_candidate_routes.json`
- `data/output/decision_platform/maquete_v2_real/selected_candidate_bom.csv`
- `data/output/decision_platform/maquete_v2_real/selected_candidate_score_breakdown.json`
- `data/output/decision_platform/maquete_v2_real/selected_candidate_render.json`
- `data/output/decision_platform/maquete_v2_real/selected_candidate.svg`

### Testes

Os testes da `decision_platform` foram atualizados para refletir o novo estado:

- fail-closed continua coberto por indisponibilidade simulada
- bridge real passa a ter teste de detecção positiva
- `maquete_v2` real passa a ter teste de integração marcado com `requires_julia`
- UI real passa a ter smoke test com stack Dash real

Observação:

- uma tentativa anterior ficou lenta por duas execuções concorrentes de `pytest`; isso foi encerrado
- a passada final correta foi rerodada em execução única, com saída visível e depot Julia explícito

Execução final validada:

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -p no:tmpdir --basetemp tests/_tmp/pytest-basetemp-real -vv -s
```

Resultado final mais recente:

- `21 passed, 2 deselected` em `16:46` para `-m "not requires_julia"`
- `2 passed, 21 deselected` em `04:41` para `-m requires_julia`
- contagem final consolidada válida: `23 passed`

## Comandos recomendados para validação local

### Smoke do bridge real

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -c "from decision_platform.julia_bridge.bridge import find_julia_executable,julia_available,watermodels_available; print(find_julia_executable()); print(julia_available()); print(watermodels_available())"
```

### Pipeline real

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2_real
```

### Testes da plataforma com saída visível

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -p no:tmpdir -vv -s
```

### Smoke rápido

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q
```

### UI

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m ui -q
```

### Subconjunto crítico

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_julia_bridge.py tests\decision_platform\test_maquete_v2_acceptance.py tests\decision_platform\test_ui_smoke.py -p no:tmpdir -vv -s
```

### Suíte rápida

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -p no:tmpdir --basetemp tests/_tmp/pytest-basetemp-fast -m "not slow and not requires_julia" -q
```

## Limitações remanescentes

- o runtime Julia real foi ativado no host atual, mas o setup depende do depot local `julia_depot_runtime`
- a instalação Julia no host ainda não está “limpa” o suficiente para dispensar esse depot local
- a engine Julia continua simplificada no conteúdo do `DecisionEngine.jl`; o runtime real está ativo, mas a lógica hidráulica ali ainda não é uma modelagem completa de WaterModels
- a evidência visual da UI foi automatizada por captura desktop; a navegação de abas ficou confiável, mas a aba final ainda depende de layout/viewport do host

## Estado objetivo no fim desta rodada

- Julia real ativado: sim
- WaterModels/JuMP/HiGHS ativos: sim
- Dash real ativo: sim
- `maquete_v2` rodou com `engine_used=watermodels_jl`: sim
- fail-closed preservado: sim
