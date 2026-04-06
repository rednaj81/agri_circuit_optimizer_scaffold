# Phase UX Refinement Wave 1 - Navigation and Information Architecture Cleanup

## Objective

Execute `ux_phase_1` without reopening architecture: make the main product journey clearer, reinforce Studio, Runs, Decisão and Auditoria as the four primary spaces, and reduce first-fold dependence on raw technical panels.

## Delivered

- Kept the product shell centered on the four primary spaces and preserved the guided shell already present in `src/decision_platform/ui_dash/app.py`.
- Added a new first-fold `studio-workspace-panel` that consolidates readiness, current focus, Runs gate and next action into one primary Studio reading instead of forcing the operator into multiple secondary cards.
- Moved the broader Studio context into `studio-context-detailed-panels`, so readiness, projection coverage, focus and connectivity remain available but no longer dominate the first fold as separate primary surfaces.
- Extended Studio navigation so the new workspace panel can open the workbench, open Runs when readiness allows and keep Auditoria accessible as progressive depth.
- Updated smoke and structural tests in `tests/decision_platform/test_ui_smoke.py` and `tests/decision_platform/test_studio_structure.py` to lock the new hierarchy, CTA wiring and progressive disclosure structure.
- Regenerated structured evidence in `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json` for the current worktree state.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider -k "dash_app_surfaces_only_four_primary_product_spaces or product_space_banner_uses_consistent_product_language_for_each_space or studio_tab_surfaces_readiness_and_selection_context or studio_workspace_panel_unifies_focus_connectivity_and_runs_gate or dash_app_exposes_structural_studio_controls" --basetemp tests\_tmp\pytest-basetemp-ux-wave1-targeted-current
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests\_tmp\pytest-basetemp-ux-wave1-dev
```

Result:

- `5 passed, 70 deselected in 0.73s`
- `75 passed in 431.35s (0:07:11)`

## Evidence

- Structured shell and Studio snapshot: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, fail-closed behavior, queue semantics or backend decision logic.
- No reintroduction of raw JSON, logs or technical internal graph entities as the primary Studio surface.

## Honest Handoff

This wave now does more than a cosmetic tab cleanup. The shell still frames the product as one journey across Studio, Runs, Decisão and Auditoria, but the main user gain is inside Studio: the first fold now answers what is in focus, whether Runs is unlocked and what to do next before the operator needs to open detailed technical context. The dense technical surfaces still exist and remain auditable, but they were pushed behind progressive disclosure instead of competing with the primary reading of the product.
