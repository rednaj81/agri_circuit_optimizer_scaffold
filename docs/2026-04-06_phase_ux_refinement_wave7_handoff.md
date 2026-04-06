# Phase UX Refinement Wave 7 - Studio Local and Global Rule Clarity

## Objective

Make the Studio explain critical structural rules near the current canvas focus without hiding the blockers that still prevent overall scenario readiness.

## Delivered

- Extended the Studio connectivity panel so it now separates `Seleção atual` from `Cenário inteiro`, making local violations and global readiness blockers visible in the same primary surface.
- Added product-language rule messages tied to the current focus for the critical constraints `no routes into W`, `no routes out of S`, and `direct measurement required for dosing routes`.
- Kept the canvas and the context rail as the main Studio experience while preserving the editing workbench and technical fields as secondary support.
- Preserved the business-only graph and hidden internal nodes; no technical hubs, raw JSON, or debugging surfaces returned to the first fold.
- Updated smoke coverage so the Studio surface now guards local/global distinction and the humanized rule messages around the current focus.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas or studio_focus_panel_uses_canvas_selection_as_primary_context or studio_tab_surfaces_readiness_and_selection_context" --basetemp tests/_tmp/pytest-basetemp-ux-wave7-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave7-full
```

Result:

- `3 passed, 37 deselected in 0.66s`
- `40 passed in 409.80s`

## Evidence

- Structured Studio local/global rules snapshot: `docs/2026-04-06_phase_ux_refinement_wave7_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, fail-closed behavior, queue/runs contracts, or backend ranking logic.
- No change to solver, candidate selection, or decision semantics.
- No reintroduction of technical hubs, raw JSON, logs, or form-heavy surfaces as the primary Studio UX.

## Honest Handoff

This wave improved Studio clarity by making the focus-aware rules more explicit without sacrificing the global picture. The operator can now see what is wrong with the selected connection or route and, at the same time, what still blocks the scenario as a whole from moving to Runs. The gain is in product-language guidance and hierarchy, not in any backend rule change.
