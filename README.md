# Agri Circuit Optimizer

Implementação incremental de um solucionador para síntese de circuito hidráulico agrícola com:
- topologia em camadas (superestrutura)
- seleção de componentes a partir de biblioteca de materiais
- medição com fluxômetros
- restrições de vazão mínima na saída
- restrições de dosagem mínima com margem de erro
- viabilidade hidráulica simplificada
- evolução por versões V1, V2 e V3

## Objetivo do sistema

Encontrar a menor rede hidráulica instrumentada que:
- conecta os nós necessários
- atende às rotas obrigatórias
- permite limpeza entre operações
- garante medição direta nas rotas de dosagem
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

## Execução validada nesta máquina

Os comandos abaixo foram executados com sucesso neste workspace:

```powershell
$env:PYTHONPATH = 'src'
pytest -q tests --basetemp tests/_tmp/pytest-basetemp
C:\Python312\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
C:\Python312\python.exe -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --output-dir data/output/example_v3
```

Observações:
- O ambiente atual não tem `pyomo` instalado, então o runner usa o fallback enumerativo.
- Quando `pyomo` e HiGHS estiverem disponíveis, `solve_case` tenta o caminho Pyomo primeiro.
- Os relatórios são gravados em `data/output/example_v3/`.

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

## Relatórios gerados

Em `data/output/example_v3/`:
- `summary.json`
- `bom.json`
- `routes.json`
- `hydraulics.json`

Os relatórios de rota incluem:
- `selected_meter_id`
- `meter_is_bypass`
- `meter_q_range_ok`
- `meter_dose_ok`
- `meter_error_ok`

Os relatórios hidráulicos incluem:
- `total_loss_lpm_equiv`
- `hydraulic_slack_lpm`
- `gargalo_principal`

## Testes

Cobertura mínima de aceite já incluída:
- validação do contrato e das regras congeladas
- geração de opções e poda
- regressão end-to-end do `example`
- medidor específico por dose/erro
- inviabilidade por medidor incompatível
- bypass permitido sem medição obrigatória
- incompatibilidade de classe
- inviabilidade por perdas excessivas
- escolha de bomba maior quando a menor não vence as perdas

## Roadmap

Concluído:
- T01 — contrato de dados e loaders
- T02 — geração de opções e poda
- T03 — modelo/runner V1
- T04 — medição e dosagem
- T05 — bitolas e hidráulica simplificada

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
