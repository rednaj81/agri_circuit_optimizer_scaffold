# Arquitetura de informação desejada

## Navegação principal recomendada

A aplicação deve convergir para poucas áreas principais:

1. **Projetos**
   - lista de projetos
   - cenários por projeto
   - runs recentes

2. **Studio**
   - canvas visual
   - editor de nós/arestas
   - rotas obrigatórias
   - validação de conectividade
   - painel de propriedades

3. **Runs**
   - fila
   - histórico
   - status
   - progresso
   - logs resumidos
   - abrir resultado

4. **Decisão**
   - candidato oficial
   - runner-up
   - technical tie
   - comparação
   - filtros
   - escolha final
   - export

5. **Auditoria**
   - engine_comparison
   - detalhes avançados
   - artefatos técnicos
   - só para uso avançado

## Layout sugerido

### Studio
- esquerda: árvore/lista de cenários e entidades
- centro: canvas do circuito
- direita: propriedades do item selecionado
- topo: barra de validação e ações principais
- o canvas mostra somente nós e relações de negócio
- elementos técnicos internos ficam fora da superfície principal
- criação/edição deve privilegiar gesto direto no canvas e menu contextual

### Runs
- esquerda: lista/queue
- centro: resumo do run
- direita: detalhes/logs

### Decisão
- topo: resumo do candidato oficial
- centro: comparação e catálogo
- lateral: filtros
- abaixo: visualização do circuito escolhido

## Princípio visual
- a ação primária da tela deve ser óbvia
- a leitura do estado deve ser rápida
- detalhes técnicos devem ficar recolhíveis
- a tela principal não pode parecer console, debug panel ou formulário bruto
