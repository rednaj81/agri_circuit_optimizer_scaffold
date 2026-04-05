# Especificação do studio de nós e arestas

## Objetivo
Fornecer um editor visual simples e amigável para modelar cenários hidráulicos.

## Capacidades mínimas

### Nós
- criar
- mover
- editar propriedades
- duplicar
- excluir
- classificar:
  - tanque
  - bomba local
  - medidor local
  - junção
  - manifold
  - saída
  - serviço/recirculação

### Arestas
- criar arestas dirigidas e/ou bidirecionais
- marcar tipo:
  - mangueira
  - tubo
  - ligação flexível
  - bypass
  - link de bomba
  - link de medidor
- editar comprimento
- editar grupo de conflito
- editar componente(s) permitidos
- editar sentido permitido

### Regras de UX
- undo/redo
- snap opcional
- grid opcional
- seleção múltipla
- painel lateral de propriedades
- salvar layout

## Corte mínimo de phase 2

- expor criar, duplicar e excluir nós no studio usando o bundle canônico já existente
- expor criar e excluir arestas sem introduzir novo formato de persistência
- persistir alterações estruturais via `save -> reopen` somente em `scenario_bundle.yaml`, `nodes.csv` e `candidate_links.csv` já canônicos
- falhar fechado quando a exclusão de nó deixar referências órfãs em `candidate_links.csv` ou `route_requirements.csv`
- validar round-trip local preservando itens criados e confirmando a remoção dos itens excluídos

## Dados mínimos por nó
- node_id
- label
- type
- x
- y
- metadata livre

## Dados mínimos por aresta
- edge_id
- source
- target
- edge_type
- length_m
- conflict_group
- allowed_component_classes
- direction_mode

## Artefato salvo
O studio deve persistir um cenário editável, não só uma imagem/render.
