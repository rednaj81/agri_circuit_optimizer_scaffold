# Phase UX Refinement Wave 2 - Studio Business Graph Surface

## Objective

Close the main remaining Studio gap by turning the primary surface into a business-graph editor, hiding candidate hubs and technical metadata from the default path while preserving the canonical bundle workflow and existing structural editing.

## Delivered

- Filtered the main Studio canvas so the primary Cytoscape surface shows only business-facing nodes and connections.
- Removed internal candidate hubs such as `HS` and `HD` from the main canvas and automatically hid connections that depend on those internal nodes.
- Reworked the Studio selection summaries to emphasize readable labels, business roles, flow context, and visible-surface status instead of raw IDs and technical types.
- Moved `node_id`, `node_type`, `allow_inbound`, `allow_outbound`, `link_id`, `archetype`, and `bidirectional` out of the main editing flow into progressive disclosure blocks.
- Kept the existing node and edge editing callbacks, persistence flow, bundle save/reopen, and canonical data contract intact.
- Added smoke coverage to protect the filtered Studio canvas, the new business-editor hierarchy, and the disclosure-only placement of technical fields.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio and not slow" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-fast
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2
```

Result:

- `8 passed, 23 deselected in 1.48s`
- `31 passed in 366.94s`

## Evidence

- Structured Studio snapshot: `docs/2026-04-05_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No changes to the Julia-only official execution path or fail-closed semantics.
- No changes to `docs/05_data_contract.md`.
- No changes to backend pipeline, API, or hydraulic solver behavior.

## Honest Handoff

This wave stayed tightly scoped to the Studio surface. The main change was not backend logic; it was redefining what the primary Studio experience renders and which fields dominate the editing flow. The structural editors, callbacks, save/reopen behavior, and canonical bundle persistence remain the same, but the default operator path is now visibly business-first and the technical fields are intentionally secondary.
