# Agri Circuit Optimizer

Implementação incremental de um solucionador para síntese de circuito hidráulico agrícola com:
- topologia em camadas (superestrutura)
- modo multitopologia com validação de topologia fixa
- plataforma paralela de catálogo multitopologia orientada a decisão
- seleção de componentes a partir de biblioteca de materiais
- medição com fluxômetros
- restrições de vazão mínima na saída
- restrições de dosagem mínima com margem de erro
- viabilidade hidráulica simplificada
- validação física simplificada da maquete
- evolução por versões V1, V2 e V3

## Objetivo do sistema

Encontrar a menor rede hidráulica instrumentada que:
- conecta os nós necessários
- atende às rotas obrigatórias
- permite limpeza entre operações
- garante medição direta nas rotas de dosagem
- garante seletividade operacional em arquitetura estrela com manifolds
- compara famílias topológicas quando o cenário fornece topologia fixa por arestas
- respeita compatibilidade física de bitolas
- é hidraulicamente viável no modelo simplificado
- atende vazões mínimas exigidas
- atende dosagens mínimas com erro máximo permitido
- minimiza custo e complexidade

## Hipóteses congeladas

1. `P1`, `P2`, `P3` são tanques flexíveis e podem armazenar premix.
2. `W` é fonte pura: nenhuma rota entra em `W`.
3. `S` é saída final: nenhuma rota sai de `S`.
4. Rotas de dosagem exigem medição direta.
5. Cada rota usa exatamente uma bomba e um medidor/bypass no modelo-base.
6. Limpeza entre operações existe, mas no MVP entra como custo operacional fixo.
7. Hidráulica é simplificada por capacidade em L/min e perdas lineares equivalentes.
8. Bitolas são tratadas por classe de sistema; adaptadores entram como itens de material.
9. Seletividade em estrela é tratada como realizabilidade operacional da rota, não como perda hidráulica.

## Superestrutura escolhida

```text
origens -> ramais de origem -> coletor de sucção -> banco de bombas
        -> banco de fluxômetros/bypass -> coletor de descarga
        -> ramais de destino -> destinos
```

Nós:
- `W` = tanque de água
- `P1`, `P2`, `P3` = tanques flexíveis de produto/premix
- `M` = misturador
- `I` = incorporador
- `IR` = pseudo-destino de recirculação do incorporador
- `S` = saída externa

## Estrutura do repositório

- `prompts/` — prompt principal para o agente Codex
- `agents/` — papéis sugeridos para agentes Codex 5.4
- `docs/` — documentação estruturada
- `guide/tasks/` — tarefas numeradas para execução incremental
- `data/scenario/example/` — cenário-exemplo e contrato de dados
- `src/agri_circuit_optimizer/` — pacote Python
- `src/decision_platform/` — plataforma multitopologia orientada a catálogo e decisão
- `tests/` — testes automatizados

Observações:
- `src/agri_circuit_optimizer/` continua mantido como baseline legado validado por testes e referência histórica do V1/V2/V3.
- `src/decision_platform/` é o runtime ativo do cenário `data/decision_platform/maquete_v2/`.

## Estado real do projeto

### Baseline legado

- `src/agri_circuit_optimizer/` continua sendo a referência histórica do fluxo V1/V2/V3.
- esse baseline não foi substituído e segue útil para comparação, regressão e leitura do contrato original.

### Runtime principal atual

- `src/decision_platform/` é a frente principal para decisão humana assistida no cenário `data/decision_platform/maquete_v2/`.
- o pipeline oficial exporta catálogo, ranking, candidato oficial, explicação do vencedor e agregados de viabilidade.
- a comparação Julia vs Python existe apenas como trilha diagnóstica explícita.
- a UI Dash já cobre catálogo, comparação, circuito, candidato oficial e filtros de decisão com persistência simples em sessão.

### O que já está validado

- bridge real Julia ativo com `engine_used=watermodels_jl`
- comparação Python vs Julia exportada quando a trilha diagnóstica é habilitada explicitamente
- candidato oficial coerente entre pipeline, UI e artefatos
- motivos de inviabilidade e falhas de restrição exportados no catálogo e no resumo
- explicação auditável do vencedor em `selected_candidate_explanation.json` e `.md`

### O que ainda é simplificação ou heurística

