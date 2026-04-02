# Decisões de implementação do V1

## Contexto

Esta rodada conclui T01–T03 e entrega V1 end-to-end no cenário `example`, preservando o scaffold e sem reabrir o escopo conceitual.

## Decisões

1. O carregador passou a validar contrato, tipos, unicidade de IDs e regras congeladas (`W` sem entradas, `S` sem saídas, existência de `I -> IR`) antes de qualquer preprocessamento.
2. A geração de opções monta combinações de ramais a partir de templates + biblioteca e usa poda de dominância conservadora. A poda só compara opções com o mesmo papel estrutural e o mesmo perfil funcional para não quebrar a disponibilidade global de materiais.
3. O runner já aplica medição direta em rotas com `measurement_required`, mesmo no V1. Isso mantém aderência às decisões congeladas e não conflita com V2, que ainda ficará responsável por dose mínima, erro máximo e adequação fina de fluxômetro.
4. A execução end-to-end local usa um fallback enumerativo quando `pyomo`/solver não estão disponíveis no ambiente. O caminho Pyomo continua implementado nos módulos de modelo; o fallback existe apenas para manter validação executável do scaffold neste ambiente.
5. No fallback do V1, a seleção estrutural pode resultar em `system_class = "mixed"` no resumo. Isso ocorreu porque a disponibilidade de válvulas no cenário-exemplo não comporta todos os ramais mandatórios em uma única classe. A escolha explícita de classe do sistema permanece reservada para V3, como definido na documentação.
6. O termo de limpeza entra no objetivo como penalidade fixa por rota ativa usando `cleaning_cost_liters_per_operation`. Não houve conversão monetária adicional porque o contrato atual não define essa equivalência.

## Impacto para V2

- V2 pode reaproveitar o loader, o preprocessador e os relatórios atuais.
- As próximas mudanças devem concentrar-se em adequação de medidor por dose mínima, erro máximo e faixas operacionais, sem refazer T01–T03.
