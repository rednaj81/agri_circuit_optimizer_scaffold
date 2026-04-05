# Phase 1 Artifact UTF-8 Correction Handoff

## Objective

Restore the sealed administrative closeout of `phase_1` without reopening any product scope.

## What Changed

- `docs/codex_dual_agent_runtime/supervisor_guidance.json` was restored to the sealed `phase_closed` reading expected by the `phase_1` artifact gate and rewritten as plain UTF-8 without BOM.
- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json` was restored to the mixed runtime-plus-phase-closeout shape that preserves `profiles` and `phase_1_exit_validation` together.
- `scripts/Invoke-CodexStrategicSupervisor.ps1` now writes JSON as UTF-8 without BOM and respects the sealed `phase_1` state already declared by the manifest instead of reopening it administratively.
- `scripts/run_decision_platform_runtime_validation.ps1` now writes JSON as UTF-8 without BOM and preserves the sealed `phase_1` administrative block when refreshing runtime profile evidence.
- `automation/codex_dual_agent_loop.py` and `automation/codex_supervisor_api.py` now normalize UTF-8 writes defensively to avoid reintroducing a leading BOM from local automation paths.

## Validated State

- `tests/decision_platform/test_phase1_exit_artifacts.py`
- `tests/decision_platform/test_phase3_queue_acceptance.py`
- `tests/decision_platform/test_runtime_validation_script.py`
- `tests/decision_platform -m fast -q -p no:cacheprovider`

## Honest Limits

- This wave did not add or modify any `phase_3` product capability.
- The `Studio`, queue semantics, official Julia-only runtime path, and bundle contracts were not changed functionally.
- The correction is administrative and operational only: artifact encoding, preserved manifest shape, and phase-closeout coherence.