- `DecisionEngine.jl` roda em Julia real e importa `WaterModels`, `JuMP` e `HiGHS`, mas a avaliação hidráulica decisória ainda é lógica própria em Julia, não um solve completo de rede via API do `WaterModels`
- resiliência e parte da exploração topológica continuam heurísticas
- a UI ainda é orientada a análise local; não há persistência multiusuário nem workflow de aprovação

### Critério prático de aceite

- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q --basetemp tests/_tmp/pytest-basetemp-fast`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q --basetemp tests/_tmp/pytest-basetemp-accept`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_diagnostic_engine_comparison_remains_explicit_opt_in -q --basetemp tests/_tmp/pytest-basetemp-accept-diag`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m "not requires_julia" -q --basetemp tests/_tmp/pytest-basetemp-no-julia`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m requires_julia -q --basetemp tests/_tmp/pytest-basetemp-julia`
- `python -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2`
- `python -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2 --include-engine-comparison`
- `python -m decision_platform.ui_dash.app`

## Quick start

### Opção 1: sem instalação editável

```powershell
python -m venv .venv
.\.venv\Scripts\activate
$env:PYTHONPATH = 'src'
pip install -r requirements.txt
pytest -q tests --basetemp tests/_tmp/pytest-basetemp
C:\Python312\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
C:\Python312\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --output-dir data/output/example_v3
```

### Opção 2: com instalação editável

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pytest -q tests --basetemp tests/_tmp/pytest-basetemp
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --output-dir data/output/example_v3
```

### Cenário da maquete

```powershell
.\.venv\Scripts\activate
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_core --dry-run
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_core --output-dir data/output/maquete_core
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_bus_manual --dry-run
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_bus_manual --output-dir data/output/maquete_bus_manual
```

### Nova plataforma de decisão

Pipeline do cenário `maquete_v2`:

```powershell
.\.venv\Scripts\activate
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
python -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2
```

Comparação diagnóstica Julia vs Python, fora do caminho oficial:

```powershell
.\.venv\Scripts\activate
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
python -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2_diag --include-engine-comparison --allow-diagnostic-python-emulation
```

UI Dash:

```powershell
.\.venv\Scripts\activate
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
python -m decision_platform.ui_dash.app
```

Smoke rápido da `decision_platform`:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q --basetemp tests/_tmp/pytest-basetemp-fast
```

Aceite diagnóstico lean, sem Julia real:

```powershell
$env:PYTHONPATH = 'src'
$env:DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE = '1'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q --basetemp tests/_tmp/pytest-basetemp-accept
```

Suíte sem Julia real:

```powershell
$env:PYTHONPATH = 'src'
$env:DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE = '1'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m "not requires_julia" -q --basetemp tests/_tmp/pytest-basetemp-no-julia
```

Comparação diagnóstica Julia vs Python:

```powershell
$env:PYTHONPATH = 'src'
$env:DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE = '1'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_diagnostic_engine_comparison_remains_explicit_opt_in -q --basetemp tests/_tmp/pytest-basetemp-accept-diag
```

Suíte com Julia real:

```powershell
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m requires_julia -q --basetemp tests/_tmp/pytest-basetemp-julia
```

UI e view-state:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m ui -q
```

Dependências:
- base: `pip install -r requirements.txt`
- UI completa: `pip install -e .[ui]`
- bridge Julia real: instalar Julia no sistema e preparar o ambiente de `julia/Project.toml`
- se o alias da Store não funcionar no terminal/sandbox, defina `JULIA_EXE` apontando para o binário real do `juliaup`, por exemplo:
  `C:\Users\<usuario>\.julia\juliaup\julia-1.12.5+0.x64.w64.mingw32\bin\julia.exe`

## Execução validada nesta máquina

