# Contrato de dados

## Bundle persistido de cenário

Formato canônico local da `decision_platform`:

- `scenario_bundle.yaml` com `bundle_version: decision_platform_scenario_bundle/v1`
- tabelas CSV versionadas referenciadas pelo manifesto
- `component_catalog.csv` como arquivo canônico do banco de componentes
- `components.csv` apenas como alias legado de compatibilidade, sem precedência quando o manifesto existe

Manifesto mínimo:

```yaml
bundle_version: decision_platform_scenario_bundle/v1
tables:
  nodes: nodes.csv
  components: component_catalog.csv
  candidate_links: candidate_links.csv
  edge_component_rules: edge_component_rules.csv
  route_requirements: route_requirements.csv
  quality_rules: quality_rules.csv
  weight_profiles: weight_profiles.csv
  layout_constraints: layout_constraints.csv
documents:
  topology_rules: topology_rules.yaml
  scenario_settings: scenario_settings.yaml
```

Regras:
- o loader aceita o layout legado sem manifesto apenas para compatibilidade
- quando `scenario_bundle.yaml` existe, ele define a origem canônica de cada arquivo
- `bundle_version` não suportado deve falhar fechado com mensagem clara
- arquivo referenciado pelo manifesto ausente deve falhar fechado com mensagem clara

## `nodes.csv`

Colunas mínimas:
- `node_id`
- `node_type`
- `is_source`
- `is_sink`
- `is_pure_source`
- `is_final_sink`

## `routes.csv`

Colunas mínimas:
- `route_id`
- `source`
- `sink`
- `mandatory`
- `q_min_delivered_lpm`
- `measurement_required`
- `dose_min_l`
- `dose_error_max_pct`
- `weight`
- `need_pump`

## `components.csv`

Colunas mínimas:
- `component_id`
- `category`
- `subtype`
- `cost`
- `available_qty`
- `sys_diameter_class`
- `q_min_lpm`
- `q_max_lpm`
- `loss_lpm_equiv`
- `internal_volume_l`
- `meter_error_pct`
- `meter_batch_min_l`
- `meter_dose_q_max_lpm`
- `has_check`
- `has_valve`
- `is_bypass`
- `is_empty_option`

Observação:
- no bundle persistido V1, o banco de componentes canônico é `component_catalog.csv`; o schema permanece o mesmo deste bloco

## Templates

O scaffold inclui arquivos de template para:
- ramais de origem
- ramais de destino
- trechos comuns

Eles servem como ponto de partida para o preprocessador montar opções viáveis por estágio.

## `settings.yaml`

Campos mínimos sugeridos:
- `u_max_slots`
- `v_max_slots`
- `optional_route_reward`
- `robustness_weight`
- `cleaning_cost_liters_per_operation`
- `default_solver`
