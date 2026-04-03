# Agri Circuit Optimizer

Implementação incremental de um solucionador para síntese de circuito hidráulico agrícola com:
- topologia em camadas (superestrutura)
- modo multitopologia com validação de topologia fixa
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
- `tests/` — testes automatizados

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

## Execução validada nesta máquina

Os comandos abaixo foram executados com sucesso neste workspace:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests --basetemp tests/_tmp/pytest-basetemp
.\.venv\Scripts\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
.\.venv\Scripts\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_core --dry-run
.\.venv\Scripts\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/maquete_core --output-dir data/output/maquete_core
```

Observações:
- A `.venv` deste workspace consegue importar `pyomo` e `highspy`.
- `solve_case` tenta Pyomo primeiro e cai para o fallback enumerativo quando necessário.
- Cenários com `edges.csv` + `topology_rules.yaml` entram no engine de topologia fixa.
- Os relatórios são gravados em `data/output/example_v3/`, `data/output/maquete_core/` e `data/output/maquete_bus_manual/`.

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

Próximos passos naturais:
- consolidar execução Pyomo real no ambiente com `pyomo` + HiGHS
- refinar a modelagem de compatibilidade geométrica se o projeto sair do escopo simplificado atual
- ampliar relatórios operacionais e comparação entre solução Pyomo e fallback

## Arquivos-chave para começar

- `prompts/PROMPT_FOR_CODEX_IMPLEMENTATION.md`
- `AGENTS.md`
- `docs/04_model_formulation_v1_v2_v3.md`
- `docs/05_data_contract.md`
- `guide/tasks/T01_data_contract_and_loaders.md`
- `guide/tasks/T05_model_v3_diameters_and_hydraulics.md`
