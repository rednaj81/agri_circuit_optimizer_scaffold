# Cenário de teste `maquete_core`

## Objetivo

Criar um cenário de validação física simplificada, usando:
- estoque real da maquete;
- um layout padrão sugerido;
- rotas obrigatórias centrais;
- nova lógica de mangueira modular + gargalo + comprimento.

## Layout sugerido

### Base
- largura: `1.00 m`
- profundidade: `0.50 m`

### Coordenadas sugeridas dos nós

| Nó | x_m | y_m |
|---|---:|---:|
| W  | 0.10 | 0.40 |
| P1 | 0.25 | 0.40 |
| P2 | 0.40 | 0.40 |
| P3 | 0.55 | 0.40 |
| P4 | 0.70 | 0.40 |
| M  | 0.85 | 0.40 |
| I  | 0.30 | 0.12 |
| IR | 0.32 | 0.12 |
| S  | 0.92 | 0.12 |

### Manifolds sugeridos
- sucção: `(0.35, 0.25)`
- descarga: `(0.65, 0.25)`

### Parâmetros geométricos sugeridos
- `hose_module_m = 1.0`
- `hose_total_available_m = 20.0`
- `bend_factor = 1.25`
- `connection_margin_m = 0.20`
- `minimum_branch_hose_m = 1.0`
- `trunk_length_suction_m = 1.0`
- `trunk_length_discharge_m = 1.0`

## Estratégia de diâmetro

O `maquete_core` deve começar com:
- `allowed_system_diameter_classes: [g1]`

Isso simplifica a validação inicial.

## Rotas obrigatórias recomendadas

| route_id | source | sink | q_min_delivered_lpm | measurement_required | dose_min_l | dose_error_max_pct |
|---|---|---|---:|---:|---:|---:|
| R001 | W  | M  | 30 | 0 | 0.0 | 100.0 |
| R002 | W  | I  | 20 | 0 | 0.0 | 100.0 |
| R003 | W  | S  | 40 | 0 | 0.0 | 100.0 |
| R004 | P1 | M  | 12 | 1 | 1.0 | 1.0 |
| R005 | P2 | M  | 12 | 1 | 1.0 | 1.0 |
| R006 | P3 | M  | 12 | 1 | 1.0 | 1.0 |
| R007 | P4 | M  | 12 | 1 | 1.0 | 1.0 |
| R008 | I  | M  | 10 | 1 | 1.0 | 1.0 |
| R009 | I  | P1 | 8  | 1 | 0.5 | 1.0 |
| R010 | I  | P2 | 8  | 1 | 0.5 | 1.0 |
| R011 | I  | P3 | 8  | 1 | 0.5 | 1.0 |
| R012 | I  | P4 | 8  | 1 | 0.5 | 1.0 |
| R013 | I  | IR | 15 | 0 | 0.0 | 100.0 |
| R014 | M  | S  | 50 | 1 | 5.0 | 2.0 |

## Rotas opcionais recomendadas

| route_id | source | sink | q_min_delivered_lpm | measurement_required | dose_min_l | dose_error_max_pct |
|---|---|---|---:|---:|---:|---:|
| R015 | W  | P1 | 15 | 0 | 0.0 | 100.0 |
| R016 | W  | P2 | 15 | 0 | 0.0 | 100.0 |
| R017 | W  | P3 | 15 | 0 | 0.0 | 100.0 |
| R018 | W  | P4 | 15 | 0 | 0.0 | 100.0 |
| R019 | P1 | S  | 10 | 1 | 1.0 | 1.5 |
| R020 | P2 | S  | 10 | 1 | 1.0 | 1.5 |
| R021 | P3 | S  | 10 | 1 | 1.0 | 1.5 |
| R022 | P4 | S  | 10 | 1 | 1.0 | 1.5 |
| R023 | I  | S  | 10 | 1 | 1.0 | 1.5 |

## Estrutura esperada de templates no `maquete_core`

### Source branch templates
- `SRC_W_PROTECTED`
  - nós: `W`
  - `require_valve = true`
  - `require_check = true`
- `SRC_STD_ACTIVE`
  - nós: `P1|P2|P3|P4|M|I`
  - `require_valve = true`
  - `require_check = false`

### Destination branch templates
- `DST_PASSIVE_INTERNAL`
  - nós: `P1|P2|P3|P4|M|I|IR`
  - `require_valve = false`
  - `require_check = false`
- `DST_ACTIVE_OUTLET`
  - nós: `S`
  - `require_valve = true`
  - `require_check = false`

## Estoque esperado da BOM

### Esperado / desejado
- usar **8 solenoides base**, sem `valve_extra`, se a arquitetura respeitar os templates;
- usar as **3 bombas base**, sem `pump_extra`, no cenário principal;
- usar **3 fluxômetros base**;
- usar **15 conectores T ao todo**:
  - 10 base
  - 5 extras
- usar **até 20 módulos de mangueira de 1 m**;
- manter alguma folga de mangueira, idealmente `>= 2 m`.

### Observação importante
O uso de `tee_extra` é aceitável e esperado neste cenário, porque a própria arquitetura em camadas exige 15 ramos e o estoque base tem 10 T.
