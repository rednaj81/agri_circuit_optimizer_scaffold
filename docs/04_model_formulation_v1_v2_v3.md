# Formulação do modelo por versões

## Visão geral

O problema será resolvido como MILP em Pyomo, usando uma superestrutura em camadas.

## V1 — Topologia, custo e vazão mínima

### Conjuntos básicos
- nós
- rotas
- slots de bomba
- slots de medição
- opções de ramal de origem
- opções de ramal de destino
- opções de trecho comum

### Variáveis
- seleção de opções por estágio
- atribuição de bomba por rota
- atribuição de medidor/bypass por rota
- vazão entregue por rota

### Restrições
- cobertura das rotas obrigatórias
- disponibilidade de materiais
- uma bomba por rota
- um medidor/bypass por rota
- vazão entregue maior ou igual à requerida
- W sem entradas
- S sem saídas

### Objetivo
Minimizar custo fixo da solução, com prêmio opcional por rotas extras.

## V2 — Medição e dosagem

### Novos parâmetros
- `dose_min_l`
- `dose_error_max_pct`
- `measurement_required`
- `meter_batch_min_l`
- `meter_error_pct`
- `meter_dose_q_max_lpm`

### Restrições novas
- rotas com dosagem devem usar medição direta
- fluxômetro escolhido precisa ser compatível com:
  - dose mínima
  - erro máximo
  - faixa de vazão da rota

## V3 — Bitolas, perdas e folga hidráulica

### Novos parâmetros
- `sys_diameter_class`
- `loss_lpm_equiv`
- `q_max_lpm`
- `q_min_lpm` por componente

### Restrições novas
- escolha de classe de bitola do sistema
- compatibilidade de componentes com a classe escolhida
- perdas acumuladas por rota
- `F_r + perdas_r <= capacidade_da_bomba`
- folga hidráulica não negativa

### Observação
O modelo permanece simplificado e linear. Não usar curvas completas de bomba nesta fase.
