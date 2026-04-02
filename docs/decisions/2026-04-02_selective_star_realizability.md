# Decisões de implementação da seletividade em estrela

## Contexto

Esta rodada refina o modelo para responder não apenas se existe conectividade, mas se uma transferência `A -> B` é seletivamente realizável em uma arquitetura estrela com manifold de sucção e manifold de descarga, sem introduzir novos tipos de válvula.

## Decisões

1. A semântica de ramo passou a ser explícita.
   - templates de origem recebem `branch_role = suction`
   - templates de destino recebem `branch_role = discharge`
   - o loader também anota `operational_role` dos nós como `source_only`, `sink_only` ou `bidirectional`
2. A seletividade foi tratada como viabilidade operacional, não como perda hidráulica.
   - se existir ramo extra inevitavelmente aberto em sucção ou descarga, a rota fica inviável
   - isso vale tanto no Pyomo quanto no fallback enumerativo
3. O mesmo SKU físico de solenoide continua sendo usado nos dois lados.
   - a distinção entre sucção e descarga é funcional e aparece em metadata, BOM e relatórios
4. O modelo Pyomo não ganhou simultaneidade.
   - a nova camada verifica se, para cada rota ativa, todos os outros ramos ativos no mesmo lado são fecháveis
   - isso preserva o escopo congelado do MVP
5. A maquete foi atualizada para refletir a seletividade real.
   - destinos internos deixaram de ser passivos
   - isso aumentou a BOM de solenoides e passou a consumir `valve_extra_g1`

## Trade-offs

- A seletividade continua sendo avaliada sobre estados operacionais por rota, não sobre uma sequência temporal completa de operações.
- Pyomo e fallback podem continuar encontrando soluções estruturalmente equivalentes com papéis invertidos entre alguns ramais de mesma métrica; os testes foram normalizados para comparar equivalência semântica quando o empate é real.
- O contrato de dados foi preservado de forma retrocompatível, com `branch_role` apenas como campo opcional.

## Impacto observável

- relatórios de rota agora incluem:
  - `source_branch_selected`
  - `discharge_branch_selected`
  - `selective_route_realizable`
  - `extra_open_branch_conflict`
  - contagens de ramos abertos por lado
- o resumo/BOM agora separa:
  - `solenoid_suction_total`
  - `solenoid_discharge_total`
  - `solenoid_total`
- no `maquete_core`, a solução passou a usar `15` solenoides ao todo:
  - `7` na sucção
  - `8` na descarga
  - com uso de `7` unidades de `valve_extra_g1`
