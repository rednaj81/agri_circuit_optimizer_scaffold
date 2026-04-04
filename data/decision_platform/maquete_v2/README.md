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
- o contrato de rotas é fail-closed: não entram rotas em nós com `allow_inbound=0`, não saem rotas de nós com `allow_outbound=0` e dosagem exige `measurement_required=1`.
- o contrato do catálogo/regras também é fail-closed: categorias do catálogo e de `edge_component_rules.csv` precisam permanecer canônicas, componentes de medição precisam ser legíveis e regras não podem declarar categorias fora do domínio ou fora de `allowed_categories`.
- settings, topologia e layout também são validados de forma fail-closed: `scenario_settings.yaml`, `topology_rules.yaml` e `layout_constraints.csv` precisam manter ids, famílias, perfis e limites estruturais explícitos e coerentes.
