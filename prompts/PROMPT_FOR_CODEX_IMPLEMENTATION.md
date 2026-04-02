# Prompt para o agente Codex — Implementação do projeto

Você está implementando um solucionador em Python/Pyomo para síntese de circuito hidráulico agrícola.
O escopo e a arquitetura já estão congelados. Não reabra o problema conceitual; implemente.

## Objetivo do sistema

Encontrar a menor rede hidráulica instrumentada que:
- conecta os nós necessários
- atende rotas obrigatórias
- permite limpeza entre operações
- garante medição direta nas rotas de dosagem
- respeita compatibilidade física de bitolas
- é hidraulicamente viável em modelo simplificado
- atende vazões mínimas exigidas
- atende dosagens mínimas com erro máximo
- minimiza custo e complexidade

## Superestrutura obrigatória

Use exatamente esta superestrutura como espaço de busca inicial:

`origens -> ramais de origem -> coletor de sucção -> banco de bombas -> banco de fluxômetros/bypass -> coletor de descarga -> ramais de destino -> destinos`

Nós:
- W, P1, P2, P3, M, I, IR, S

## Hipóteses congeladas

1. Operações sequenciais, sem simultaneidade.
2. P1, P2 e P3 são tanques flexíveis.
3. Nenhuma rota entra em W.
4. Nenhuma rota sai de S.
5. Cada rota usa exatamente uma bomba e um medidor/bypass no modelo-base.
6. Rotas com dosagem exigem medição direta.
7. Hidráulica simplificada por L/min e perdas lineares equivalentes.
8. Limpeza existe, mas no MVP é custo operacional fixo e não altera a topologia.

## Ordem mandatória de execução

### V1
Implementar:
- leitura do cenário
- geração de opções por estágio
- seleção estrutural
- cobertura de rotas obrigatórias
- vazão mínima entregue por rota
- custo fixo da solução
- disponibilidade de materiais

### V2
Adicionar:
- medição direta por fluxômetro
- dosagem mínima por rota
- erro máximo de dosagem por rota
- regras de adequação de fluxômetro

### V3
Adicionar:
- classe de bitola do sistema
- adaptadores
- perdas acumuladas por rota
- folga hidráulica
- restrições simplificadas de capacidade

## Fontes obrigatórias de verdade

- `README.md`
- `docs/04_model_formulation_v1_v2_v3.md`
- `docs/05_data_contract.md`
- `docs/08_decisions_frozen.md`
- `guide/tasks/`

## Requisitos de implementação

- Linguagem: Python 3.11+
- Modelagem: Pyomo
- Solver inicial: HiGHS (via `highspy`)
- Código modular
- Testes automatizados
- Relatórios legíveis para engenharia

## Estrutura de código esperada

- `src/agri_circuit_optimizer/io/`
- `src/agri_circuit_optimizer/preprocess/`
- `src/agri_circuit_optimizer/model/`
- `src/agri_circuit_optimizer/solve/`
- `src/agri_circuit_optimizer/postprocess/`

## Critérios de aceite

1. Caso mínimo viável resolve o cenário-exemplo em dry-run.
2. O carregador valida o contrato de dados.
3. O modelo V1 consegue montar a estrutura e verificar cobertura das rotas básicas.
4. O modelo V2 filtra fluxômetros incompatíveis com dose/erro.
5. O modelo V3 rejeita combinações inviáveis por bitola/perda.
6. Os relatórios mostram:
   - BOM
   - rotas atendidas
   - bomba por rota
   - fluxômetro por rota
   - vazão por rota
   - perdas por rota
   - folga por rota

## Estilo de trabalho

- Trabalhe por tarefa numerada em `guide/tasks/`.
- Ao concluir cada tarefa, atualize o status no próprio arquivo da tarefa.
- Não remova documentação congelada.
- Prefira pequenas iterações verificáveis a grandes saltos.

## Primeiro passo

Comece por:
- `guide/tasks/T01_data_contract_and_loaders.md`
- `guide/tasks/T02_option_generation_and_pruning.md`
- `guide/tasks/T03_model_v1_topology_and_capacity.md`
