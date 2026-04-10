# Phase UX Refinement Wave 8 - Assisted Final Choice

## Objective

Make the Decision surface explicit about the difference between automatic recommendation and final human choice, especially when `technical_tie` keeps the choice in assisted mode.

## Delivered

- Reworked the primary Decision strip so the first fold now distinguishes `winner sugerido`, `runner-up ainda comparável`, and `escolha final humana` instead of collapsing them into a generic manual-choice narrative.
- Updated the final-choice panel to show both the current automatic recommendation and the final human choice in the same block, which makes the assisted-decision flow explicit without expanding the page into a dense comparison surface.
- Renamed the assisted export CTA for `technical_tie` to `Exportar escolha humana assistida (...)`, aligning the export language with the real state of the decision.
- Kept `winner_clear` simple and confident while preserving blocked behavior for `winner_infeasible` and `no usable result`.
- Updated phase-4 acceptance coverage and smoke coverage to lock the new distinction between recommendation, assisted final choice, and blocked export states.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_workspace_panel_makes_winner_runner_up_and_tie_legible or decision_export_cta_tracks_manual_choice_without_overwriting_official_reference or primary_decision_panels_hide_raw_metric_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave8-targeted-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave8-phase4-targeted-rerun2
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave8-full-ui-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave8-phase4-full
```

Result:

- `3 passed, 108 deselected in 0.80s`
- `6 passed in 0.05s`
- `111 passed in 336.52s (0:05:36)`
- `6 passed in 0.07s`

## Evidence

- Structured Decision state snapshot: `docs/2026-04-09_phase_ux_refinement_wave8_ui_snapshot.json`
- This wave did not retry browser capture. The evidence remains structured and explicit because the change was semantic/flow-oriented and the earlier browser-capture blocker was already documented honestly.

## Scope Guardrails

- No architecture reopening.
- No changes to Dash/Cytoscape stack or Julia-only official execution policy.
- No reopening of Studio or Runs scope beyond the stabilized transition into Decision.
- No changes to solver, ranking core, hydraulic logic, or `docs/05_data_contract.md`.
- No return of raw JSON, logs, payloads, or dense technical grids as primary Decision surface.

## Honest Handoff

`ux_phase_4` can close on this baseline. The Decision page now makes the operator's role explicit: `winner_clear` remains an automatic recommendation ready to confirm, `technical_tie` remains a human-assisted final choice, and blocked states still block export and closure honestly. The next phase should move to consistency and polish only; it should not reopen the core Decision reading unless a concrete regression appears.