Os comandos abaixo foram executados com sucesso neste workspace:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests --basetemp tests/_tmp/pytest-basetemp
.\.venv\Scripts\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
.\.venv\Scripts\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_core --dry-run
.\.venv\Scripts\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_core --output-dir data/output/maquete_core
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -m "not requires_julia" -q
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m requires_julia -q
.\.venv\Scripts\python.exe -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2
```

Observações:
- A `.venv` deste workspace consegue importar `pyomo` e `highspy`.
- `solve_case` tenta Pyomo primeiro e cai para o fallback enumerativo quando necessário.
- Cenários com `edges.csv` + `topology_rules.yaml` entram no engine de topologia fixa.
- Os relatórios são gravados em `data/output/example_v3/`, `data/output/maquete_core/` e `data/output/maquete_bus_manual/`.
- Julia, `WaterModels`, `JuMP` e `HiGHS` estão ativos nesta máquina via `julia_depot_runtime/`.
- `data/decision_platform/maquete_v2/scenario_settings.yaml` é `fail closed`: se `WaterModels` não estiver disponível e `fallback: none`, o pipeline oficial falha com mensagem clara.
- o pipeline oficial não habilita `python_emulated_julia` nem exporta `engine_comparison.json` por padrão.
- a comparação Julia vs Python e qualquer uso de `python_emulated_julia` ficaram restritos a trilhas diagnósticas explícitas com `--include-engine-comparison` e/ou `--allow-diagnostic-python-emulation`.
- a suíte `decision_platform` usa `-p no:cacheprovider` por padrão para não poluir a saída com `PytestCacheWarning` neste workspace.
- o override `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1` existe para suites diagnósticas sem Julia real; no caminho oficial ele apenas força fail-closed.
- O stack real do Dash está ativo na `.venv` e a UI é testada com o runtime real.
- A suíte atual da `decision_platform` coleta `24` testes.
- Os slices validados nesta rodada foram:
  - `9 passed` em `-m fast`
  - `8 passed` em `tests/decision_platform/test_ui_smoke.py -m "not requires_julia"`
  - `1 passed` no aceite exportador de `maquete_v2`
  - `2 passed` em `-m requires_julia`
- O pipeline oficial exporta `selected_candidate_explanation.json`, `selected_candidate_explanation.md`, `family_summary.csv`, `infeasibility_summary.json`, motivos de inviabilidade por candidato e métricas agregadas de viabilidade/custo por família.
- `engine_comparison.json` e `engine_comparison_candidates.csv` só são exportados na trilha diagnóstica explícita.

## Candidato selecionado oficial

Na `decision_platform`, o candidato selecionado não é mais implícito nem derivado da ordem de um `dict`.

Regras:
- o cenário define `ranking.default_profile`
- o pipeline retorna explicitamente:
  - `default_profile_id`
  - `selected_candidate_id`
  - `selected_candidate`
- o candidato selecionado oficial é o primeiro do ranking do perfil padrão já ordenado pelo pipeline
- o CLI usa esse `selected_candidate_id`
- a UI abre usando esse `selected_candidate_id`
- os exports finais usam esse mesmo candidato
- os exports carregam também metadados de geração/origem do candidato quando disponíveis

Na UI:
- trocar o perfil recalcula o ranking visível
- filtros e pesos alteram o catálogo visível
- se o candidato selecionado sair do conjunto filtrado, a UI escolhe explicitamente outro candidato visível
- o painel `Circuito` e o painel `Escolha final` sempre refletem o mesmo candidato atual

## O que está implementado

### V1
- loaders e validação de cenário
- geração de opções por estágio
- poda conservadora de dominância
- modelo base com topologia, custo e vazão mínima
- runner de cenário e relatórios mínimos

### V2
- compatibilidade explícita `route -> meter_option`
- medição direta obrigatória em rotas com `measurement_required`
- adequação de medidor por vazão, dose mínima, erro máximo e faixa operacional de dosagem
- mesma lógica no fallback enumerativo
- relatórios com seleção e flags de medição

### V3
- compatibilidade de classe na linha central do sistema
- suporte a ramais mistos quando a opção já embute adaptadores
- perdas acumuladas por rota
- capacidade efetiva da bomba após perdas
- `hydraulic_slack_lpm` por rota
- relatórios de hidráulica com perda total, folga e gargalo principal

### Extensão da maquete
- cenário `data/scenario/maquete_core/`
- colunas opcionais de geometria e mangueira no loader
- mangueira modular de `1 m` com consumo físico na BOM
- conectores T como itens reais de material
- troncos sem consumo de T no modo da maquete
- modo hidráulico `bottleneck_plus_length`
- resumo de estoque com `hose_total_used_m`, `tee_total_used` e `base_vs_extra_usage`

### Seletividade operacional
- ramos de sucção e descarga têm papel funcional explícito
- uma rota `A -> B` só é válida se puder operar com exatamente:
  - `1` ramo aberto na sucção: o da origem `A`
  - `1` ramo aberto na descarga: o do destino `B`
- ramo extra aberto invalida a rota como operação seletiva
- nós bidirecionais exigem isolamento independente nos dois lados usando o mesmo SKU físico de solenoide

### Multitopologia
- `settings.yaml` aceita `topology_family`
- `star_manifolds` continua usando o pipeline V1/V2/V3 já existente
- `bus_with_pump_islands` usa `edges.csv` + `topology_rules.yaml`
- a topologia instalada é separada da operação por rota
- cada rota passa a ser validada por caminho ativo dirigido
- bombas e medidores instalados podem permanecer no caminho como elementos ociosos quando a família permitir
- `route_group=service` permite separar rotas como `I -> IR` do atendimento core

### Plataforma de decisão `maquete_v2`
- dados em `data/decision_platform/maquete_v2/`
- geração de candidatos por família topológica
- normalização/reparo conservador de topologia
- instalação de componentes por link com fallback controlado
- bridge Python -> Julia com `fail closed` respeitando o contrato do cenário
- `python_emulated_julia` preservado apenas para auditoria, comparação e testes explicitamente opt-in
- catálogo com soluções viáveis e inviáveis
- auditoria explícita do engine Julia real versus `python_emulated_julia`
- `engine_comparison.json` com diff de decisão, ranking e métricas por rota quando a comparação diagnóstica é solicitada explicitamente
- `engine_comparison_candidates.csv` com ranking exportável por engine/perfil/cenário quando a comparação diagnóstica é solicitada explicitamente
- ranking multicritério por `weight_profiles.csv`
- renderização 2D e comparação por radar
- UI Dash com abas de dados, execução, catálogo, comparação, circuito e escolha final
- UI com persistência simples em sessão para perfil, filtros e pesos
- UI com resumo do candidato oficial, comparação lado a lado, export de comparação em CSV/JSON, filtro por motivo de inviabilidade, resumo agregado por família e destaque de rota/componente crítico no circuito
- `quality_rules.csv` aplicado de verdade no score com breakdown, flags e regras disparadas
- logs de seleção de componentes por candidato
- `selected_candidate_explanation.json` e `.md` para explicar por que o vencedor superou o runner-up
- métricas de geração por família, viabilidade por família, distribuição de custo viável e motivos de inviabilidade

## Relatórios gerados

Em `data/output/example_v3/`:
- `summary.json`
- `bom.json`
- `routes.json`
- `hydraulics.json`

Em `data/output/maquete_core/`:
- `summary.json`
- `bom.json`
- `routes.json`
- `hydraulics.json`

Em `data/output/maquete_bus_manual/`:
- `summary.json`
- `bom.json`
- `routes.json`
- `hydraulics.json`
- `topology.json`
- `comparison.json`

Em `data/output/decision_platform/maquete_v2/`:
- `summary.json`
- `catalog.csv`
- `catalog.json`
- `catalog_detailed.json`
- `ranked_profiles.json`
- `ranking_profiles.json`
- `catalog_summary.json`
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
- `ui_validation/README.md`
- `ui_validation/*.png`
- um diretório por candidato com `solution.json` e `bom.csv`

Somente na trilha diagnóstica explícita:
- `engine_comparison.json`
- `engine_comparison_candidates.csv`

Os relatórios de rota incluem:
- `selected_meter_id`
- `meter_is_bypass`
- `meter_q_range_ok`
- `meter_dose_ok`
- `meter_error_ok`
- `source_branch_selected`
- `discharge_branch_selected`
- `selective_route_realizable`
- `extra_open_branch_conflict`
- `open_suction_branch_count`
- `open_discharge_branch_count`
- `topology_family`
- `served`
- `failure_reason`
- `active_path_edge_ids`
- `active_path_arc_ids`
- `active_path_nodes`
- `total_loss_lpm_equiv`
- `route_effective_q_max_lpm`
- `hydraulic_slack_lpm`
- `bottleneck_component_id`
- `critical_consequence`
- `hydraulic_trace`

Os relatórios hidráulicos incluem:
- `total_loss_lpm_equiv`
- `hydraulic_slack_lpm`
- `gargalo_principal`
- `route_effective_q_max_lpm`
- `route_hose_total_m`
- `bottleneck_component_id`

O resumo da maquete também inclui:
- `hose_total_used_m`
- `tee_total_used`
- `base_vs_extra_usage`
- `solenoid_suction_total`
- `solenoid_discharge_total`
- `solenoid_total`

No modo multitopologia, o resumo também inclui:
- `topology_family`
- `core_routes_served`
- `service_routes_served`
- `core_mandatory_routes_served`
- `service_mandatory_routes_served`
- `mandatory_core_routes_unserved`

## Testes

Cobertura mínima de aceite já incluída:
- validação do contrato e das regras congeladas
- geração de opções e poda
- regressão end-to-end do `example` em fatia representativa
- medidor específico por dose/erro
- inviabilidade por medidor incompatível
- bypass permitido sem medição obrigatória
- incompatibilidade de classe
- inviabilidade por perdas excessivas
- escolha de bomba maior quando a menor não vence as perdas
- loader, preprocessamento, hidráulica e relatórios do `maquete_core`
- consistência Pyomo/fallback em slice reduzida da maquete
- gargalo por T e sensibilidade a comprimento na maquete
- inviabilidade por quebra de seletividade em estrela
- validacão de isolamento independente para nós bidirecionais
- loader completo do contrato da nova plataforma
- geração de famílias, mutações e crossovers para `maquete_v2`
- bridge Python/Julia com `fail closed` e metadados de engine
- catálogo, ranking e UI smoke test da nova arquitetura
- export completo do cenário `maquete_v2`
- quality rules dirigindo o score por tabela
- seleção de componentes com log explícito por candidato
- candidato selecionado oficial compartilhado entre pipeline, CLI, UI e exports
- separação entre suíte rápida, suíte com Julia real e suíte completa

## Roadmap

Concluído:
- T01 — contrato de dados e loaders
- T02 — geração de opções e poda
- T03 — modelo/runner V1
- T04 — medição e dosagem
- T05 — bitolas e hidráulica simplificada
- T09 — contrato e cenário da maquete
- T10 — geometria e mangueira modular
- T11 — modo `bottleneck_plus_length`
- T12 — testes e relatórios da maquete
- refinamento de seletividade operacional em arquitetura estrela
- engine de topologia fixa multitopologia
- suporte à família `bus_with_pump_islands`
- cenário `data/scenario/maquete_bus_manual/`
- comparação básica entre famílias por BOM e cobertura
- nova plataforma `src/decision_platform/`
- cenário `data/decision_platform/maquete_v2/`
- bridge Julia scaffold + fallback Python executável
- catálogo multitopologia com ranking e renderização 2D
- UI Dash para exploração do catálogo

## Testes da decision platform

Suíte rápida:

```powershell
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q --basetemp tests/_tmp/pytest-basetemp-fast
```

Aceite diagnóstico lean:

Janela operacional esperada nesta máquina: abaixo de `30 s`.

```powershell
$env:PYTHONPATH = 'src'
$env:DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE = '1'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q --basetemp tests/_tmp/pytest-basetemp-accept
```

Comparação diagnóstica explícita:

Janela operacional esperada nesta máquina: abaixo de `45 s`.

```powershell
$env:PYTHONPATH = 'src'
$env:DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE = '1'
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_diagnostic_engine_comparison_remains_explicit_opt_in -q --basetemp tests/_tmp/pytest-basetemp-accept-diag
```

Suíte com Julia real:

Gate oficial Julia-only. Não use `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE`.

```powershell
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m "requires_julia" -q --basetemp tests/_tmp/pytest-basetemp-julia
```

Suíte completa:

```powershell
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m pytest tests\decision_platform -q --basetemp tests/_tmp/pytest-basetemp-full
```

UI local:

```powershell
$env:PYTHONPATH = 'src'
$env:JULIA_DEPOT_PATH = (Resolve-Path 'julia_depot_runtime')
.\.venv\Scripts\python.exe -m decision_platform.ui_dash.app
```

Validação visual da UI:

```powershell
data/output/decision_platform/ui_validation/
```

Próximos passos naturais:
- consolidar execução Pyomo real no ambiente com `pyomo` + HiGHS
- refinar a modelagem de compatibilidade geométrica se o projeto sair do escopo simplificado atual
- ampliar relatórios operacionais e comparação entre solução Pyomo e fallback
- instalar Julia/WaterModels.jl no ambiente alvo e validar o bridge real
- instalar o stack Dash completo para uso interativo da UI

## Arquivos-chave para começar

- `prompts/PROMPT_FOR_CODEX_IMPLEMENTATION.md`
- `AGENTS.md`
- `docs/04_model_formulation_v1_v2_v3.md`
- `docs/05_data_contract.md`
- `guide/tasks/T01_data_contract_and_loaders.md`
- `guide/tasks/T05_model_v3_diameters_and_hydraulics.md`
