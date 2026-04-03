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

### 5. UI mais fechada para decisão real

Arquivo principal:

- `src/decision_platform/ui_dash/app.py`

A UI agora suporta:

- filtros por família
- filtro de viabilidade
- custo máximo
- qualidade mínima
- resiliência mínima
- filtro por uso de fallback
- pesos editáveis
- reranking local
- seleção explícita do candidato
- export do catálogo filtrado
- export do candidato selecionado

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
- `candidate_count = 74`
- `feasible_count = 73`
- `engine_requested = watermodels_jl`
- `engine_used = watermodels_jl`
- `engine_mode = real_julia`
- `julia_available = true`
- `watermodels_available = true`

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

Resultado final:

- `16 passed in 1643.60s (0:27:23)`

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

### Subconjunto crítico

```powershell
$env:PYTHONPATH='src'
$env:JULIA_DEPOT_PATH=(Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_julia_bridge.py tests\decision_platform\test_maquete_v2_acceptance.py tests\decision_platform\test_ui_smoke.py -p no:tmpdir -vv -s
```

## Limitações remanescentes

- o runtime Julia real foi ativado no host atual, mas o setup depende do depot local `julia_depot_runtime`
- a instalação Julia no host ainda não está “limpa” o suficiente para dispensar esse depot local
- a engine Julia continua simplificada no conteúdo do `DecisionEngine.jl`; o runtime real está ativo, mas a lógica hidráulica ali ainda não é uma modelagem completa de WaterModels

## Estado objetivo no fim desta rodada

- Julia real ativado: sim
- WaterModels/JuMP/HiGHS ativos: sim
- Dash real ativo: sim
- `maquete_v2` rodou com `engine_used=watermodels_jl`: sim
- fail-closed preservado: sim
