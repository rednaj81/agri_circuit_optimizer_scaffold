# Estado atual e baseline

## Base assumida

A evolução deve partir do **estado atual da `decision_platform`**.

Premissas operacionais assumidas:

- `decision_platform` é o runtime principal da nova abordagem
- o legado `agri_circuit_optimizer` deve ser tratado como baseline histórico
- a aplicação já possui:
  - pipeline de cenário
  - runtime Julia-only no caminho oficial
  - comparação Python vs Julia
  - `selected_candidate`
  - `selected_candidate_explanation`
  - `engine_comparison`
  - UI com studio, catálogo, decisão e fila/run model
  - conceito de `technical_tie`

## O que NÃO deve ser refeito

- Não reconstruir o pipeline central
- Não reabrir a discussão de stack
- Não criar nova aplicação paralela
- Não transformar a rodada em novo projeto de solver

## O que o estado atual já permite

- execução de cenários
- inspeção de candidatos
- comparação lado a lado
- escolha do candidato oficial
- leitura de viabilidade
- entendimento de divergência entre Python e Julia

## O que ainda prejudica a UX

- interface ainda muito "ferramenta técnica"
- excesso de superfícies e informações simultâneas
- muitos blocos textuais/preformatados
- ausência de fluxo guiado por tarefa
- sensação de baixa linearidade para usuários novos
- falta de hierarquia visual entre:
  - editar cenário
  - rodar cenário
  - analisar resultados
  - decidir opção final
