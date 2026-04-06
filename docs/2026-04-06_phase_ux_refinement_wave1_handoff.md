# Phase UX Refinement Wave 1 - Direct Edge Correction On The Studio Canvas

## Objective

Close a remaining gap in the approved wave without reopening architecture: keep the existing business-first shell intact, but let the operator understand and correct edge direction directly from the Studio canvas and immediate connectivity guidance instead of falling back to the advanced workbench.

## Delivered

- Preserved the current `decision_platform` shell and the four primary product spaces already present in the branch baseline: Studio, Runs, Decisão and Auditoria.
- Added the `reverse-edge` action to the Studio canvas context menu in `src/decision_platform/ui_dash/app.py`, so an operator can invert a selected connection directly on the business graph.
- Extended `render_studio_connectivity_panel(...)` with a local action card that explains the active business flow in plain language, previews what changes if the edge is reversed, and summarizes the readiness impact before the user acts.
- Passed `nodes_rows` and `candidate_links_rows` into the initial Studio connectivity render, so the same local edge-action guidance is available from first paint and not only after callbacks refresh the panel.
- Updated `apply_studio_context_menu_action(...)` to execute the new canvas action, preserve selection, and report whether the inversion reduces blockers, keeps the scenario ready, or changes the gate to Runs.
- Hardened `reverse_edge_studio_selection(...)` so edge reversal fails closed on blank endpoints, self-loops or unknown nodes instead of masking invalid graph state.
- Updated `tests/decision_platform/test_studio_structure.py` and `tests/decision_platform/test_ui_smoke.py` to lock the new context-menu action, the readiness-aware status message and the business-language preview in the Studio connectivity panel.
- Refreshed the structured evidence artifact in `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json` to match the current canvas-first edge-correction flow and the latest validation count.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_studio_structure.py tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-dev-wave1-reverse
```

Result:

- `89 passed in 614.52s (0:10:14)`

## Evidence

- Structured Studio connectivity snapshot: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No change to the Julia-only official execution path.
- No backend solver, queue semantics, ranking logic or hydraulic-model changes.
- No promotion of raw JSON, debug payloads or technical internals back to the primary Studio surface.

## Honest Handoff

The navigation cleanup and workspace-first Studio shell were already present on the branch baseline when this wave started; I did not reopen or rework those surfaces. This wave concentrated on one specific UX gap that still forced users toward advanced paths: correcting edge direction. The result is a direct canvas action with readiness-aware guidance and tests to keep it stable. Evidence is still structured rather than screenshot-based, and the repository still contains unrelated dirty files outside this wave scope.
