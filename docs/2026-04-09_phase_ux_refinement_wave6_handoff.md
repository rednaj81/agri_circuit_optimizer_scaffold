# Phase UX Refinement Wave 6 - Decision Comparison Read

## Objective

Improve the primary comparative read of `winner` versus `runner-up` and make `technical_tie` more operationally explicit without rebuilding the Decision surface into a dense technical comparison area.

## Delivered

- Refined the primary Decision workspace so `technical_tie` now explains what remains tied in product language instead of only labeling the state.
- Adjusted `Próxima ação segura` and manual-choice copy for `technical_tie` so the page no longer sounds like the choice is already resolved or export-ready by default.
- Strengthened the comparative narrative between `winner` and `runner-up` by surfacing tie factors and pressure signals earlier in the main fold and in the contrast panel.
- Kept the blocked/export coherence from wave 5 intact while improving the assisted narrative for `technical_tie`.
- Expanded phase-4 and smoke coverage to lock the new tie explanation and comparison-focused primary read.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_workspace_panel_makes_winner_runner_up_and_tie_legible or primary_decision_panels_hide_raw_metric_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave6-targeted-ui-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave6-phase4-targeted-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave6-full-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave6-phase4-full
```

Result:

- `2 passed, 109 deselected in 0.61s`
- `6 passed in 0.05s`
- `111 passed in 317.98s (0:05:17)`
- `6 passed in 0.04s`

## Evidence

- Structured comparison snapshot: `docs/2026-04-09_phase_ux_refinement_wave6_ui_snapshot.json`
- This wave did not retry real browser capture. The change was centered on comparison narrative and assisted-state explanation, and the previously blocked browser-capture path remained unnecessary for honest evidence.

## Scope Guardrails

- No architecture reopening.
- No changes to Dash/Cytoscape stack or Julia-only official execution policy.
- No reopening of Studio or Runs scope beyond the existing transition into Decision.
- No changes to solver, ranking core, hydraulic logic, or `docs/05_data_contract.md`.
- No return of raw JSON, logs, or dense technical grids as the main Decision reading surface.

## Honest Handoff

This wave adds real product clarity instead of more comparison density. The Decision page now explains why `winner` still leads, why `runner-up` remains relevant, and what is actually tied when `technical_tie` is active. The safe action in the tie state now reads like an assisted decision step, not like a nearly finished export. Blocked and ready states remain separated the same way they were after wave 5.
