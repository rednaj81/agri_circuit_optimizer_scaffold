# 2026-04-03 — Nova plataforma de decisão multitopologia

## Contexto

O repositório já continha o baseline legado em camadas para V1/V2/V3, a extensão da maquete e o engine multitopologia fixo. A nova documentação em `docs/new_arquiteture/` congela uma segunda plataforma, orientada a catálogo de soluções, com:

- geração de topologias candidatas por família
- avaliação hidráulica por bridge Python -> Julia/WaterModels.jl
- ranking multicritério por perfis e pesos dinâmicos
- UI Dash para inspeção e comparação
- renderização 2D por topologia

## Decisões

### 1. Preservar o baseline legado e isolar a nova plataforma

A implementação nova entrou em `src/decision_platform/`, sem substituir `src/agri_circuit_optimizer/`. Isso evita regressão destrutiva no baseline e mantém os dois modos convivendo no mesmo repositório.

### 2. Priorizar um bridge executável mesmo sem Julia local

O contrato pedia Julia/WaterModels.jl, mas a máquina atual não possui Julia instalada. Por isso o bridge foi implementado em duas camadas:

- caminho real via `julia/bin/run_scenario.jl` quando `julia` existe no ambiente
- fallback local em Python (`python_emulated_julia`) com as mesmas entradas e saídas estruturais

Assim, o pipeline completo consegue rodar e gerar catálogo nesta máquina, sem bloquear a integração futura com Julia real.

### 3. Tornar Dash opcional em runtime, não no contrato

Como `dash`, `dash-ag-grid` e `dash-cytoscape` não estavam instalados no ambiente atual, a UI foi montada com uma camada de compatibilidade:

- com Dash instalado, a aplicação roda normalmente
- sem Dash, o layout ainda é construído e testável por smoke test

Isso preserva o contrato arquitetural sem mentir sobre a limitação local.

### 4. Limitar explosão combinatória na avaliação de caminhos

A enumeração de caminhos simples explodia em alguns candidatos. Para manter robustez operacional, o engine Python limita:

- número máximo de caminhos por rota
- profundidade de busca
- expansão agressiva na normalização/reparo de grafo

O objetivo foi garantir previsibilidade e execução prática do catálogo, antes de qualquer otimização mais sofisticada.

### 5. Declarar dependências novas no projeto

`plotly` entrou como dependência padrão do pacote e o stack Dash entrou como dependência opcional `ui`. Também foi corrigida a descoberta de pacotes no layout `src/`, para que o novo pacote `decision_platform` seja instalável formalmente.

## Trade-offs

- O engine Python emula o contrato de avaliação, mas não substitui WaterModels.jl em fidelidade hidráulica.
- A UI pode ser validada por layout e callbacks mesmo sem os pacotes reais, mas o servidor interativo depende da instalação do stack Dash.
- O catálogo exporta `parquet` apenas quando o engine correspondente está disponível; o fallback principal continua sendo `csv` + `json`.

## Próximos passos

1. Instalar Julia e WaterModels.jl no ambiente alvo e validar o bridge real.
2. Instalar o stack Dash completo e rodar a UI localmente.
3. Refinar o engine de viabilidade para reduzir a dependência do fallback Python.
4. Adicionar comparação cruzada explícita entre bridge Python e bridge Julia nas suítes de aceite.
