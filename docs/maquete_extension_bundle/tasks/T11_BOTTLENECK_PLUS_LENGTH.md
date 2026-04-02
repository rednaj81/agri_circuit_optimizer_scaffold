# T11 — modo hidráulico `bottleneck_plus_length`

## Objetivo
Implementar o modo hidráulico da maquete, mantendo compatibilidade com o modo antigo.

## Entregáveis
- `hydraulic_loss_mode` em `settings.yaml`
- preprocessamento com `q_max_lpm` efetivo por opção
- relatórios com gargalo e folga hidráulica

## Definição de pronto
- T, válvula e redução atuam como gargalo
- mangueira depende do comprimento
- o cenário `maquete_core` resolve com relatórios coerentes
