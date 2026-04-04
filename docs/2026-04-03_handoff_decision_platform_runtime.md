## Handoff -- Runtime Validation Phase 0

Data: 2026-04-04
Branch: `codex/new-architecture-platform`

## Objetivo deste handoff

Registrar apenas a evidencia operacional reproduzida na phase 0 para o gate Julia-only da `decision_platform`.

Escopo deste documento:

- caminho oficial Julia-only
- trilha diagnostica com opt-in explicito
- script canonico `scripts/run_decision_platform_runtime_validation.ps1`
- artefatos persistidos em `data/output/decision_platform/runtime_validation_*`

Este documento nao reabre arquitetura funcional de V1/V2/V3.

## Comandos canonicos executados nesta wave

```powershell
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison
```

Suporte automatizado executado na mesma rodada:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_run_pipeline_cli.py tests\decision_platform\test_runtime_validation_script.py -q --basetemp tests/_tmp/pytest-basetemp-wave3-target
.\.venv\Scripts\python.exe -m pytest tests\scripts\test_decision_platform_runtime_validation.py -q --basetemp tests/_tmp/pytest-basetemp-wave3-script-suite
```

## Evidencia persistida

### 1. Perfil official

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_official_20260404-171759-547.json`

Artefatos validados:

- `data/output/decision_platform/runtime_validation_official/summary.json`
- `data/output/decision_platform/runtime_validation_official/selected_candidate.json`
- `data/output/decision_platform/runtime_validation_official/selected_candidate_routes.json`
- `data/output/decision_platform/runtime_validation_official/selected_candidate_explanation.json`
- `data/output/decision_platform/runtime_validation_official/selected_candidate_bom.csv`
- `data/output/decision_platform/runtime_validation_official/family_summary.csv`
- `data/output/decision_platform/runtime_validation_official/infeasibility_summary.json`

Campos observados em `summary.json`:

- `execution_mode = official`
- `official_gate_valid = true`
- `engine_requested = watermodels_jl`
- `engine_used = watermodels_jl`
- `engine_mode = real_julia`
- `real_julia_probe_disabled = false`
- `runtime_policy_mode = official_julia_only`
- `selected_candidate_id = bus_with_pump_islands__g18m1_1`

Contrato de perfil observado:

- `engine_comparison.json` nao existe
- `engine_comparison_candidates.csv` nao existe
- o relatorio do validador marca `success = true`
- o relatorio expõe `profile_config_path = C:\d\dev\agri_circuit_optimizer_scaffold\scripts\decision_platform_runtime_validation_profiles.json`

### 2. Perfil diagnostic

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_diagnostic_20260404-171626-776.json`

Artefatos validados:

- `data/output/decision_platform/runtime_validation_diagnostic/summary.json`
- artefatos principais do candidato oficial do perfil diagnostico

Campos observados em `summary.json`:

- `execution_mode = diagnostic`
- `official_gate_valid = false`
- `engine_requested = watermodels_jl`
- `engine_used = python_emulated_julia`
- `engine_mode = fallback_emulated`
- `real_julia_probe_disabled = true`
- `runtime_policy_mode = diagnostic_override_probe_disabled`
- `selected_candidate_id = loop_ring__g18m1_1`

Contrato de perfil observado:

- `engine_comparison.json` nao existe
- `engine_comparison_candidates.csv` nao existe
- a mensagem de politica menciona explicitamente `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE`
- o relatorio do validador marca `success = true`

### 3. Perfil diagnostic_comparison

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_diagnostic_comparison_20260404-171626-120.json`

Artefatos validados:

- `data/output/decision_platform/runtime_validation_diagnostic_comparison/summary.json`
- `data/output/decision_platform/runtime_validation_diagnostic_comparison/engine_comparison.json`
- `data/output/decision_platform/runtime_validation_diagnostic_comparison/engine_comparison_candidates.csv`

Campos observados em `summary.json`:

- `execution_mode = diagnostic`
- `official_gate_valid = false`
- `engine_used = python_emulated_julia`
- `real_julia_probe_disabled = true`
- `runtime_policy_mode = diagnostic_override_probe_disabled`
- `selected_candidate_id = loop_ring__g18m1_1`

Campos observados em `engine_comparison.json`:

- `comparison_policy.official_runtime = julia_only_fail_closed`
- `comparison_policy.python_emulation = diagnostic_only_explicit_opt_in`
- `execution_policy.execution_mode = diagnostic`
- `execution_policy.official_gate_valid = false`
- `execution_policy.real_julia_probe_disabled = true`
- `runtime.execution_mode = diagnostic`
- `runtime.official_gate_valid = false`
- `scenario_comparisons.maquete_v2.same_winner = true`

Leitura correta do artefato de comparacao:

- este arquivo pertence apenas ao perfil `diagnostic_comparison`
- ele nao tem validade para o gate oficial
- ele nao deve ser usado para inferir o vencedor do perfil `official`
- a prova oficial do caminho Julia-only continua sendo `runtime_validation_official/summary.json`

## Comportamento operacional confirmado

- o script canonico usa `summary.json` como fonte de verdade e valida os artefatos principais a partir dele
- o caminho oficial falha fechado se o override diagnostico estiver ativo no processo atual
- o caminho oficial nao exporta comparacao entre engines
- a trilha diagnostica exige opt-in explicito
- a comparacao entre Julia e Python fica restrita ao perfil `diagnostic_comparison`
- o contrato do relatorio do validador usa o campo unico `profile_config_path`

## Conclusao

A phase 0 fica fechada com evidencia operacional reproduzivel de que:

- o caminho oficial da `decision_platform` e Julia-only
- o gate oficial so vale com `execution_mode = official` e `official_gate_valid = true`
- qualquer execucao com `python_emulated_julia` permanece fora do gate oficial
- a comparacao Julia vs Python e diagnostica, opt-in e explicitamente marcada como invalida para o gate oficial
