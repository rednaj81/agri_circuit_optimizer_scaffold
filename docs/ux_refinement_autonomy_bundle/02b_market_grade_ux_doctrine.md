# Doutrina de UX de mercado

Esta fase não busca apenas "organizar melhor" a UI atual.
Ela busca transformar a `decision_platform` em uma experiência com aparência, fluxo e legibilidade de software profissional de mercado.

## Princípios obrigatórios

1. **Studio mostra apenas o grafo de negócio**
   - o usuário deve editar apenas entidades de negócio
   - nós intermediários técnicos, hubs internos de sucção/descarga e estruturas derivadas do solver não pertencem ao Studio
   - qualquer grafo técnico interno deve ser derivado do modelo do usuário e permanecer oculto na experiência principal

2. **Interação direta vem antes de formulários crus**
   - o Studio deve priorizar manipulação no canvas
   - arrastar e soltar
   - seleção clara
   - menu contextual / ações locais
   - propriedades no painel lateral, não como fluxo primário fragmentado

3. **A cadeia de suprimento do negócio precisa ficar explícita**
   - o usuário deve conseguir entender quem supre e quem é suprido sem abrir auditoria
   - a primeira dobra do Studio precisa falar em relações operacionais de negócio, não em estrutura de solver
   - o foco do canvas deve explicar o trecho de suprimento visível associado ao nó ou à conexão selecionada

4. **JSON, `html.Pre` e logs brutos não são UI principal**
   - detalhes técnicos só entram como auditoria avançada
   - a superfície principal deve ser composta por cards, tabelas legíveis, status, resumos, painéis e ações guiadas

5. **A visualização final mostra apenas o que faz sentido para o negócio**
   - nós órfãos não devem aparecer sem contexto e sem intenção explícita
   - elementos técnicos internos não devem poluir circuito final, decisão final ou comparação principal

6. **A UI deve parecer produto, não console avançado**
   - hierarquia visual clara
   - ação primária evidente
   - poucos focos por tela
   - rótulos amigáveis
   - contraste entre editar, rodar, analisar e decidir
   - polimento visual consistente

## Reprovações automáticas

Uma onda deve ser reprovada se:

- mantiver o Studio expondo entidades técnicas internas
- tratar JSON cru como interface primária
- só rearranjar blocos sem melhorar a jornada
- melhorar estética local sem clarificar o fluxo
- manter a sensação de "software de engenharia bruto"
- continuar polindo shell/copy sem atacar interação direta e legibilidade do fluxo de suprimento

## Expectativa de resultado

Ao final, a experiência principal deve parecer:

- um editor de cenário de negócio
- uma área clara de acompanhamento de execução
- uma superfície de decisão profissional
- uma área de auditoria separada, não dominante

## Prioridade da próxima rodada

Antes de qualquer nova onda de polimento visual amplo:

1. o Studio precisa continuar reduzindo dependência do workbench avançado
2. a leitura "quem supre quem" deve aparecer de forma natural no canvas e no foco
3. as ações comuns do usuário devem acontecer por interação direta/local
