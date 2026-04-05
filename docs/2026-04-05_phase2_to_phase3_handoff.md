# Phase 2 To Phase 3 Handoff

## Estado da transição

- `phase_2` está encerrada.
- o gate único de saída da fase é `tests/decision_platform/test_phase2_exit_acceptance.py`.
- o gate foi reproduzido no codebase local atual sem reabrir o caminho oficial Julia-only.
- a `phase_3` abriu sobre esta baseline com `tests/decision_platform/test_phase3_queue_acceptance.py` como aceite atual do corte mínimo de fila serial.
- o handoff operacional único da fase ativa agora é `docs/2026-04-05_phase3_wave1_queue_open_handoff.md`.

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

## Corte mínimo já aberto na phase 3

- `run_job` persistido localmente com estados `queued`, `preparing`, `running`, `exporting`, `completed`, `failed` e `canceled`
- worker serial explícito: um job por vez, sem simultaneidade no MVP
- diretório isolado por run com `job.json`, `events.jsonl`, `run.log`, `source_bundle_reference.json` e `artifacts/`
- cancelamento explícito de jobs ainda em `queued`, sem artefatos de execução
- re-run explícito de runs `completed` ou `failed`, sempre por criação de novo `run_id` com referência à run de origem
- inspeção individual de run na UI local com status, eventos, log e diretório de artefatos
- trilha diagnóstica continua opt-in explícito; modo oficial continua Julia-only quando solicitado

## Fonte única para a fase ativa

- `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml` em `phase_3`
- `docs/codex_dual_agent_runtime/supervisor_guidance.json`
- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json` no bloco `phase_3_current_validation`
- `docs/2026-04-05_phase3_wave1_queue_open_handoff.md`
- `tests/decision_platform/test_phase3_queue_acceptance.py`

## Riscos operacionais remanescentes

- o workspace local continua com arquivos modificados ou não rastreados fora desta transição (`AGENTS.md`, `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`, `.codex/`, `docs/codex_dual_agent_hydraulic_autonomy_bundle/*`, `docs/codex_dual_agent_runtime/supervisor_guidance.json`)
- o ambiente local ainda pode emitir avisos de permissão para alguns diretórios temporários fora do escopo funcional, sem impacto no gate funcional ativo

## Regra prática para o próximo papel

Antes de iniciar qualquer mudança funcional da `phase_3`, tratar este handoff como congelamento do `Studio` já entregue e não como convite para continuar expandindo a UI local sem novo gate.
