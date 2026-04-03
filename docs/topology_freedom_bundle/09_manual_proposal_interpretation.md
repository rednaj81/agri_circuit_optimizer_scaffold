# 09. Interpretação técnica da proposta manual do usuário

## 9.1 Leitura do desenho

A proposta manual do usuário não é uma estrela endurecida.
Ela se parece com:
- barramento horizontal principal
- taps dos tanques ligados ao barramento
- loops superiores/laterais que criam caminhos alternativos
- 3 ilhas de bomba + fluxômetro ao longo do barramento
- possibilidade de usar apenas 1 bomba ativa e 1 ponto de leitura por rota
- demais bombas/fluxômetros ficam instalados, porém inativos na operação corrente

## 9.2 Consequência

Essa arquitetura pode ser mais econômica em válvulas do que a estrela endurecida, porque a seletividade pode ser obtida pelo caminho ativo, não necessariamente por duplicação sucção/descarga em todos os nós.

## 9.3 Limitações do modelo atual frente à proposta
- o modelo atual não busca essa família topológica
- o modelo atual assume superestrutura em camadas
- o modelo atual força a semântica da estrela na seletividade
- o modelo atual não representa bem caminhos alternativos laterais nem uso de bombas instaladas porém inativas

## 9.4 Como validar a proposta
O caminho correto não é "forçar" a estrela a imitar o barramento.
É:
1. representar a proposta manual como topologia fixa
2. rodar o validador de rotas
3. comparar BOM e operabilidade com a estrela
4. só depois ampliar para comparação mais livre