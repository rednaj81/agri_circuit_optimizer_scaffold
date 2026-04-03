# Bundle de direcionamento — topologias alternativas e validação por caminho hidráulico

Este pacote foi feito para ser descompactado dentro de `docs/` do repositório.

Objetivo: direcionar a próxima rodada do Codex para evoluir o modelo de uma superestrutura fixa em estrela para uma arquitetura mais geral, capaz de explorar e comparar diferentes famílias topológicas, em especial `bus_with_pump_islands`, sem perder as garantias já conquistadas em medição, seletividade, estoque e testes.

Conteúdo principal:
- `01_context_and_goal.md` — problema, motivação e objetivo técnico
- `02_key_definitions_frozen.md` — definições congeladas e decisões que o Codex não deve reinterpretar
- `03_target_architecture_multitopology.md` — arquitetura-alvo do motor de síntese/validação
- `04_data_contract_extensions.md` — proposta de extensão do contrato de dados
- `05_modeling_and_solver_changes.md` — mudanças no modelo matemático e no solver
- `06_execution_plan_codex.md` — plano técnico de execução
- `07_acceptance_tests.md` — critérios de aceite e testes obrigatórios
- `08_risks_and_non_goals.md` — riscos, limites e o que fica fora desta rodada
- `09_manual_proposal_interpretation.md` — leitura técnica da proposta manual do usuário
- `prompts/` — prompt completo e prompt curto para despacho ao Codex
- `tasks/` — tarefas organizadas por blocos de implementação

Leitura recomendada pelo Codex:
1. `README.md`
2. `01_context_and_goal.md`
3. `02_key_definitions_frozen.md`
4. `03_target_architecture_multitopology.md`
5. `04_data_contract_extensions.md`
6. `05_modeling_and_solver_changes.md`
7. `06_execution_plan_codex.md`
8. `07_acceptance_tests.md`
9. `prompts/PROMPT_CODEX_MULTITOPOLOGY_COMPLETO.md`