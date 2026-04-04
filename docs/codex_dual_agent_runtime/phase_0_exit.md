# Phase 0 Exit Record

Status: encerrada para a `phase_0`

Data-base do registro: `2026-04-04`

## Fontes de verdade

- script canônico: `scripts/run_decision_platform_runtime_validation.ps1`
- matriz declarativa: `scripts/decision_platform_runtime_validation_profiles.json`
- manifesto regenerável da fase: `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
- registro operacional desta fase: este arquivo

Rastreabilidade bruta:

- os últimos relatórios relevantes por perfil ficam indexados no manifesto em `profiles.<profile>.last_report_path`
- este documento não depende de nomes timestampados copiados manualmente

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

## Evidência derivada do manifesto do validador

### `official_preflight`

Fonte estável:

- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
- entrada `profiles.official_preflight`

- `validation_profile=official_preflight`
- `validation_flow=preflight`
- `validation_sufficiency=triage_only`
- `status=passed`
- `evidence.julia_available=true`
- `evidence.watermodels_available=true`
- `evidence.watermodels_probe_mode=project_manifest_inventory`
- `evidence.runtime_policy_mode=official_julia_only`
- `evidence.official_gate_valid=true`
- esta run não exporta `summary.json` e não substitui o gate completo

### `official`

Fonte estável:

- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
- entrada `profiles.official`

- `validation_profile=official`
- `validation_flow=full`
- `validation_sufficiency=official_evidence`
- `status=passed`
- `evidence.execution_mode=official`
- `evidence.official_gate_valid=true`
- `evidence.runtime_policy_mode=official_julia_only`
- `evidence.selected_candidate_id`
- `evidence.engine_used=watermodels_jl`
- `evidence.forbidden_artifacts` inclui `engine_comparison.json` e `engine_comparison_candidates.csv`

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

Fonte estável:

- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
- entrada `profiles.diagnostic`

- `validation_profile=diagnostic`
- `validation_flow=full`
- `validation_sufficiency=diagnostic_evidence`
- `status=passed`
- `evidence.execution_mode=diagnostic`
- `evidence.official_gate_valid=false`
- `evidence.runtime_policy_mode=diagnostic_override_probe_disabled`
- `evidence.engine_used=python_emulated_julia`
- `evidence.forbidden_artifacts` inclui `engine_comparison.json`

### `diagnostic_comparison`

Fonte estável:

- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
- entrada `profiles.diagnostic_comparison`

- `validation_profile=diagnostic_comparison`
- `validation_flow=full`
- `validation_sufficiency=diagnostic_evidence`
- `status=passed`
- `evidence.execution_mode=diagnostic`
- `evidence.official_gate_valid=false`
- `evidence.runtime_policy_mode=diagnostic_override_probe_disabled`
- `evidence.engine_used=python_emulated_julia`
- `evidence.required_artifacts` inclui `engine_comparison.json` e `engine_comparison_candidates.csv`

## Contrato auditável usado neste encerramento

Campos mínimos lidos do relatório do validador:

- `validation_profile`
- `validation_flow`
- `validation_sufficiency`
- `official_gate_complete`
- `profile_config_path`
- `validation_manifest_path`
- `report_path`
- `runtime_scenario_dir`

Campos mínimos lidos do manifesto estável:

- `generated_at`
- `phase_id`
- `official_validation_profile`
- `official_validation_sufficiency`
- `profiles.<profile>.status`
- `profiles.<profile>.last_report_path`
- `profiles.<profile>.summary_path`
- `profiles.<profile>.evidence`

Campos mínimos lidos do runtime oficial em `summary.json`, quando o manifesto aponta um `summary_path` válido:

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
