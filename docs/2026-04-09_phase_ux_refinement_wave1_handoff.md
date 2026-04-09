# Phase UX Refinement Wave 1 - Studio Connectivity-First First Fold

## Objective

Advance `ux_phase_2` inside the current Dash/Cytoscape Studio by making the first fold more explicitly route-first, keeping the business graph as the primary surface and reducing the need to open the advanced workbench for routine route-definition steps.

## Delivered

- The canvas guidance surface now keeps the supply-chain reading on the first fold with an explicit `Cadeia visível neste foco` block that shows who supplies the current focus, who the focus supplies, the route draft state and the most legible business-flow excerpts without exposing technical internals.
- Node focus now adapts to the active route draft: when the composer already has an origin, selecting another node promotes `Usar como destino` as the primary direct action instead of forcing the operator back through the editor flow.
- The Studio workspace now exposes a first-fold supply strip with `Quem supre este foco`, `Quem este foco supre` and `Trecho mais legível`, so the operator can read the business chain before opening disclosure-heavy panels.
- The existing local canvas editing path remains intact and technical fields stay behind progressive disclosure; the change stayed inside Studio and did not reopen Runs, Decision, Audit or the product architecture.
- UI smoke coverage was extended to assert the new supply-chain panels, the draft-aware destination action and the no-duplicate-layout guarantee.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1-current
```

Result:

- `96 passed in 544.22s (0:09:04)`

## Evidence

- Structured Studio snapshot: `docs/2026-04-09_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement and no changes to the Julia-only official execution path.
- No business-graph exposure of hidden technical hubs, centrais or derived helper entities.
- No Runs, Decision or Audit redesign beyond incidental coupling already present in shared callbacks.

## Honest Handoff

This wave is materially stronger than a copy-only pass: the primary canvas CTA now follows the actual route-draft state, and the supply-chain reading moved into the first fold instead of remaining mostly buried in disclosure blocks. The Studio is still card-dense, and some less common edits still rely on the advanced workbench, but routine route completion and business-flow reading are now more direct and more legible without reopening architecture.
