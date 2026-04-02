# Prompt completo — implementação da maquete

Use este projeto como fonte de verdade e implemente a próxima rodada sem redesenhar a arquitetura central.

## Leia nesta ordem
1. `README.md`
2. `AGENTS.md`
3. `docs/04_model_formulation_v1_v2_v3.md`
4. `docs/maquete_extension_bundle/01_CENARIO_MAQUETE_ESCOPO.md`
5. `docs/maquete_extension_bundle/02_SOLUCAO_TECNICA_NOVOS_ITENS.md`
6. `docs/maquete_extension_bundle/03_EVOLUCAO_DO_MODELO.md`
7. `docs/maquete_extension_bundle/04_DADOS_E_CONTRATO_MAQUETE.md`
8. `docs/maquete_extension_bundle/05_HIDRAULICA_SIMPLIFICADA_MAQUETE.md`
9. `docs/maquete_extension_bundle/06_CENARIO_TESTE_MAQUETE_CORE.md`
10. `docs/maquete_extension_bundle/07_TESTES_DE_ACEITE_MAQUETE.md`
11. `docs/maquete_extension_bundle/tasks/`
12. `docs/maquete_extension_bundle/examples/`

## Objetivo da rodada
Implementar o suporte ao cenário físico da maquete, preservando o que já existe e adicionando:
- `P4`
- cenário `maquete_core`
- estoque real da maquete
- mangueira modular de 1 m com total de 20 m
- cálculo geométrico simplificado de comprimento de ramos
- fator de curva e margem de conexão
- conectores T como BOM real
- novo modo hidráulico `bottleneck_plus_length`
- testes de aceite específicos da maquete

## Regras congeladas
- não permitir rotas entrando em `W`
- não permitir rotas saindo de `S`
- manter `I -> IR` obrigatório
- rotas obrigatórias devem ser atendidas
- rotas com `measurement_required = true` não podem usar bypass
- manter compatibilidade com o cenário example e com o modo antigo

## Estratégia de implementação

### Fase A — contrato e cenário
1. criar `data/scenario/maquete_core/`
2. adicionar `P4`
3. permitir colunas extras opcionais no loader sem quebrar cenários antigos
4. manter o contrato atual obrigatório intacto

### Fase B — geometria e mangueira modular
1. adicionar suporte a coordenadas `(x_m, y_m)` em `nodes.csv`
2. adicionar parâmetros geométricos em `settings.yaml`
3. gerar comprimento de ramal por distância ao manifold
4. converter o comprimento em módulos de `hose_g1_1m`
5. somar esse consumo na BOM e restringir o total a 20 m

### Fase C — conectores T e templates da maquete
1. usar conectores T como estoque real
2. garantir que, no modo da maquete, troncos **não** consumam T
3. configurar templates da maquete para:
   - origem ativa com válvula
   - `W` protegido com antirretorno
   - destinos internos passivos
   - saída `S` ativa com válvula
4. a intenção é caber em 8 solenoides base, evitando `valve_extra`

### Fase D — hidráulica `bottleneck_plus_length`
1. adicionar `hydraulic_loss_mode` nos settings
2. manter o modo antigo existente
3. no modo da maquete:
   - usar `q_max_lpm` como gargalo principal
   - reduzir a capacidade local de branch/trunk pelo comprimento da mangueira
   - calcular `hydraulic_slack_lpm`
   - identificar o gargalo principal nos relatórios
4. manter o MILP linear usando preprocessamento para gerar `q_max_lpm` efetivo por opção

### Fase E — testes e relatórios
1. criar testes específicos para o cenário `maquete_core`
2. validar que o cenário resolve end-to-end
3. validar que o uso de mangueira não passa de 20 m
4. validar que `pump_extra` e `valve_extra` não são usados no cenário principal
5. validar que `tee_extra` pode aparecer, pois a própria arquitetura exige 15 ramos
6. atualizar relatórios com:
   - `hose_total_used_m`
   - `tee_total_used`
   - `base_vs_extra_usage`
   - `route_effective_q_max_lpm`
   - `hydraulic_slack_lpm`
   - `bottleneck_component_id`

## Requisitos de qualidade
- preserve a modularidade atual
- mantenha tipagem e clareza de código
- documente decisões em `docs/decisions/`
- não faça refatorações cosméticas desnecessárias
- mantenha fallback e Pyomo coerentes

## Entregáveis esperados nesta rodada
- código funcional da extensão da maquete
- novo cenário `maquete_core`
- testes passando
- README/documentação atualizados
- resumo final com:
  - arquivos alterados
  - decisões tomadas
  - limitações
  - próximos passos
