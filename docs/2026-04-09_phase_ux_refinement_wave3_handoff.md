# Phase UX Refinement Wave 3 - Direct Route Editing From Edge Context

## Objective

Advance `ux_phase_2` with a real Studio interaction gain by letting the operator resolve a frequent edge-focused task locally, instead of relying on the advanced workbench or a separate heavier edit path.

## Delivered

- The connectivity panel now exposes `Particularidades diretas deste trecho` whenever a visible connection is selected, turning the edge context into an operational editor for the linked business route.
- From that local edge context, the operator can now update route intent, minimum flow, minimum dose, measurement requirement and notes directly on the selected route, without leaving the current connection review.
- When the selected connection still has no route, the same local panel now offers `Criar rota a partir deste trecho`, sending the connection directly into the route composer from the connectivity context.
- The direct measurement action `Exigir medição direta` closes one of the most common preventable readiness blockers from the local panel instead of pushing the operator into the heavier route editing path.
- The Studio remains business-graph-first: no technical helpers were surfaced, and the supply-flow reading plus route-first framing stayed explicit on the primary surface.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-current
```

Result:

- `97 passed in 341.53s (0:05:41)`

## Evidence

- Live app structured capture: `output/playwright/wave3-studio-live-layout.json`
- Live app index capture: `output/playwright/wave3-studio-live-index.html`
- Capture metadata: `output/playwright/wave3-studio-live-capture.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement beyond the current Dash/Cytoscape Studio.
- No exposure of technical internal hubs, centrais or derived entities on the primary Studio surface.
- No broad Runs, Decision or Audit redesign.

## Honest Handoff

This wave changes behaviour, not only structure: selecting a connection now opens a local operational route editor capable of fixing measurement and route particularities directly from the edge context, which is a more meaningful Studio interaction gain than another card/disclosure pass. The evidence is live and tied to the app in execution through a local Dash server capture of `/?tab=studio` and `/_dash-layout`. I still did not obtain a literal browser screenshot because the sandboxed browser toolchain remained blocked, so the proof is a live structured capture rather than a PNG.
