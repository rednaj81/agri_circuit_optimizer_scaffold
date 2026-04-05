# Objetivo do programa

Queremos transformar a aplicação em uma plataforma profissional de engenharia hidráulica orientada a decisão, com liberdade topológica real e UX simples para modelar cenários.

## Resultado final desejado

A plataforma deve permitir:

- criar cenários visualmente por um studio de nós e arestas
- manter um banco de componentes
- definir rotas obrigatórias e restrições por cenário
- executar processamento apenas em Julia
- rodar cenários em fila de background, sem interferência entre execuções
- abrir cada cenário individualmente
- comparar soluções viáveis com:
  - custo
  - qualidade
  - vazão
  - resiliência
  - limpeza
  - uso de fallback de componentes
  - operabilidade
- visualizar circuitos em 2D
- selecionar uma solução final por decisão humana assistida ou por pesos computacionais congelados

## Princípio central

O sistema não deve ficar preso a uma topologia fixa.
Ele deve explorar arquiteturas viáveis, inclusive disruptivas, e retornar um catálogo de opções viáveis para análise.
