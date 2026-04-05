# Especificação do banco de componentes

## Objetivo
Gerenciar o catálogo de componentes usados nas soluções.

## Categorias mínimas
- bomba
- fluxômetro
- válvula solenoide
- check valve
- tee
- conexão
- redutor/adaptador
- mangueira/tubo

## Campos mínimos
- component_id
- category
- subtype
- description
- cost
- available_qty
- is_fallback
- hard_min_lpm
- hard_max_lpm
- confidence_min_lpm
- confidence_max_lpm
- forward_loss_factor
- reverse_loss_factor
- cleaning_hold_up_l
- quality_tags
- compatible_edge_types
- compatible_diameter_classes
- notes

## Regras importantes
- fluxômetros têm faixa hard e faixa de confiança
- bombas e fluxômetros fallback existem para viabilidade, com custo alto
- componentes devem ser filtráveis por cenário
- seleção deve deixar rastro de decisão (`selection_log`)
