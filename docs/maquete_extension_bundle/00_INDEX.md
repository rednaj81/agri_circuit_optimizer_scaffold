# Índice — extensão da maquete

## Leitura recomendada

1. `01_CENARIO_MAQUETE_ESCOPO.md`
2. `02_SOLUCAO_TECNICA_NOVOS_ITENS.md`
3. `03_EVOLUCAO_DO_MODELO.md`
4. `05_HIDRAULICA_SIMPLIFICADA_MAQUETE.md`
5. `06_CENARIO_TESTE_MAQUETE_CORE.md`
6. `07_TESTES_DE_ACEITE_MAQUETE.md`
7. `08_RESULTADO_ESPERADO_DA_MAQUETE.md`
8. `prompts/PROMPT_CODEX_MAQUETE_COMPLETO.md`

## Decisões congeladas neste pacote

- o cenário de validação inicial será `maquete_core`;
- o sistema ganha o nó `P4`;
- as regras congeladas anteriores continuam válidas:
  - nada entra em `W`;
  - nada sai de `S`;
  - `I -> IR` é obrigatório;
  - rotas obrigatórias devem ser atendidas;
  - rotas com `measurement_required = true` não podem usar bypass;
- a maquete usará **mangueira modular de 1 m**, com **20 m totais disponíveis**;
- o modo hidráulico recomendado para a maquete é **`bottleneck_plus_length`**;
- T, válvula e redução passam a atuar principalmente como **gargalo de capacidade**;
- o comprimento da mangueira passa a ser o principal fator degradante variável;
- somente `pump_extra` e `valve_extra` terão penalidade de custo explícita no cenário-base;
- `connector_t_extra` e `check_valve_extra` existirão como overflow de estoque, com custo zero neste primeiro ciclo;
- o cenário `maquete_core` começa com **uma única classe de diâmetro do sistema (`g1`)** para isolar a validação da geometria e da BOM.
