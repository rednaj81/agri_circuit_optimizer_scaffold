# 01. Contexto e objetivo

## Situação atual

O projeto atual está forte em uma família de superestrutura fixa:
- origem -> ramo -> coletor de sucção -> banco de bombas -> banco de medição -> coletor de descarga -> ramo -> destino

Ao longo das últimas rodadas, o projeto evoluiu corretamente para:
- medição e dosagem formais
- hidráulica simplificada
- seletividade real dentro da topologia estrela endurecida
- validação da maquete com estoque, geometria e mangueira modular

## Problema agora identificado

O usuário trouxe propostas manuais de arquitetura que parecem mais econômicas e hidraulicamente plausíveis, mas que não cabem no espaço de busca da superestrutura atual.

Em especial, surgiram arquiteturas do tipo:
- barramento linear com ilhas de bombeamento e medição
- loops superiores/laterais de bypass
- caminhos alternativos para água e mistura
- uso de várias bombas instaladas, mas somente uma bomba efetivamente ativa por rota
- uso de vários fluxômetros instalados, mas somente um ponto de leitura válido por rota

Nessas arquiteturas, a seletividade não é mais bem descrita por:
- "um ramo de sucção aberto e um de descarga aberto"

Ela passa a ser melhor descrita por:
- "existe um caminho hidráulico ativo e seletivo entre A e B, sem vazamentos operacionais relevantes"

## Objetivo desta rodada

Evoluir o motor para um modo **multitopologia**, em que a pergunta central deixe de ser:

> qual é a melhor estrela endurecida?

e passe a ser:

> qual é a melhor arquitetura viável dentre diferentes famílias topológicas candidatas, e existe ao menos um caminho hidráulico seletivo e mensurável para cada rota exigida?

## Resultado esperado

Ao fim desta rodada, o repositório deve ser capaz de:
1. manter a família existente (`star_manifolds`) funcionando
2. adicionar pelo menos uma nova família (`bus_with_pump_islands`)
3. validar uma topologia fixa desenhada manualmente pelo usuário
4. comparar famílias topológicas no mesmo cenário
5. separar claramente:
   - topologia instalada
   - operação por rota
6. provar operabilidade por caminho, em vez de forçar uma única estrutura em camadas