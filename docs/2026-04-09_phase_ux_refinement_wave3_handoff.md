# Phase UX Refinement Wave 3 - Runs Phase Close

## Objective

Close `ux_phase_3` with one last meaningful gain in visual hierarchy and real-use validation: make the first fold of Runs feel decisively centered on `run em foco`, current state, and safe next action, while documenting whether browser evidence could be produced.

## Delivered

- Added a compact first-fold progress rail in the Runs workspace so `queued`, `preparing`, `running`, `exporting`, `completed`, `failed`, and `canceled` are distinguishable by presentation and progression, not only by copy.
- Reduced the feeling of same-weight cards by removing one primary-state card from the focus fold and shifting more emphasis into the focus headline, progress rail, and tinted `Próxima ação segura` block.
- Kept the strongest states visually distinct: `failed` and `canceled` now end in an explicit final-state rail block, while `completed com resultado` and `running/preparing` present different progression and action emphasis.
- Preserved the honest Runs -> Decision gate and the secondary place of technical disclosure, while keeping the workspace text lighter than in the previous wave.
- Prepared documentation to close `ux_phase_3` and hand off cleanly into `ux_phase_4` without preemptively implementing Decision work.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "runs_workspace_panel_prioritizes_queue_focus_and_primary_transition or runs_workspace_panel_contrasts_failed_and_canceled_focus_states or runs_workspace_panel_uses_refresh_cta_for_intermediate_execution_states or runs_workspace_panel_distinguishes_failure_recovery_from_decision_ready" --basetemp tests/_tmp/pytest-basetemp-ux-wave3-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase3_runs_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-phase3-smoke
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-full-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase3_queue_acceptance.py tests/decision_platform/test_phase3_runs_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-phase3-full
```

Result:

- `4 passed, 105 deselected in 0.59s`
- `1 passed in 30.83s`
- `109 passed in 335.79s (0:05:35)`
- `14 passed in 61.87s (0:01:01)`

## Evidence

- Structured Runs snapshot: `docs/2026-04-09_phase_ux_refinement_wave3_ui_snapshot.json`
- Browser capture attempt via local Edge headless failed because the browser could not create its Crashpad/ProcessSingleton files in this environment. The wave documents that failure explicitly instead of claiming a screenshot that did not land.

## Scope Guardrails

- No architecture reopening.
- No stack replacement beyond the existing Dash/Cytoscape surface.
- No change to Julia-only official execution policy or fail-closed behavior.
- No change to the accepted Studio baseline except preserving the gate into Runs.
- No change to hydraulic core logic or `docs/05_data_contract.md`.

## Honest Handoff

This wave is a real phase-close, not a wording pass. The visible gain is that the first fold of Runs now has a stronger center of gravity: focus run, progression, recovery, and safe action read faster than before, and history has stayed secondary. Browser evidence was attempted and failed for environmental reasons, but the failure is explicit and the structured snapshot plus green suites are strong enough to close `ux_phase_3` without pretending there was a screenshot.
