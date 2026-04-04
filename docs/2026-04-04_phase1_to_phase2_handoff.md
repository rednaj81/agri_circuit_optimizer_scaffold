# Phase 1 To Phase 2 Handoff

## Estado da transição

- `phase_1` está encerrada.
- `phase_2` deve iniciar sobre a baseline já validada do bundle canônico.
- o gate único de saída da fase anterior permanece `tests/decision_platform/test_phase1_exit_acceptance.py`.

## Baseline obrigatória

Use como fonte única de verdade da `phase_1` congelada:

- `docs/2026-04-04_phase1_exit.md`
- `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml` em `phase_1`
- `data/decision_platform/maquete_v2/scenario_bundle.yaml`
- `data/decision_platform/maquete_v2/component_catalog.csv`

## O que não deve ser reaberto na phase 2

- persistência do bundle canônico;
- contrato de catálogo e caminho `component_catalog.csv`;
- contrato de rotas, settings, topologia e layout já endurecidos;
- falha fechada dos entrypoints oficiais para layout legado sem manifesto.

Qualquer reabertura desses pontos exige justificativa objetiva e novo handoff explícito.

## Foco esperado da phase 2

A `phase_2` deve consumir a baseline acima para avançar no studio de nós e arestas, sem reinterpretar a `phase_1` como tema ainda aberto.

## Riscos operacionais remanescentes

Os pontos abaixo não reabrem escopo funcional da `phase_1`, mas precisam ser lembrados pelo próximo papel:

- o workspace local continua com arquivos modificados fora desta transição, incluindo `AGENTS.md`, `data/decision_platform/maquete_v2/README.md`, `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json` e `src/decision_platform/api/run_pipeline.py`;
- existem diretórios/docs não rastreados do bundle/autonomia fora do escopo funcional já congelado;
- o ambiente local ainda emite avisos de permissão para `.pytest-tmp-wave1-one/` e `.pytest-tmp-wave1-persistence/`.

## Regra prática para o próximo papel

Antes de iniciar qualquer mudança funcional da `phase_2`, tratar este handoff como congelamento de baseline e não como convite para completar ajustes pendentes da `phase_1`.
