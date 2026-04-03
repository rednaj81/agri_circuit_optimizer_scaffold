# Plano completo de implementação

## Fase 1 — scaffold e branch
- abrir novo branch;
- criar nova árvore de módulos;
- não quebrar baseline legado;
- adicionar dados de exemplo da maquete.

## Fase 2 — contrato de dados
- loaders
- validação
- editores
- import/export

## Fase 3 — bridge Julia
- `Project.toml`
- CLI de execução
- payload JSON

## Fase 4 — gerador de topologias
- famílias conhecidas
- mutações de grafo
- geração livre controlada
- regras de reparo

## Fase 5 — avaliação
- WaterModels/JuMP
- relatório por rota
- limpeza por rota
- fallback

## Fase 6 — catálogo e ranking
- persistência
- filtros
- pesos
- score final

## Fase 7 — UI
- tabelas editáveis
- catálogo
- comparação
- renderização 2D
- export

## Fase 8 — testes
- unitários
- integração Python/Julia
- smoke test de UI
- regressões do cenário da maquete

## Fase 9 — documentação final
- README
- docs
- exemplos
- guia operacional

## Instrução para o Codex
Implementar o pacote completo.
Não parar na bridge, não parar no catálogo, não parar na UI.
Tudo precisa ficar conectado no branch novo.
