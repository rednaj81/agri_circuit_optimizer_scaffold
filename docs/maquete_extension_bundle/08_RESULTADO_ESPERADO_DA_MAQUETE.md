# Resultado esperado da maquete

## Objetivo desta leitura

Este arquivo não define uma solução rígida, mas descreve o que seria uma **saída saudável** do modelo para o cenário `maquete_core`.

## Resultado qualitativo esperado

### Topologia
- arquitetura em camadas preservada;
- todos os nós relevantes da maquete conectados por ramos coerentes;
- `I -> IR` implementado como recirculação real via pseudo-destino.

### Componentes
- 3 bombas base suficientes;
- 3 medidores base suficientes;
- 8 solenoides base suficientes, graças aos templates de destino passivo;
- 15 conectores T usados ao todo (10 base + 5 extra);
- mangueira total usada abaixo de 20 m.

### Medição
- rotas de produto/premix/mistura usando medição direta;
- água e recirculação podendo usar bypass onde permitido.

### Hidráulica
- `hydraulic_slack_lpm` positivo em todas as rotas obrigatórias;
- gargalos identificáveis no relatório;
- comprimentos de mangueira influenciando a folga.

## Resultado ruim / alerta

A solução merece revisão se ocorrer qualquer um destes sintomas:

- uso de `pump_extra` no cenário principal sem razão clara;
- uso de `valve_extra` quando os templates deveriam caber em 8 válvulas base;
- consumo de mangueira acima de 20 m;
- todos os medidores sendo trocados por bypass em rotas que exigem medição;
- gargalos incoerentes, como mangueira muito curta gerando perda excessiva sem justificativa;
- resultados do fallback incompatíveis com os do Pyomo.

## O que fazer se o cenário não fechar

Se o `maquete_core` ficar inviável, revisar nesta ordem:
1. templates de válvula por ramo;
2. contagem de T por tronco vs. ramo;
3. cálculo de mangueira por ramo;
4. parâmetros de `bend_factor` e `connection_margin_m`;
5. ranges dos fluxômetros;
6. q_min exigido nas rotas principais.
