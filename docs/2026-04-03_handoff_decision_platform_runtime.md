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

Checklist unico de saida da phase_0:

- `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml`, chave `phase_0.phase_exit_checklist`

Este handoff operacional deve permanecer coerente com esse checklist. Em caso de divergencia, trate o checklist como fonte de verdade para a saida de fase.

## Matriz canonica suportada

- `official_preflight`: triagem rapida de ambiente e politica; nao executa o pipeline completo e nao produz evidencia oficial suficiente
- `official`: gate oficial Julia-only com validacao completa de `summary.json` e artefatos principais; e o unico perfil que pode aparecer como `official_gate_complete=true`
- `diagnostic`: trilha diagnostica lean com override explicito de probe Julia real
- `diagnostic_comparison`: trilha diagnostica com comparacao explicita entre Julia e Python

## Comandos reproduzidos neste codebase em 2026-04-04

```powershell
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official -OfficialPreflight
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe
pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison
```

Suporte automatizado reproduzido nesta wave:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\scripts\test_decision_platform_runtime_validation.py -q --basetemp tests/_tmp/pytest-basetemp-wave5-script-suite
```

## Evidencia persistida

### 1. Perfil official_preflight

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_official_preflight_20260404-174138-977.json`

Campos observados no relatorio:

- `validation_profile = official_preflight`
- `validation_flow = preflight`
- `validation_sufficiency = triage_only`
- `official_gate_complete = false` no contrato automatizado desta fase
- `scenario_primary_engine = watermodels_jl`
- `scenario_fallback_engine = none`
- `julia_available = true`
- `watermodels_available = true`
- `runtime_policy_valid = true`
- `official_gate_valid = true`
- `runtime_policy_mode = official_julia_only`

Contrato de perfil observado:

- o preflight nao gera `summary.json`
- o preflight nao executa o pipeline completo
- o preflight nao substitui o gate `official`
- o relatorio do validador marca `success = true`
- o relatorio expõe `profile_config_path = C:\d\dev\agri_circuit_optimizer_scaffold\scripts\decision_platform_runtime_validation_profiles.json`

### 2. Perfil official

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_official_20260404-174150-905.json`

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
- `official_gate_complete = true` no contrato automatizado desta fase
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

### 3. Perfil diagnostic

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_diagnostic_20260404-174654-628.json`

Artefatos validados:

- `data/output/decision_platform/runtime_validation_diagnostic/summary.json`
- artefatos principais do candidato oficial do perfil diagnostico

Campos observados em `summary.json`:

- `execution_mode = diagnostic`
- `official_gate_valid = false`
- `official_gate_complete = false` no contrato automatizado desta fase
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

### 4. Perfil diagnostic_comparison

Relatorio salvo:

- `scripts/logs/decision-platform-runtime-validation_diagnostic_comparison_20260404-174654-321.json`

Artefatos validados:

- `data/output/decision_platform/runtime_validation_diagnostic_comparison/summary.json`
- `data/output/decision_platform/runtime_validation_diagnostic_comparison/engine_comparison.json`
- `data/output/decision_platform/runtime_validation_diagnostic_comparison/engine_comparison_candidates.csv`

Campos observados em `summary.json`:

- `execution_mode = diagnostic`
- `official_gate_valid = false`
- `official_gate_complete = false` no contrato automatizado desta fase
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

- a matriz declarativa suportada pelo validador canônico tem quatro perfis explicitos: `official_preflight`, `official`, `diagnostic` e `diagnostic_comparison`
- `official_preflight` permanece suportado apenas como triagem rapida e explicitamente insuficiente para evidencia oficial
- `official_gate_complete=true` e reservado ao perfil `official` no contrato automatizado desta fase
- o script canonico usa `summary.json` como fonte de verdade e valida os artefatos principais a partir dele
- o caminho oficial falha fechado se o override diagnostico estiver ativo no processo atual
- o caminho oficial nao exporta comparacao entre engines
- a trilha diagnostica exige opt-in explicito
- a comparacao entre Julia e Python fica restrita ao perfil `diagnostic_comparison`
- o contrato do relatorio do validador usa o campo unico `profile_config_path`

## Conclusao

A phase 0 fica fechada com evidencia operacional reproduzivel de que:

- a fonte de verdade da matriz canônica inclui quatro perfis explicitos, sem perfil oculto ou ambiguo
- o caminho oficial da `decision_platform` e Julia-only
- o gate oficial so vale com `execution_mode = official` e `official_gate_valid = true`
- `official_preflight` e apenas triagem de ambiente e politica, nao evidencia oficial suficiente
- qualquer execucao com `python_emulated_julia` permanece fora do gate oficial
- a comparacao Julia vs Python e diagnostica, opt-in e explicitamente marcada como invalida para o gate oficial

## Encerramento da phase_0

Esta phase termina congelada com os seguintes invariantes operacionais:

- a matriz canonica suportada permanece em quatro perfis: `official_preflight`, `official`, `diagnostic` e `diagnostic_comparison`
- `official_preflight` permanece `triage_only`
- `diagnostic` e `diagnostic_comparison` permanecem fora do gate oficial
- apenas `official` constitui evidencia oficial suficiente do gate Julia-only completo
- `official_gate_complete=true` permanece reservado ao perfil `official`

Transicao liberada para a proxima fase:

- trate `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml`, chave `phase_0.phase_exit_checklist`, como contrato congelado da phase encerrada
- use este handoff apenas como resumo operacional da evidencia ja reproduzida
- nao reabra a semantica do gate Julia-only na fase seguinte sem justificativa objetiva e nova aprovacao arquitetural
