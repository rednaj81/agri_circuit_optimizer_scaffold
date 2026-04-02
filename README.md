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

## Como usar com Codex

1. Extraia o `.zip`.
2. Crie o ambiente virtual.
3. Instale `requirements.txt`.
4. Entregue ao Codex o arquivo `prompts/PROMPT_FOR_CODEX_IMPLEMENTATION.md`.
5. Oriente o agente a seguir a ordem das tarefas em `guide/tasks/`.
6. Peça implementação incremental em V1, depois V2 e por fim V3.

## Quick start

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --output-dir data/output/example_v1
pytest -q
```

## Execução real do V1

O fluxo V1 já cobre:
- leitura e validação do cenário
- geração de opções por estágio
- poda conservadora de dominância
- resolução end-to-end do cenário `example`
- relatórios mínimos de BOM, rotas e hidráulica

Com o projeto instalado em modo editável:

```bash
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run
python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --output-dir data/output/example_v1
pytest -q tests --basetemp tests/_tmp/pytest-basetemp
```

Arquivos gerados em `data/output/example_v1/`:
- `summary.json`
- `bom.json`
- `routes.json`
- `hydraulics.json`

Observação:
- Quando `pyomo` e o solver HiGHS estiverem instalados no ambiente, o runner usa o caminho Pyomo.
- Se essas dependências não estiverem disponíveis, o runner cai para um fallback enumerativo para manter a validação executável do V1.

## Roadmap de implementação

- **V1:** topologia + custo + cobertura de rotas + vazão mínima
- **V2:** medição direta + dosagem mínima + erro máximo
- **V3:** classe de bitola + adaptadores + perdas hidráulicas + folga

## Arquivos-chave para começar

- `prompts/PROMPT_FOR_CODEX_IMPLEMENTATION.md`
- `AGENTS.md`
- `docs/04_model_formulation_v1_v2_v3.md`
- `docs/05_data_contract.md`
- `guide/tasks/T03_model_v1_topology_and_capacity.md`

## Status atual

Concluído nesta rodada:
- T01 — contrato de dados e loaders
- T02 — geração de opções e poda
- T03 — modelo/runner V1 com validação do cenário `example`

Ainda pendente:
- V2 — dose mínima, erro máximo e adequação fina de medição
- V3 — classe explícita de bitola, adaptadores, perdas e folga hidráulica
