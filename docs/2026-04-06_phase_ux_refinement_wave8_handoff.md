# Phase UX Refinement Wave 8 - Studio Quick Actions from Canvas Focus

## Objective

Reduce dependence on the secondary Studio workbench by exposing quick, guided actions directly from the current canvas focus.

## Delivered

- Added a new `Ações rápidas deste foco` section to the Studio focus panel so the operator can act from the first fold instead of immediately dropping into the full workbench.
- Exposed direct quick actions for the selected node and connection: move the focused node, duplicate the focused node, delete the focused connection, and open the full workbench when deeper editing is still necessary.
- Reused the existing Studio editing logic and callbacks instead of inventing a parallel editor, preserving the current business-first hierarchy and technical audit trail.
- Kept the secondary workbench available for full editing, but made it clearly a deeper layer rather than the only practical path for common Studio actions.
- Extended smoke coverage so the first-fold quick actions stay visible on the Studio surface and the focus panel continues to communicate rules and next steps.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_tab_surfaces_readiness_and_selection_context or studio_focus_panel_uses_canvas_selection_as_primary_context or studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas" --basetemp tests/_tmp/pytest-basetemp-ux-wave8-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave8-full-rerun
```

Result:

- `3 passed, 37 deselected in 0.55s`
- `40 passed in 402.01s`

## Evidence

- Structured Studio quick-action snapshot: `docs/2026-04-06_phase_ux_refinement_wave8_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, fail-closed behavior, queue/runs contracts, or backend decision logic.
- No change to solver, ranking, winner selection, or `technical_tie`.
- No reintroduction of raw JSON, logs, technical hubs, or form-led editing as the primary Studio surface.

## Honest Handoff

This wave moved the Studio a step closer to direct manipulation without pretending the workbench no longer matters. The main gain is that common actions now start where the user is already looking: the canvas focus rail. The detailed editor remains intact for auditability and full structural changes, but it stopped being the only practical action surface for the most common adjustments.
