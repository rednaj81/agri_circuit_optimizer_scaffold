# T04 — Modelo V2: medição e dosagem

## Objetivo
Adicionar regras de fluxômetro, dose mínima e erro máximo.

## Entradas
routes.csv, components.csv, docs/04_model_formulation_v1_v2_v3.md

## Entregáveis
restrições de medição e dosagem, testes para casos inviáveis

## Dependências
T03

## Definição de pronto
modelo rejeita fluxômetros incompatíveis e atende rotas de dosagem com medição direta

## Status
- [ ] não iniciado
- [ ] em andamento
- [x] concluído

## Implementado
- compatibilidade explícita `route -> meter_option`
- restrição formal de medição direta para rotas com `measurement_required`
- adequação por vazão mínima, dose mínima, erro máximo e `meter_dose_q_max_lpm`
- mesmos critérios no fallback enumerativo
- relatórios com `selected_meter_id`, `meter_is_bypass`, `meter_q_range_ok`, `meter_dose_ok` e `meter_error_ok`
- testes de aceite para medidor específico, inviabilidade, bypass permitido e consistência de lógica
