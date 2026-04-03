# Score, filtros e pesos

## Regra principal
Viabilidade vem antes de score.

## Fase A — filtros duros
Um cenário só entra no catálogo viável se:
- atende rotas obrigatórias;
- atende ranges hard de bomba/medidor;
- respeita catálogo e layout;
- produz caminho operacional admissível;
- não viola restrições geométricas duras.

## Fase B — métricas separadas
Cada cenário viável recebe métricas independentes:
- custo total
- qualidade
- vazão
- resiliência
- limpeza
- operabilidade
- manutenção

## Fase C — score ponderado dinâmico
A UI aplica pesos dinâmicos.

### Fórmula sugerida
`score_final = Σ (peso_normalizado_i * score_normalizado_i)`

## Exemplos de regras qualitativas

### Bônus
- bomba ativa única no sentido correto
- medidor dentro da faixa de confiabilidade
- caminho alternativo para rota crítica
- menor volume de limpeza

### Penalidades
- fluxo reverso por bomba desligada
- uso de fallback
- série de bombas
- medição só dentro do hard range e fora da confidence range
- muitas manobras/aberturas por rota

## Perfis de peso
- menor custo
- balanceado
- robustez
- operação simples
- limpeza prioritária

## UI
O usuário deve poder:
- travar um perfil pronto;
- ajustar sliders de peso;
- filtrar soluções;
- ver ranking instantâneo.
