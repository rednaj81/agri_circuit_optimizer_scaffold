# 04. Extensões do contrato de dados

## 4.1 Objetivo

Adicionar um novo contrato de dados orientado a grafo/arestas, sem quebrar imediatamente o contrato baseado em templates da família estrela.

## 4.2 Novos arquivos recomendados

### edges.csv
Representa as ligações candidatas/instaladas do grafo.

Campos sugeridos:
- `edge_id`
- `from_node`
- `to_node`
- `topology_family`
- `edge_kind`
  - hose
  - valve_segment
  - pump_segment
  - meter_segment
  - tee_branch
  - bypass
  - fixed_link
- `length_m`
- `direction_mode`
  - forward_only
  - reverse_only
  - bidirectional
  - conditional
- `group_id`
- `can_be_active`
- `counts_towards_hose_total`
- `counts_towards_connector_total`
- `must_be_closed_if_unused`
- `default_installed`
- `notes`

### edge_component_options.csv
Opções de componente por aresta.

Campos sugeridos:
- `edge_id`
- `component_id`
- `component_role`
  - hose
  - valve
  - pump
  - meter
  - connector
- `is_required_if_edge_installed`
- `is_active_control_element`
- `topology_family`

### topology_rules.yaml
Regras por família topológica.

Campos sugeridos:
- `topology_family`
- `max_active_pumps_per_route`
- `max_reading_meters_per_route`
- `allow_idle_pumps_on_path`
- `allow_idle_meters_on_path`
- `allow_passive_bypass_on_path`
- `enforce_simple_path`
- `allow_cycle_if_inactive`
- `treat_extra_open_branch_as_invalid`
- `core_routes_group`
- `service_routes_group`

## 4.3 Reuso do contrato antigo

A família `star_manifolds` pode continuar usando os contratos existentes:
- `source_branch_templates.csv`
- `destination_branch_templates.csv`
- `trunk_templates.csv`

Mas o sistema deve ter um adaptador interno para converter isso em uma representação equivalente baseada em arestas.

## 4.4 Extensões em routes.csv

Adicionar campos opcionais:
- `route_group`
  - core
  - service
- `allow_multi_stage_path`
- `max_active_pumps`
- `max_reading_meters`
- `route_notes`

## 4.5 Extensões em nodes.csv

Adicionar campos opcionais:
- `node_role`
  - source_only
  - sink_only
  - bidirectional
  - service
- `preferred_topology_family`
- `allow_service_loop`

## 4.6 Importante

O Codex deve implementar isso de modo incremental:
- primeiro permitir os novos arquivos para a nova família
- depois criar adaptadores ou convertores para o contrato antigo