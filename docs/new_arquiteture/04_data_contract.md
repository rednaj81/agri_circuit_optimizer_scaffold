# Contrato de dados

## Arquivos mínimos da nova arquitetura

### 1. `nodes.csv`
Define tanques, saídas, junções e pontos especiais.

Campos sugeridos:
- `node_id`
- `node_type`
- `label`
- `x_m`
- `y_m`
- `allow_inbound`
- `allow_outbound`
- `requires_mixing_service`
- `zone`
- `is_candidate_hub`
- `notes`

### 2. `components.csv`
Catálogo de componentes.

Campos sugeridos:
- `component_id`
- `category`
- `subtype`
- `nominal_diameter_mm`
- `cost`
- `available_qty`
- `is_fallback`
- `quality_base_score`
- `hard_min_lpm`
- `hard_max_lpm`
- `confidence_min_lpm`
- `confidence_max_lpm`
- `forward_loss_pct_when_on`
- `reverse_loss_pct_when_off`
- `cleaning_hold_up_l`
- `can_be_in_series`
- `active_for_reading`
- `notes`

### 3. `candidate_links.csv`
Arestas/caminhos possíveis do grafo.

Campos sugeridos:
- `link_id`
- `from_node`
- `to_node`
- `archetype`
- `length_m`
- `bidirectional`
- `family_hint`
- `install_cost_override`
- `group_id`
- `notes`

### 4. `edge_component_rules.csv`
Regras de quais categorias podem ser usadas em cada tipo de ligação.

Campos sugeridos:
- `rule_id`
- `archetype`
- `allowed_categories`
- `required_categories`
- `optional_categories`
- `max_series_pumps`
- `max_reading_meters`
- `notes`

### 5. `route_requirements.csv`
Requisitos funcionais por rota.

Campos sugeridos:
- `route_id`
- `source`
- `sink`
- `mandatory`
- `route_group`
- `q_min_delivered_lpm`
- `measurement_required`
- `dose_min_l`
- `dose_error_max_pct`
- `cleaning_required`
- `allow_series_pumps`
- `weight`
- `notes`

### 6. `quality_rules.csv`
Regras de pontuação pós-viabilidade.
Campos sugeridos:
- `rule_id`
- `metric_scope`
- `metric_name`
- `operator`
- `threshold`
- `score_delta_if_true`
- `score_delta_if_false`
- `hard_filter`
- `description`

### 7. `weight_profiles.csv`
Perfis prontos de pesos.

### 8. `layout_constraints.csv`
Restrições geométricas e de mangueira.

### 9. `topology_rules.yaml`
Regras por família topológica.

### 10. `scenario_settings.yaml`
Configurações de geração, avaliação, ranking e UI.

## Observação
Os arquivos são projetados para:
- edição manual;
- edição pela UI;
- importação/exportação fácil;
- versionamento em Git.
