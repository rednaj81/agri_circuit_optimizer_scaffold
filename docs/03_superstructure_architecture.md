# Arquitetura da superestrutura

## Estrutura escolhida

```text
origens -> ramais de origem -> coletor de sucção -> banco de bombas
        -> banco de fluxômetros/bypass -> coletor de descarga
        -> ramais de destino -> destinos
```

## Justificativa

Essa arquitetura:
- representa melhor uma montagem real com manifold
- reduz o espaço de busca em relação a um grafo all-to-all
- facilita bombas compartilhadas
- facilita medição compartilhada
- facilita bitolas e perdas
- facilita gerar BOM e esquema de montagem

## Rotas obrigatórias recomendadas no cenário-exemplo

- `W -> M`
- `W -> I`
- `W -> S`
- `W -> P1`, `W -> P2`, `W -> P3`
- `P1 -> M`, `P2 -> M`, `P3 -> M`
- `P1 -> S`, `P2 -> S`, `P3 -> S`
- `I -> M`
- `I -> P1`, `I -> P2`, `I -> P3`
- `I -> S`
- `I -> IR`
- `M -> S`

## Rotas opcionais sugeridas

- transferências entre tanques flexíveis
- `M -> P1`, `M -> P2`, `M -> P3`
- retornos adicionais ao incorporador, se no futuro fizer sentido
