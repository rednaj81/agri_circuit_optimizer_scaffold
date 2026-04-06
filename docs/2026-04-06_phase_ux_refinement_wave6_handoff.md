# Phase UX Refinement Wave 6 - Studio Focus-Driven Context

## Objective

Make the current canvas selection drive the main Studio context so the operator can understand the selected node or connection, see the most relevant connectivity implications, and act from that focus before opening the secondary editing workbench.

## Delivered

- Added a primary `Foco do canvas` panel to the Studio main rail, driven by the current node and connection selections already synchronized from Cytoscape.
- Reworked the connectivity panel so it prioritizes routes linked to the current focus when possible, instead of behaving only as a generic scenario summary.
- Moved the node and connection summaries into the secondary editing workbench so they support editing without competing with the main focus rail.
- Kept the canvas, connectivity panel, and focus panel in the first fold while preserving the business-only graph and hidden internal nodes.
- Preserved the secondary workbench and technical disclosure; the change is about hierarchy and prioritization, not backend behavior.
- Extended smoke coverage to protect the new focus-driven context and the selection-aware prioritization inside the connectivity panel.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_tab_surfaces_readiness_and_selection_context or studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas or studio_focus_panel_uses_canvas_selection_as_primary_context" --basetemp tests/_tmp/pytest-basetemp-ux-wave6-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave6-full
```

Result:

- `3 passed, 37 deselected in 0.61s`
- `40 passed in 403.39s`

## Evidence

- Structured Studio focus snapshot: `docs/2026-04-06_phase_ux_refinement_wave6_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, fail-closed behavior, or queue/runs contracts.
- No change to solver, ranking, official decision logic, or `technical_tie`.
- No reintroduction of technical entities, raw JSON, or logs as primary Studio UX.

## Honest Handoff

This wave improved the quality of Studio attention rather than adding another status block. The canvas selection now governs the main context rail, and the connectivity panel tries to talk first about what matters to the current focus. The editing workbench remains available, but it stopped competing with the canvas as the primary attention anchor.
