# Phase UX Refinement Wave 2 - Studio First-Fold Simplification

## Objective

Advance `ux_phase_2` by reducing first-fold density in the Studio, keeping more common node and edge actions on the primary surface, and tightening the route-first editing hierarchy without reopening architecture.

## Delivered

- The Studio workspace now exposes a compact `Ajustes locais do canvas` action rail with direct left/right move, duplicate, reverse-edge and delete-edge actions, so frequent edits no longer compete with larger form blocks on the first fold.
- Fine-grained node and edge editing stayed in the Studio but moved under `Ajustes finos do foco`, which keeps the first fold lighter while preserving direct label, length and family edits outside the advanced workbench.
- The route editor now keeps intent, next-step guidance and main route actions on the first fold, while route particularities for both the draft and the selected route moved into disclosure blocks (`Particularidades da rota em preparo` and `Particularidades da rota em foco`).
- The route-first CTA logic from wave 1 remains intact and now sits in a clearer visual hierarchy: supply chain, route draft state and readiness still lead the first reading, but with fewer competing expanded blocks.
- UI smoke coverage was updated to assert the new disclosure panels, the visible move-right action and the simplified local-edit structure.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-current
```

Result:

- `96 passed in 435.90s (0:07:15)`

## Evidence

- Browser-ready first-fold export: `output/playwright/wave2-studio-first-fold.html`
- Capture attempt log: `output/playwright/wave2-studio-first-fold-meta.json`

## Scope Guardrails

- No architecture reopening.
- No stack change beyond the current Dash/Cytoscape Studio.
- No reintroduction of technical helper entities into the primary Studio surface.
- No functional redesign of Runs, Decision or Audit.

## Honest Handoff

This wave makes the Studio first fold easier to parse and act on: the operator now sees a shorter action rail for common edits, while detailed route and focus fields stay one disclosure away instead of occupying the same visual priority as readiness and supply flow. I did not fully satisfy the ideal evidence path of a live-browser screenshot against a running local Dash server: `playwright` was unavailable in Python, Selenium could not resolve a local driver in the sandbox, and the MCP browser navigation session was cancelled before capture. To avoid fabricating proof, I recorded a browser-ready HTML export plus the failed-capture log and kept the limitation explicit.
