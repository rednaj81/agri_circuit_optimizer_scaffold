# Phase UX Refinement Wave 7 - Decision Ready vs Assisted Split

## Objective

Reduce cognitive repetition around `technical_tie` and make ready decision versus assisted decision distinguishable by structure and signaling, not only by text.

## Delivered

- Reworked the Decision comparison strip so `winner_clear`, `technical_tie`, and blocked states now expose different strip titles and support-card structures.
- Reduced first-level repetition in `technical_tie`: the tie factor now lands once with primary weight instead of being echoed across multiple first-level cards.
- Kept `winner` and `runner-up` in the primary fold while making the assisted state read as a different structure from the ready state.
- Simplified the contrast panel for `technical_tie` so it no longer repeats the same factor in multiple support areas; the operator now gets a single primary tie explanation plus lighter secondary context.
- Updated smoke and phase-4 acceptance coverage to lock the new differentiation between `winner_clear` and `technical_tie`.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_workspace_panel_makes_winner_runner_up_and_tie_legible or primary_decision_panels_hide_raw_metric_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave7-targeted-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave7-phase4-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave7-full-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave7-phase4-full
```

Result:

- `2 passed, 109 deselected in 0.60s`
- `6 passed in 0.28s`
- `111 passed in 335.00s (0:05:34)`
- `6 passed in 0.04s`

## Evidence

- Structured Decision hierarchy snapshot: `docs/2026-04-09_phase_ux_refinement_wave7_ui_snapshot.json`
- This wave did not retry browser capture. The change was about structural hierarchy and narrative deduplication, and the previously blocked browser-capture route was not necessary for honest evidence.

## Scope Guardrails

- No architecture reopening.
- No changes to Dash/Cytoscape stack or Julia-only official execution policy.
- No reopening of Studio or Runs scope beyond the existing transition into Decision.
- No changes to solver, ranking core, hydraulic logic, or `docs/05_data_contract.md`.
- No return of raw JSON, logs, payloads, or dense technical grids as primary Decision surface.

## Honest Handoff

This wave improves real scan speed instead of adding more copy. `Winner_clear` now reads as a ready-to-confirm structure, `technical_tie` reads as an assisted-decision structure, and blocked states remain visually and semantically separate. The primary tie factor is still visible, but it is no longer repeated with the same weight across multiple first-level panels.
