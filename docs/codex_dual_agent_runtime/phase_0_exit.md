# Phase 0 Exit Record

Status: encerrada para a `phase_0`

Data-base do registro: `2026-04-04`

## Fontes de verdade

- script canônico: `scripts/run_decision_platform_runtime_validation.ps1`
- matriz declarativa: `scripts/decision_platform_runtime_validation_profiles.json`
- registro operacional desta fase: este arquivo

Relatórios usados para derivar este registro:

- `scripts/logs/decision-platform-runtime-validation_official_preflight_20260404-175037-758.json`
- `scripts/logs/decision-platform-runtime-validation_official_20260404-175049-236.json`
- `scripts/logs/decision-platform-runtime-validation_diagnostic_20260404-174813-118.json`
- `scripts/logs/decision-platform-runtime-validation_diagnostic_comparison_20260404-174813-348.json`

## Regra de encerramento

- o caminho oficial continua `Julia-only` e `fail-closed`
- apenas o profile `official` com `validation_sufficiency=official_evidence` conta como validação oficial suficiente
- o profile `official_preflight` é apenas triagem operacional rápida
- os profiles `diagnostic` e `diagnostic_comparison` continuam auxiliares e não contam como aprovação oficial da fase

## Matriz aprovada de perfis

| profile | validation_flow | validation_sufficiency | papel operacional | conta como evidência oficial? |
| --- | --- | --- | --- | --- |
| `official_preflight` | `preflight` | `triage_only` | detectar cedo override proibido, configuração oficial inválida ou indisponibilidade de Julia/WaterModels sem rodar o pipeline completo | não |
| `official` | `full` | `official_evidence` | validar o runtime oficial com Julia real, `summary.json` e artefatos centrais do candidato oficial | sim |
| `diagnostic` | `full` | `diagnostic_evidence` | validar exports centrais e coerência do candidato com override diagnóstico explícito | não |
| `diagnostic_comparison` | `full` | `diagnostic_evidence` | executar a trilha diagnóstica explícita com comparação entre engines | não |

## Evidência derivada dos relatórios do validador

### `official_preflight`

Relatório: `scripts/logs/decision-platform-runtime-validation_official_preflight_20260404-175037-758.json`

- `validation_profile=official_preflight`
- `validation_flow=preflight`
- `validation_sufficiency=triage_only`
- etapa `2. Executar preflight oficial`: `julia_available=true`
- etapa `2. Executar preflight oficial`: `watermodels_available=true`
- etapa `2. Executar preflight oficial`: `watermodels_probe_mode=project_manifest_inventory`
- etapa `2. Executar preflight oficial`: `runtime_policy_mode=official_julia_only`
- etapa `2. Executar preflight oficial`: `official_gate_valid=true`
- esta run não exporta `summary.json` e não substitui o gate completo

### `official`

Relatório: `scripts/logs/decision-platform-runtime-validation_official_20260404-175049-236.json`

- `validation_profile=official`
- `validation_flow=full`
- `validation_sufficiency=official_evidence`
- etapa `3. Validar summary.json`: `execution_mode=official`
- etapa `3. Validar summary.json`: `official_gate_valid=true`
- etapa `3. Validar summary.json`: `runtime_policy_mode=official_julia_only`
- etapa `3. Validar summary.json`: `selected_candidate_id=bus_with_pump_islands__g18m1_1`
- etapa `4. Validar artefatos principais`: `engine_used=watermodels_jl`
- etapa `5. Validar artefatos do perfil`: `engine_comparison.json` e `engine_comparison_candidates.csv` proibidos

Campos exportados em `data/output/decision_platform/runtime_validation_official/summary.json` usados por este encerramento:

- `execution_mode`
- `official_gate_valid`
- `engine_requested`
- `engine_used`
- `engine_mode`
- `runtime_policy_mode`
- `runtime_policy_message`
- `real_julia_probe_disabled`
- `runtime.started_at`
- `runtime.finished_at`
- `runtime.duration_s`
- `selected_candidate_id`

### `diagnostic`

Relatório: `scripts/logs/decision-platform-runtime-validation_diagnostic_20260404-174813-118.json`

- `validation_profile=diagnostic`
- `validation_flow=full`
- `validation_sufficiency=diagnostic_evidence`
- etapa `2. Executar pipeline`: ambiente com `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1`
- etapa `3. Validar summary.json`: `execution_mode=diagnostic`
- etapa `3. Validar summary.json`: `official_gate_valid=false`
- etapa `3. Validar summary.json`: `runtime_policy_mode=diagnostic_override_probe_disabled`
- etapa `4. Validar artefatos principais`: `engine_used=python_emulated_julia`
- etapa `5. Validar artefatos do perfil`: `engine_comparison.json` proibido

### `diagnostic_comparison`

Relatório: `scripts/logs/decision-platform-runtime-validation_diagnostic_comparison_20260404-174813-348.json`

- `validation_profile=diagnostic_comparison`
- `validation_flow=full`
- `validation_sufficiency=diagnostic_evidence`
- etapa `2. Executar pipeline`: ambiente com `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1`
- etapa `3. Validar summary.json`: `execution_mode=diagnostic`
- etapa `3. Validar summary.json`: `official_gate_valid=false`
- etapa `3. Validar summary.json`: `runtime_policy_mode=diagnostic_override_probe_disabled`
- etapa `4. Validar artefatos principais`: `engine_used=python_emulated_julia`
- etapa `5. Validar artefatos do perfil`: `engine_comparison.json` e `engine_comparison_candidates.csv` obrigatórios quando a comparação é pedida explicitamente

## Contrato auditável usado neste encerramento

Campos mínimos lidos do relatório do validador:

- `validation_profile`
- `validation_flow`
- `validation_sufficiency`
- `profile_config_path`
- `steps[].name`
- `steps[].status`
- `steps[].details`
- `report_path`
- `runtime_scenario_dir`

Campos mínimos lidos do runtime oficial em `summary.json`:

- `execution_mode`
- `official_gate_valid`
- `engine_requested`
- `engine_used`
- `engine_mode`
- `runtime_policy_mode`
- `runtime_policy_message`
- `real_julia_probe_disabled`
- `runtime.started_at`
- `runtime.finished_at`
- `runtime.duration_s`

Campos mínimos exigidos do runtime diagnóstico com comparação:

- `engine_comparison.json`
- `engine_comparison_candidates.csv`
- `execution_policy`
- `runtime`

## Comandos canônicos aprovados

```powershell
# profile: official_preflight
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official -OfficialPreflight

# profile: official
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official

# profile: diagnostic
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe

# profile: diagnostic_comparison
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison
```

## Handoff para a próxima fase

- não reabrir a discussão conceitual sobre `Julia-only` no caminho oficial sem fato objetivo novo
- continuar tratando `scripts/run_decision_platform_runtime_validation.ps1` e `scripts/decision_platform_runtime_validation_profiles.json` como fonte operacional principal
- usar este registro como resumo humano auditável da `phase_0`
- qualquer evolução de fase seguinte deve preservar `official_gate_valid=true` apenas no profile `official` com Julia real
