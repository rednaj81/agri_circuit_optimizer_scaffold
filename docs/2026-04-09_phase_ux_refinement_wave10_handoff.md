# Phase UX Refinement Wave 10 - Studio Supply Chain And Final Stabilization

## Objective

Use the final stabilization wave on the highest remaining UX risk: make the Studio read more clearly as a supply chain surface and reduce dependence on the advanced workbench for a common route edit.

## Delivered

- Promoted `Quem supre quem neste foco` into the primary Studio fold so the current business chain is visible before opening secondary disclosures.
- Added direct route-intent actions to the main Studio context panel with `Obrigatória`, `Desejável`, and `Opcional` buttons for the route already in focus.
- Kept the direct route-intent action local to the focused route and reused the existing route-intent callback path instead of reopening Studio architecture.
- Preserved the existing business-only canvas surface: no internal hubs, derived technical nodes, raw JSON, or workbench-first editing returned to the primary Studio area.
- Updated Studio structure and smoke coverage to lock the new supply-chain rail and the direct route-intent action from the first fold.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider -k "dash_app_exposes_structural_studio_controls" --basetemp tests/_tmp/pytest-basetemp-ux-wave10-structure-targeted-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_workspace_panel_unifies_focus_connectivity_and_runs_gate or studio_workspace_panel_promotes_direct_measurement_fix_in_primary_context or studio_workspace_panel_keeps_context_actions_discoverable_when_not_applicable or workspace_context_route_intent_button_updates_selected_edge_route_directly" --basetemp tests/_tmp/pytest-basetemp-ux-wave10-ui-targeted-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave10-structure-full
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave10-ui-full
```

Result:

- `1 passed, 17 deselected in 0.52s`
- `4 passed, 108 deselected in 0.54s`
- `18 passed in 29.94s`
- `112 passed in 332.01s (0:05:32)`

## Evidence

- Structured Studio stabilization snapshot: `docs/2026-04-09_phase_ux_refinement_wave10_ui_snapshot.json`
- This final wave did not retry browser capture. The change stayed within the Studio first fold and is documented with structured excerpts plus passing structural and smoke suites.

## Scope Guardrails

- No architecture reopening.
- No changes to Dash/Cytoscape stack or Julia-only official execution policy.
- No reopening of Runs or Decision logic beyond preserving the existing transitions.
- No changes to solver, ranking core, hydraulic logic, or `docs/05_data_contract.md`.
- No return of technical hubs, raw JSON, or workbench-first editing as the primary Studio surface.

## Honest Handoff

The final wave closes with a contained but real Studio gain. The operator now sees the business supply chain directly in the primary fold and can reclassify the route in focus without leaving for the advanced workbench. The residual risk is that the local supply-chain summary still depends on the currently focused node or route; a future UX phase would need real browser evidence and heavier canvas interaction work to go beyond this without reopening architecture.
