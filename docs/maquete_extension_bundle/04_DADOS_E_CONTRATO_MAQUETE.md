# Extensões recomendadas do contrato de dados para a maquete

## Princípio

As colunas atuais obrigatórias devem continuar válidas. As extensões abaixo devem entrar como **colunas/chaves opcionais**, para preservar cenários existentes.

## `nodes.csv`

### Colunas existentes (mantidas)
- `node_id`
- `node_type`
- `is_source`
- `is_sink`
- `is_pure_source`
- `is_final_sink`

### Colunas novas sugeridas
- `x_m`
- `y_m`
- `footprint_w_m`
- `footprint_d_m`
- `mount_height_m` (opcional, reservado para futuro)

### Uso
- `x_m`, `y_m` alimentam o cálculo geométrico de ramais;
- `footprint_*` servem para documentação/layout, sem entrar na primeira otimização;
- `mount_height_m` pode ficar ignorado no primeiro ciclo.

## `components.csv`

### Colunas existentes (mantidas)
As colunas atuais continuam sendo necessárias.

### Colunas novas sugeridas
- `hose_length_m`
- `hose_loss_pct_per_m`
- `is_extra`
- `extra_penalty_group`
- `consume_connector_in_trunk`
- `preferred_for_maquette`

### Uso recomendado
- `hose_length_m`: define o tamanho unitário do SKU de mangueira;
- `hose_loss_pct_per_m`: taxa de degradação local do `q_max_lpm` por metro;
- `is_extra`: marca peças de overflow;
- `extra_penalty_group`: agrupa custos/regras em relatórios;
- `consume_connector_in_trunk`: ajuda a desligar T do tronco no modo da maquete;
- `preferred_for_maquette`: opcional, para filtros/relatórios.

## `settings.yaml`

### Chaves atuais (mantidas)
As chaves obrigatórias atuais permanecem.

### Chaves novas sugeridas
- `hydraulic_loss_mode`
- `hose_total_available_m`
- `hose_module_m`
- `bend_factor`
- `connection_margin_m`
- `minimum_branch_hose_m`
- `suction_manifold_x_m`
- `suction_manifold_y_m`
- `discharge_manifold_x_m`
- `discharge_manifold_y_m`
- `trunk_length_suction_m`
- `trunk_length_discharge_m`
- `prefer_shorter_hose_weight`
- `count_external_hose_inside_total`
- `allow_meter_extra`

### Valor padrão recomendado
Se a chave não existir:
- o cenário atual continua no modo antigo;
- o código usa defaults conservadores.

## `source_branch_templates.csv` e `destination_branch_templates.csv`

### Semântica sugerida
As colunas atuais já são suficientes para a primeira versão da maquete.

### Estratégia
Use **mais templates**, e não necessariamente mais colunas.

Exemplo:
- `SRC_W_PROTECTED`
- `SRC_STD_ACTIVE`
- `DST_PASSIVE_INTERNAL`
- `DST_ACTIVE_OUTLET`

## `trunk_templates.csv`

### Extensão sugerida
Adicionar coluna opcional:
- `consume_connector`

### Objetivo
Permitir que, no cenário da maquete, troncos não consumam T.

Se não quiser alterar o contrato de template agora, isso pode ser controlado por uma regra em `settings.yaml`, por exemplo:
- `maquette_trunks_consume_connectors: false`

## Derivados que o preprocessamento deve produzir

O preprocessamento deve enriquecer opções geradas com:
- `hose_length_m`
- `hose_modules_used`
- `is_extra_usage_possible`
- `q_max_lpm_effective`
- `local_hydraulic_mode`
- `base_component_counts`
- `extra_component_counts`
