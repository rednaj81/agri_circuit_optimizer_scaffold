# T05 — Modelo V3: bitolas e hidráulica simplificada

## Objetivo
Adicionar classe de bitola, adaptadores, perdas e folga hidráulica.

## Entradas
components.csv, docs/04_model_formulation_v1_v2_v3.md

## Entregáveis
restrições de compatibilidade e hidráulica simplificada

## Dependências
T04

## Definição de pronto
modelo calcula perdas, aplica classe de bitola e filtra rotas inviáveis

## Status
- [ ] não iniciado
- [ ] em andamento
- [x] concluído

## Implementado
- compatibilidade de classe na linha central do sistema
- preservação de ramais mistos quando a própria opção incorpora adaptadores
- perdas acumuladas por rota com `loss_lpm_equiv`
- capacidade efetiva da bomba após perdas
- `hydraulic_slack_lpm` por rota
- relatórios com `total_loss_lpm_equiv`, `hydraulic_slack_lpm` e `gargalo_principal`
- testes de incompatibilidade de classe, perda excessiva, escolha de bomba maior e regressão completa
