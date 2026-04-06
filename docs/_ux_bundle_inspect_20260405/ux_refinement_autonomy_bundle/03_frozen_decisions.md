# Decisões congeladas para a próxima evolução

Estas decisões não devem ser reabertas nesta fase.

## Arquitetura
- Manter `decision_platform`
- Manter Julia-only como caminho oficial de execução
- Manter comparação Python vs Julia apenas como apoio/auditoria
- Não criar novo frontend separado
- Manter Dash/Cytoscape/stack atual salvo necessidade pontual muito justificada

## Produto
- O sistema deve suportar:
  - criação/edição de cenários
  - runs independentes
  - fila de processamento
  - decisão humana assistida
- `technical_tie` é conceito de primeira classe
- `connectivity` deve ser visível como causa de inviabilidade e como validação preventiva no studio

## UX
- Priorizar progressão guiada
- Reduzir exposição de JSON/`html.Pre` como interface principal
- Aplicar progressive disclosure:
  - principal = resumo e ação
  - secundário = detalhes
  - terciário = auditoria avançada

## Operação
- Cenários independentes devem poder ser abertos sem interferência
- Runs em background devem ser observáveis
- O usuário deve conseguir voltar a um run e entender o estado sem ler logs brutos
