# T05 — separar rotas core e service

## Objetivo
Permitir que `I -> IR` seja tratado como serviço opcional ou subcircuito local, sem distorcer a topologia core quando apropriado.

## Entregas
- classificação `route_group`
- relatórios separados por grupo
- teste de não contaminação do core por serviço