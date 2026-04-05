# Phase 2 To Phase 3 Handoff

## Estado da transição

- `phase_2` está encerrada.
- o gate único de saída da fase é `tests/decision_platform/test_phase2_exit_acceptance.py`.
- o gate foi reproduzido no codebase local atual sem reabrir o caminho oficial Julia-only.
- a próxima fase deve tratar fila/background runs como novo tema explícito.

## Baseline obrigatória

Use como fonte única de verdade da `phase_2` congelada:

- `docs/2026-04-05_phase2_exit.md`
- `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml` em `phase_2`
- `tests/decision_platform/test_phase2_exit_acceptance.py`
- `tests/decision_platform/test_studio_structure.py`
- `data/decision_platform/maquete_v2/scenario_bundle.yaml`
- `data/decision_platform/maquete_v2/component_catalog.csv`

## O que não deve ser reaberto na phase 3

- autoria local de nós e arestas já entregue no `Studio`
- fluxo canônico de `save/reopen` do bundle
- contratos de referência entre `nodes.csv`, `candidate_links.csv` e `route_requirements.csv`
- rejeição de layout legado sem manifesto

Qualquer reabertura desses pontos exige justificativa objetiva e novo handoff explícito.

## Foco esperado da phase 3

A `phase_3` deve avançar em fila/background runs, isolamento por execução, status por run, logs e artefatos. Esse tema começa sobre a baseline do `Studio` já congelada, e não como continuação implícita do save/reopen local.

## Riscos operacionais remanescentes

- o workspace local continua com arquivos modificados ou não rastreados fora desta transição (`AGENTS.md`, `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`, `.codex/`, `docs/codex_dual_agent_hydraulic_autonomy_bundle/*`, `docs/codex_dual_agent_runtime/supervisor_guidance.json`)
- o ambiente local ainda emite warnings de `pytest` para `cache_dir` e avisos de permissão para alguns diretórios temporários fora do escopo funcional

## Regra prática para o próximo papel

Antes de iniciar qualquer mudança funcional da `phase_3`, tratar este handoff como congelamento do `Studio` já entregue e não como convite para continuar expandindo a UI local sem novo gate.
