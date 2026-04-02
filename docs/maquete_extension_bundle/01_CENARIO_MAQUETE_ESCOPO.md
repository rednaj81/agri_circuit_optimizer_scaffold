# Escopo congelado — cenário da maquete

## Objetivo

Criar um cenário de validação do modelo que represente uma **maquete física real**, com estoque limitado, layout simplificado e capacidade de revelar se a arquitetura proposta é montável com os componentes disponíveis.

## Nós do cenário

- `W` — tanque de água
- `P1`, `P2`, `P3`, `P4` — tanques de produto / premix
- `M` — tanque misturador
- `I` — tanque incorporador
- `IR` — retorno do incorporador
- `S` — saída externa para abastecimento

## Estoque base

- 8 válvulas solenoide
- 10 válvulas antirretorno
- 3 fluxômetros
- 3 bombas de sucção
- 10 conectores T
- 20 m de mangueira total

Todos os itens do estoque base entram com **custo zero** no cenário da maquete.

## Estoque extra / fallback

- `pump_extra` — custo 50
- `valve_extra` — custo 50
- `connector_t_extra` — quantidade 5, custo zero
- `check_valve_extra` — quantidade 10, custo zero

### Assunções congeladas para esta rodada

- **não** haverá `meter_extra` no `maquete_core`;
- o total de 20 m **inclui** a mangueira de abastecimento / saída;
- a maquete inicial usará **somente classe de sistema `g1`**;
- conectores T extras e antirretornos extras existem para não inviabilizar a montagem física por um detalhe de estoque, mas sem desviar a solução por custo;
- a penalização estrutural relevante fica concentrada em **bombas extras** e **solenoides extras**.

## Geometria simplificada

- base da maquete: `1.00 m x 0.50 m`
- tanques com footprint aproximado `0.10 m x 0.10 m`
- tanques posicionados acima da base, mas a altura não entra na primeira modelagem geométrica
- mangueira modelada em módulos inteiros de `1 m`

## Estratégia de roteamento geométrico

Não será implementado um roteamento 2D completo. Em vez disso:

1. cada nó terá coordenadas `(x_m, y_m)`;
2. o cenário terá coordenadas dos manifolds de sucção e descarga;
3. o comprimento de cada ramal será derivado da distância reta até o manifold;
4. o comprimento derivado será ampliado por um **fator de curva** e uma **margem de conexão**;
5. o valor resultante será arredondado para cima em módulos inteiros de mangueira.

## Rotas obrigatórias do `maquete_core`

### Água
- `W -> M`
- `W -> I`
- `W -> S`

### Produtos para o misturador
- `P1 -> M`
- `P2 -> M`
- `P3 -> M`
- `P4 -> M`

### Incorporador
- `I -> M`
- `I -> P1`
- `I -> P2`
- `I -> P3`
- `I -> P4`
- `I -> IR`

### Misturador para saída
- `M -> S`

## Rotas opcionais recomendadas

- `W -> P1`, `W -> P2`, `W -> P3`, `W -> P4`
- `P1 -> S`, `P2 -> S`, `P3 -> S`, `P4 -> S`
- `I -> S`

## Leitura estratégica desse cenário

O `maquete_core` não tem o objetivo de provar flexibilidade máxima do sistema. Ele serve para verificar, primeiro, se:

- a estrutura cabe no estoque físico da maquete;
- a topologia principal é montável;
- a BOM resultante faz sentido;
- as vazões mínimas principais são atendidas;
- a medição/dosagem funciona nas rotas realmente críticas.
