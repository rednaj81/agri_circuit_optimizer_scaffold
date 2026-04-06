# UX Refinement Autonomy Bundle

Este pacote foi preparado para ser descompactado dentro de `docs/` do repositório, ficando como:

`docs/ux_refinement_autonomy_bundle/`

Objetivo: orientar agentes autônomos do Codex a evoluir a `decision_platform` com foco em:

- UX mais agradável e menos "engenharia-first"
- fluxo limpo para usuário
- studio visual melhor
- fila/runs mais claros
- decisão humana assistida mais confiável
- preservando a arquitetura atual e a `decision_platform` como runtime principal

## Princípios centrais

1. **Não reabrir arquitetura**
   - Não criar nova plataforma paralela
   - Não trocar stack
   - Não reescrever o motor sem necessidade
   - Refinar a aplicação atual

2. **Produto antes de mais features**
   - Menos superfícies confusas
   - Mais clareza de fluxo
   - Menos blocos JSON expostos como UI primária
   - Mais progressão guiada

3. **Manter o que já existe de valioso**
   - `selected_candidate_explanation`
   - `engine_comparison`
   - `selected_candidate`
   - comparação lado a lado
   - studio de nós/arestas
   - fila/run model
   - Julia-only como caminho oficial

## Conteúdo do pacote

- `01_current_state_and_baseline.md`
- `02_ux_findings_and_problem_statement.md`
- `03_frozen_decisions.md`
- `04_target_user_flows.md`
- `05_information_architecture.md`
- `06_ui_refinement_backlog.md`
- `07_autonomous_agent_roles.md`
- `08_acceptance_and_exit_criteria.md`
- `automation/phase_plan.yaml`
- `prompts/PROMPT_FULL_AUTONOMOUS_UI_REFINEMENT.md`
- `prompts/PROMPT_SHORT_BOOTSTRAP_UI_REFINEMENT.md`
- `templates/.codex/agents/`
- `templates/.codex/skills/`

## Forma recomendada de uso

1. Descompactar este pacote em `docs/`
2. Ler os documentos na ordem numérica
3. Copiar os agentes para `.codex/agents/` se desejar
4. Iniciar com o prompt curto
5. Em seguida, usar o prompt completo
6. Exigir commits por fase
7. Trazer o resultado para auditoria
