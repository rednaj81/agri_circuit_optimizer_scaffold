# Rotas obrigatórias e obrigações de arestas

## Objetivo
Permitir definir o que o cenário precisa atender.

## Rotas obrigatórias
Cada rota deve ter:
- route_id
- source
- sink
- mandatory
- q_min_delivered_lpm
- measurement_required
- dose_min_l
- dose_error_max_pct
- criticality
- notes

## Obrigações de arestas
Além da rota em si, o studio deve permitir:
- marcar arestas obrigatórias
- marcar arestas proibidas
- marcar arestas opcionais
- marcar grupos de conflito
- marcar capacidade máxima de compartilhamento

## Uso
O solver/engine pode explorar topologias livres,
mas precisa respeitar:
- rotas obrigatórias
- edge obligations definidas pelo cenário
