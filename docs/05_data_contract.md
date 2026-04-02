# Contrato de dados

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
