# Execução em Julia, fila e gestão de runs

## Objetivo
Executar cenários em background, com isolamento e acompanhamento.

## Requisitos
- run oficial apenas por Julia
- sem fallback no caminho oficial
- comparação Julia vs Python apenas por opt-in explícito
- `python_emulated_julia` apenas para auditoria, comparação ou testes
- cada cenário pode ter vários runs
- cada run tem status próprio
- runs simultâneos não se bloqueiam mutuamente, salvo locks intencionais
- logs por run
- artefatos por run
- cancelamento e re-run
- re-run explícito deve aceitar qualquer run terminal (`completed`, `failed`, `canceled`) com novo `run_id` e vínculo rastreável com a execução de origem

## Estados de run
- queued
- preparing
- running
- exporting
- completed
- failed
- canceled

## Entidades mínimas
- scenario
- scenario_version
- run_job
- run_event
- artifact
- queue_worker

## Telemetria mínima
- engine_requested
- engine_used
- engine_mode
- julia_available
- watermodels_available
- real_julia_probe_disabled
- execution_mode
- official_gate_valid
- started_at
- finished_at
- duration_s
- policy_mode
- policy_message
- failure_reason
- failure_stacktrace_excerpt

## Regra crítica
Se Julia falhar no caminho oficial:
- falhar fechado
- não cair silenciosamente para Python
- se `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1` estiver ativo, falhar informando que a execução é inválida para o gate oficial

Se for necessário rodar comparação diagnóstica:
- habilitar explicitamente a trilha de comparação
- habilitar explicitamente qualquer override diagnóstico
- registrar que `python_emulated_julia` não compõe o candidato oficial
- registrar em artefato exportado que a sonda Julia real foi desabilitada e que a execução não vale como gate oficial

## Fluxo operacional da fase 0
- validador canônico: `scripts/run_decision_platform_runtime_validation.ps1`
- modo official:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official`
- modo diagnostic lean:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe`
- modo diagnostic com comparação:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison`
- o modo official falha se detectar override diagnóstico no ambiente, `official_gate_valid=false` ou `engine_comparison.json`
- o modo diagnostic exige `official_gate_valid=false`, override explícito e valida a marcação diagnóstica em `summary.json`
- o validador cruza `summary.json` com `selected_candidate.json`, `selected_candidate_routes.json`, `selected_candidate_explanation.json`, `selected_candidate_bom.csv`, `family_summary.csv` e `infeasibility_summary.json`
- `engine_comparison.json` e `engine_comparison_candidates.csv` só são aceitos quando `-IncludeEngineComparison` foi pedido explicitamente
