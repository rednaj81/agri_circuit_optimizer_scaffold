# Phase UX Refinement Wave 5 - Studio Connectivity-First Workbench

## Objective

Open the transition into `ux_phase_2` by making `Studio` work primarily as a business-graph and connectivity surface: the canvas should stay central, the current selection should read next to the graph, and editing forms should become secondary rather than competing with the first operator read.

## Delivered

- Reorganized the Studio main fold so the business graph and a right-hand context rail now lead the experience together.
- Added a dedicated `Conectividade do grafo` panel next to the canvas, surfacing blockers, warnings, mandatory routes, direct measurement requirements, and immediate next steps near the editing surface.
- Moved the business editors into a secondary `Ações de edição do grafo` workbench so the operator can read the graph and connectivity state before dropping into field edits.
- Kept technical fields and audit data inside progressive disclosure, preserving auditability without turning the Studio back into a technical console.
- Preserved the business-only canvas, hidden internal hubs, Julia-only official path, and all existing structural editing callbacks.
- Extended smoke coverage to protect the new connectivity panel and the editor workbench separation from the primary Studio surface.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_tab_surfaces_readiness_and_selection_context or studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas" --basetemp tests/_tmp/pytest-basetemp-ux-wave5-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave5-full
```

Result:

- `2 passed, 37 deselected in 0.35s`
- `39 passed in 404.46s`

## Evidence

- Structured Studio snapshot: `docs/2026-04-05_phase_ux_refinement_wave5_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to the Julia-only official path, fail-closed runtime, or queue/runs behavior.
- No change to solver, ranking, official-candidate logic, or `technical_tie`.
- No reintroduction of raw JSON, logs, or internal nodes as primary Studio UX.

## Honest Handoff

This wave changed where the operator starts in `Studio`, not how the backend behaves. The graph and connectivity state now dominate the first read, while editing fields remain available in a secondary workbench. That makes the Studio feel more connectivity-first and less like a scattered form without reopening architecture or exposing technical internals.
