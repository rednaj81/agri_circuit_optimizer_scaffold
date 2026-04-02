# Decisões de implementação da extensão da maquete

## Contexto

Esta rodada adiciona o cenário `maquete_core`, geometria simplificada, mangueira modular de `1 m`, conectores T como BOM real e o modo hidráulico `bottleneck_plus_length`, preservando a arquitetura em camadas já existente.

## Decisões

1. O contrato de dados foi estendido de forma retrocompatível.
   - `nodes.csv` aceita coordenadas e footprint opcionais.
   - `components.csv` aceita atributos opcionais de mangueira modular e marcação de item extra.
   - `settings.yaml` aceita parâmetros geométricos e do modo hidráulico da maquete.
2. O cálculo geométrico foi mantido no preprocessamento.
   - ramos recebem `hose_length_m` derivado da distância até o manifold correspondente
   - troncos usam `trunk_length_*_m`
   - o consumo de mangueira é discretizado em módulos de `1 m`
3. O modo `bottleneck_plus_length` não abriu um segundo pipeline de modelagem.
   - o mesmo builder de opções passa a calcular `q_max_lpm` efetivo
   - Pyomo e fallback continuam consumindo as mesmas opções já preprocessadas
4. Os troncos da maquete não consomem T.
   - isso foi implementado por template/configuração, sem criar uma exceção estrutural fora do cenário
5. Extras de custo zero passaram a ter desempate mínimo no objetivo.
   - foi adicionado um epsilon de uso de extras para evitar que Pyomo selecione `overflow` arbitrariamente quando base e extra têm o mesmo custo
   - isso manteve consistência com o fallback e melhorou a legibilidade da BOM
6. O modelo Pyomo passou a exigir que uma opção de bomba/medidor selecionada seja efetivamente usada por pelo menos uma rota.
   - isso evita inventário fantasma quando componentes têm custo zero

## Trade-offs

- O modo hidráulico da maquete ainda é simplificado.
  - a perda por comprimento entra como fator multiplicativo de capacidade local
  - não há balanço contínuo de pressão
- `count_external_hose_inside_total` e `preferred_for_maquette` foram aceitos no contrato, mas ainda não dirigem regras adicionais de otimização.
- A regressão do cenário `example` foi mantida em uma fatia representativa nos testes automatizados para manter o tempo total da suíte viável neste ambiente.

## Impacto

- `maquete_core` resolve end-to-end com:
  - `hose_total_used_m`
  - `tee_total_used`
  - `base_vs_extra_usage`
  - gargalo e folga hidráulica por rota
- a suíte automatizada cobre loader, preprocessamento, Pyomo, fallback, relatórios e sensibilidade geométrica da maquete
