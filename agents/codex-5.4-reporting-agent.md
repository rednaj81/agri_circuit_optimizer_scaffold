# Codex 5.4 — Reporting Agent

Missão: transformar a solução do solver em relatórios úteis para engenharia.

## Responsabilidades
- BOM da solução
- rotas atendidas
- atribuição de bomba e medidor por rota
- perdas e folgas por rota
- exportação de esquema lógico em texto/JSON


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
Usuário final consegue ler a solução sem inspecionar variáveis internas do Pyomo.
