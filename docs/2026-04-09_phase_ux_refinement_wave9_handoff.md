# Phase UX Refinement Wave 9 - Consistency And Semantic Polish

## Objective

Open `ux_phase_5` by tightening terminology and confirmation language across the primary product surfaces without reopening the already stabilized Studio, Runs, and Decision flows.

## Delivered

- Normalized ready-state Decision language so `winner_clear` now reads as `confirmação final` instead of sounding like another assisted state.
- Kept `technical_tie` explicitly assisted while leaving blocked states blocked, which preserves the semantic ladder between ready, assisted, and blocked decisions.
- Softened Runs-to-Decision copy so completed runs now talk about opening `Decisão` and carrying usable decision context, instead of implying that every downstream decision remains assisted.
- Aligned product-space banner objectives so `Runs` points to opening `Decisão`, while `Decisão` keeps the assisted wording only where human tie resolution is still needed.
- Updated smoke and phase-4 acceptance coverage to lock the ready-versus-assisted terminology split.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "runs_workspace_panel_prioritizes_queue_focus_and_primary_transition or studio_runs_decision_primary_journey_uses_consistent_transition_language" --basetemp tests/_tmp/pytest-basetemp-ux-wave9-targeted-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave9-phase4-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave9-full-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave9-phase4-full
```

Result:

- `2 passed, 109 deselected in 0.63s`
- `6 passed in 0.06s`
- `111 passed in 332.13s (0:05:32)`
- `6 passed in 0.05s`

## Evidence

- Structured consistency snapshot: `docs/2026-04-09_phase_ux_refinement_wave9_ui_snapshot.json`
- This wave did not spend time retrying browser capture. The change was semantic and cross-surface, so structured excerpts are the honest evidence baseline here.

## Scope Guardrails

- No architecture reopening.
- No changes to Dash/Cytoscape stack or Julia-only official execution policy.
- No reopening of Studio, Runs, or Decision logic beyond consistency-level copy alignment.
- No changes to solver, ranking core, hydraulic logic, or `docs/05_data_contract.md`.
- No return of raw JSON, logs, payloads, or dense technical grids as primary surface.

## Honest Handoff

This wave adds coherence, not new flow. `Winner_clear` now sounds ready to confirm, `technical_tie` still sounds explicitly assisted, and Runs no longer suggests that every usable result must end in an assisted decision. `ux_phase_5` is now open on a clearer semantic baseline and can continue with polish/stabilization without reopening the closed journey architecture.
