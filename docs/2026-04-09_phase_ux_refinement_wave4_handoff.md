# Phase UX Refinement Wave 4 - Persistent Selected Edge Flow

## Objective

Consolidate the selected-edge Studio flow so it is visible, stable and demonstrable end-to-end: a relevant route edge starts in focus, keeps a perceptible highlight on the primary canvas surface and exposes the local edge editor in a reproducible captured state.

## Delivered

- The primary Studio now starts with a non-null selected edge in the business graph whenever a visible route projection exists, instead of falling back to `selected_link_id: null`.
- The selected edge flow now supports route projections directly (`route:R...`) as a first-class focus state, which keeps the visible business route in focus even when no visible candidate link exists on the primary surface.
- The canvas guidance gained a persistent `Trecho fixado no Studio` banner, making the selected route edge explicit in the first fold before the operator opens any deeper panel.
- The Cytoscape stylesheet now applies a much stronger visual focus to the selected edge with thicker line, outline and label emphasis, so the selected relation is easier to read in human review.
- The detailed Studio context now auto-opens when an edge is selected, ensuring the local direct-route panel is already visible in the captured live state instead of requiring an extra unreproducible interaction.
- UI smoke coverage now checks that the initial edge focus is non-null, that the detailed Studio context opens with the selected edge flow, and that the direct local edge route editor continues to work without exposing technical internals.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4-current
```

Result:

- `98 passed in 459.21s (0:07:39)`

## Evidence

- Live selected-edge layout capture: `output/playwright/wave4-studio-selected-edge-layout.json`
- Live selected-edge report: `output/playwright/wave4-studio-selected-edge-report.html`
- Capture metadata: `output/playwright/wave4-studio-selected-edge-capture.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement beyond the current Dash/Cytoscape Studio.
- No reintroduction of technical helper entities, hubs or derived nodes on the primary Studio surface.
- No broad redesign of Runs, Decision or Audit.

## Honest Handoff

This wave hardens the demonstrability of the direct edge flow rather than adding another isolated edit control. The important change is not only that local route editing exists, but that a visible business route now starts and stays in focus clearly enough for a live capture to prove the interaction path. The evidence remains structured/browser-driven instead of a literal PNG screenshot because the sandboxed browser stack is still unreliable for final image capture, but the capture now explicitly records `selected_edge_id: route:R001` with the detailed context open and the local panel visible.
