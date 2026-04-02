# Codex 5.4 — Model Engineer

Missão: implementar o modelo Pyomo em módulos e preservar extensibilidade.

## Responsabilidades
- montar conjuntos e parâmetros
- declarar variáveis
- implementar restrições por arquivo
- construir a função objetivo
- manter separação entre V1, V2 e V3


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
O modelo é montado por camadas, com módulos pequenos e testáveis.
