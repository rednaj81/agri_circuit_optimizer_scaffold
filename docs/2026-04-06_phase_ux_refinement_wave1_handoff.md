# Phase UX Refinement Wave 1 - Studio First-Fold Direct Editing

## Objective

Execute the approved UX refinement wave without reopening architecture: preserve the four-space product shell, keep the business graph as the primary Studio surface, and reduce dependence on the advanced workbench for routine first-fold adjustments.

## Delivered

- Kept the current `decision_platform` shell centered on Studio, Runs, Decisão and Auditoria while preserving the existing workspace hierarchy already present in `src/decision_platform/ui_dash/app.py`.
- Expanded the Studio focus panel with direct first-fold editing for the selected business entity: the operator can now update the visible node label from the main canvas context through `studio-focus-node-label` and `studio-focus-node-apply-button`.
- Added direct edge adjustments in the same focus area through `studio-focus-edge-length-m`, `studio-focus-edge-family-hint`, `studio-focus-edge-apply-button` and `studio-focus-edge-reverse-button`, keeping common business-flow corrections local to the canvas.
- Wired new Dash callbacks so quick edits update node and edge state in place, return honest status messages, and preserve fail-closed validation through the existing node and edge edit helpers.
- Added `reverse_edge_studio_selection` as an explicit reusable helper so business flow direction can be flipped without opening the full workbench path.
- Updated `tests/decision_platform/test_studio_structure.py` and `tests/decision_platform/test_ui_smoke.py` to lock the presence of the new first-fold controls and validate the direct-edit callback behavior for label updates, edge adjustments and edge reversal.
- Refreshed the structured evidence artifact in `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json` to capture the new first-fold Studio affordances and validation results.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_studio_structure.py tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-dev-wave1
```

Result:

- `86 passed in 600.45s (0:10:00)`

## Evidence

- Structured Studio quick-edit snapshot: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No change to Dash/Cytoscape stack or to the Julia-only official execution path.
- No backend solver, queue semantics, ranking logic or hydraulic-model changes.
- No promotion of raw JSON, debug payloads or technical internals back to the primary Studio surface.

## Honest Handoff

The main code delta for this wave was already present in the local worktree when the session started. I treated that worktree state as authoritative, validated that the new Studio first-fold editing path behaves correctly, updated the affected UI suites, and refreshed the handoff plus structured evidence so they now describe the real state of the product surface. The wave meaningfully reduces routine workbench dependence for common label and connection edits, but it does not attempt broader shell or navigation changes beyond preserving the existing four-space product framing.
