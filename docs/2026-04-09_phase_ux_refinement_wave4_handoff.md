# Phase UX Refinement Wave 4 - Decision First Fold

## Objective

Open `ux_phase_4` by making the first fold of `Decisão` readable as a product surface: explicit decision state, winner, runner-up, honest gating, and clear technical-tie guidance before dense comparison panels.

## Delivered

- Reworked `render_decision_workspace_panel` into a stronger first-fold hierarchy centered on a decision hero, not a flat grid of same-weight cards.
- Promoted the four primary outcomes to the main surface:
  - clear winner
  - technical tie
  - no usable decision yet
  - visible but infeasible winner
- Kept `winner`, `runner-up`, and `Próxima ação segura` in the primary fold, while pushing comparative density, profile views, and export context behind disclosure.
- Preserved the honest Runs -> Decision gate: the Decision surface now stays explicit about blocked or inconclusive states instead of borrowing confident export language.
- Added a dedicated phase-4 acceptance suite for the Decision first fold.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_workspace_panel_makes_winner_runner_up_and_tie_legible or decision_workspace_panel_blocks_primary_choice_without_usable_result or decision_workspace_panel_surfaces_infeasible_winner_as_blocked_state" --basetemp tests/_tmp/pytest-basetemp-ux-wave4-targeted-ui-rerun2
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4-phase4-targeted-rerun2
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4-full-ui-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4-phase4-full-rerun
```

Result:

- `3 passed, 108 deselected in 0.60s`
- `4 passed in 0.26s`
- `111 passed in 328.26s (0:05:28)`
- `4 passed in 0.04s`

## Evidence

- Structured Decision snapshot: `docs/2026-04-09_phase_ux_refinement_wave4_ui_snapshot.json`
- Real browser evidence was attempted by launching the local Dash UI on port `8056`, but the background server exited before opening the socket and produced no stdout/stderr traces; connection checks returned `connection refused`. This wave documents that blocker explicitly instead of claiming a screenshot that did not land.

## Scope Guardrails

- No architecture reopening.
- No change to the Dash/Cytoscape stack or Julia-only official execution policy.
- No change to the accepted Studio baseline from `ux_phase_2`.
- No reopening of Runs beyond preserving the already-stabilized transition into Decision.
- No change to solver, ranking core, or `docs/05_data_contract.md`.

## Honest Handoff

This wave is a real phase opening, not a cosmetic text pass. The primary gain is that `Decisão` now answers, in the first fold, whether the operator has a clear winner, a technical tie, a blocked winner, or no usable decision yet. Winner and runner-up read as the main objects of comparison before the deeper comparison stack opens, and blocked states no longer reuse confident export language. The browser-capture attempt failed, but the blocker is explicit and the structured snapshot plus green suites are sufficient to continue `ux_phase_4` on top of this Decision baseline.
