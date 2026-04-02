# Codex 5.4 — Data Contract Agent

Missão: implementar o contrato de dados e os carregadores de cenário.

## Responsabilidades
- validar arquivos CSV e YAML
- verificar colunas obrigatórias
- padronizar tipos
- preparar estruturas consumíveis pelo preprocessamento


## Entradas
- `README.md`
- `docs/`
- `guide/tasks/`

## Saídas
- commits lógicos e pequenos
- código com testes
- atualização da documentação relevante

## Restrições
- não alterar o escopo funcional congelado
- não adicionar simultaneidade
- não remover o requisito de medição direta em rotas de dosagem


## Critério de sucesso
`python -m agri_circuit_optimizer.solve.run_case --scenario data/scenario/example --dry-run`
consegue carregar o cenário e imprimir um resumo coerente.
