# Evolução recomendada do modelo para suportar a maquete

## Estratégia geral

A evolução deve ser **incremental e retrocompatível**. O objetivo não é refatorar tudo, mas adicionar um novo modo de cenário que preserve o comportamento dos cenários já existentes.

## Bloco A — contrato de dados e cenário

### Objetivo
Permitir que um cenário carregue geometria, estoque de mangueira modular e preferências da maquete.

### Mudanças recomendadas
- aceitar colunas extras em `nodes.csv` para coordenadas e footprint;
- aceitar colunas extras em `components.csv` para mangueira por módulo, penalidade por comprimento e marcação de item extra;
- aceitar novas chaves opcionais em `settings.yaml`;
- criar `data/scenario/maquete_core/`.

## Bloco B — preprocessamento geométrico

### Objetivo
Gerar opções de ramal e tronco com consumo realista de mangueira.

### Mudanças recomendadas
1. ler coordenadas dos nós;
2. ler coordenadas dos manifolds em `settings.yaml`;
3. calcular comprimento necessário por ramal;
4. converter em módulos de 1 m;
5. multiplicar `component_counts` de `hose_g1_1m`;
6. ajustar `internal_volume_l` e `q_max_lpm` da opção.

## Bloco C — troncos da maquete

### Objetivo
Ajustar a contagem de conectores para casar com a maquete real.

### Mudanças recomendadas
- permitir que o template de tronco declare se consome ou não conector;
- no cenário da maquete, troncos não devem consumir T;
- os T ficam associados aos ramos, não aos troncos.

## Bloco D — hidráulica simplificada específica da maquete

### Objetivo
Trocar o peso principal do cálculo hidráulico: sair da soma fixa de perdas e ir para **gargalo + comprimento**.

### Mudanças recomendadas
- manter `q_max_lpm` como sinal hidráulico principal;
- degradar `q_max_lpm` local de mangueira/ramal conforme o comprimento;
- usar `hydraulic_loss_mode` para decidir entre o modo antigo e o novo;
- calcular `hydraulic_slack_lpm = q_effective_lpm - q_required_lpm`.

## Bloco E — relatórios

### Relatórios novos / ampliados
- `summary.json`
  - `hose_total_used_m`
  - `hose_total_available_m`
  - `tee_total_used`
  - `base_vs_extra_usage`
  - `maquette_layout_mode`
- `routes.json`
  - `source_branch_hose_m`
  - `destination_branch_hose_m`
  - `route_effective_q_max_lpm`
  - `hydraulic_mode`
- `bom.json`
  - consumo separado de `base` e `extra`
- `hydraulics.json`
  - `bottleneck_component_id`
  - `route_hose_total_m`
  - `q_effective_lpm`
  - `hydraulic_slack_lpm`

## Bloco F — fallback enumerativo

### Regra importante
O fallback precisa continuar coerente com o Pyomo.

### Recomendação
- implementar as mesmas regras de viabilidade geométrica e hidráulica no payload/preprocessamento;
- deixar o fallback apenas enumerar estruturas já pré-filtradas;
- não criar uma lógica independente e divergente para o modo da maquete.
