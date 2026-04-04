# Cenário de exemplo: maquete_v2

Este cenário é uma base para a nova arquitetura.

## Objetivos do cenário
- servir como cenário oficial da maquete;
- exercitar topologias star, bus, loop e híbridas;
- incluir fallback de bomba e medidor;
- incluir métricas de limpeza por rota;
- incluir ranges hard e confidence de fluxômetros;
- permitir score dinâmico.

## Observações
- os dados são exemplo inicial e podem ser refinados;
- o objetivo aqui é dar ao Codex uma base concreta de implementação;
- o cenário já está alinhado ao bundle persistido e deve permanecer versionável por diff;
- `scenario_bundle.yaml` é o manifesto canônico do bundle persistido;
- `component_catalog.csv` é o catálogo de componentes canônico e `components.csv` fica como alias legado.
