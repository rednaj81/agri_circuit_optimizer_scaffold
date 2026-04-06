# Phase UX Refinement Wave 1 - Studio Direct Editing On The Main Surface

## Objective

Execute the approved Studio wave without reopening architecture: keep the business graph as the primary surface, move routine edits into the main workspace around the canvas, make supply relationships readable in business language, and keep the advanced workbench as secondary support.

## Delivered

- Preserved the current `decision_platform` shell and Dash/Cytoscape stack while keeping Studio, Runs, Decisão and Auditoria as the only primary product spaces.
- Moved the quick-edit path into the Studio workspace first fold in `src/decision_platform/ui_dash/app.py` through `studio-workspace-quick-edit-panel` and `studio-workspace-local-actions-panel`, so routine node and edge changes live beside the main canvas instead of inside the detailed focus area.
- Kept direct node label editing available through `studio-focus-node-label` and `studio-focus-node-apply-button`, now surfaced from the local canvas workspace rather than as the main payload of the focus panel.
- Kept direct edge adjustments on the primary Studio surface through `studio-focus-edge-length-m`, `studio-focus-edge-family-hint`, `studio-focus-edge-apply-button` and `studio-focus-edge-reverse-button`, alongside move, duplicate and delete shortcuts that reduce routine dependence on the advanced workbench.
- Reinforced first-fold supply-chain readability in the workspace with explicit business-flow language under "Quem supre quem na camada principal" and a local readiness readout near the quick-edit controls.
- Simplified `render_studio_focus_panel` so it now explains why the selection matters and points the operator back to the first-fold workspace controls instead of duplicating the full editing surface.
- Updated `tests/decision_platform/test_studio_structure.py` and `tests/decision_platform/test_ui_smoke.py` to lock the new workspace quick-edit panels, preserve the business-first reading of the Studio surface, and validate the direct-edit callbacks for node label update, edge length/family update and edge direction reversal.
- Refreshed the structured evidence artifact in `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json` to match the current workspace-first quick-edit flow and the latest validation results.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_studio_structure.py tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-dev-wave1-full
```

Result:

- `87 passed in 491.58s (0:08:11)`

## Evidence

- Structured Studio workspace snapshot: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No change to the Julia-only official execution path.
- No backend solver, queue semantics, ranking logic or hydraulic-model changes.
- No promotion of raw JSON, debug payloads or technical internals back to the primary Studio surface.

## Honest Handoff

The main Studio quick-edit implementation was already present in the local worktree when this session started. I treated that worktree state as authoritative, validated it against the approved wave intent, updated the UI tests that now describe the workspace-first direct-edit path, and refreshed the handoff plus structured evidence so they match the actual product surface. This wave now gives the Studio a real routine-editing path on the main business graph surface, but visual screenshot evidence is still missing and the worktree still carries unrelated agent/supervisor overlay edits outside this wave scope.
