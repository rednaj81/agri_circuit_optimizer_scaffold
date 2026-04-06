# Runtime bootstrap

## Estado preparado

Este repositório já foi preparado para a rodada autônoma de UX:

- bundle extraído em `docs/ux_refinement_autonomy_bundle/`
- agentes instalados em `.codex/agents/`
- skill instalada em `.codex/skills/ux_refinement/`
- `phase_ux_refinement` registrado em `automation/phase_plan.yaml`
- guidance de UX gravável em `docs/codex_dual_agent_runtime/supervisor_guidance.json`

## Preparar novamente

```powershell
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File .\scripts\Prepare-UxRefinementAutonomy.ps1 -InstallTemplates
```

## Iniciar rodada autônoma de UX

```powershell
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File .\scripts\Start-UxRefinementAutonomy.ps1
```

Defaults:

- fase do loop: `phase_ux_refinement`
- fase ativa de UX: `ux_phase_1`
- `max_waves = 10`
- watchdog: `60s`
- supervisor estratégico de UX: `20min`
- duração máxima do laço estratégico: `18h`

## Acompanhar estado

```powershell
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File .\scripts\Test-CodexSupervisorApi.ps1 -Action summary
```

## Regerar guidance de UX manualmente

```powershell
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File .\scripts\Invoke-UxRefinementStrategicSupervisor.ps1 -ActiveUxPhaseId ux_phase_1
```

## Artefatos principais

- prompt curto: `docs/ux_refinement_autonomy_bundle/prompts/PROMPT_SHORT_BOOTSTRAP_UI_REFINEMENT.md`
- prompt completo: `docs/ux_refinement_autonomy_bundle/prompts/PROMPT_FULL_AUTONOMOUS_UI_REFINEMENT.md`
- plano de fases: `docs/ux_refinement_autonomy_bundle/automation/phase_plan.yaml`
- log do supervisor estratégico de UX: `docs/codex_dual_agent_runtime/api/ux_strategic_supervisor.log`
