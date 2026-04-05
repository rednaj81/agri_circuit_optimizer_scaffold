# Phase UX Refinement Wave 4 - Studio Projection Coverage and Technical Discovery

## Objective

Close `ux_phase_1` by making the Studio explain the coverage and limits of its business projection, and by making the technical trail discoverable without reintroducing engineering clutter into the primary surface.

## Delivered

- Added an explicit projection-coverage panel to the Studio primary surface with complete/partial/degraded states.
- Surfaced clear product-language guidance for each projection state so the user understands when the business view is complete, when metadata is partial, and when the primary layer is intentionally reduced to business entities only.
- Added a discoverable technical-trail guide directly in the Studio and introduced CTAs to open the technical explanation and jump to the `Auditoria` tab.
- Kept the primary surface business-first in all states: internal nodes, hubs, and raw structural identifiers remain hidden by default even when route metadata is poor or absent.
- Expanded UI/smoke coverage to protect the projection-state logic, the technical-discovery controls, and the continued disclosure-only placement of technical fields.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio and not slow" --basetemp tests/_tmp/pytest-basetemp-ux-wave4-fast
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4
```

Result:

- `10 passed, 23 deselected in 1.38s`
- `33 passed in 312.22s`

## Evidence

- Structured Studio coverage snapshot: `docs/2026-04-05_phase_ux_refinement_wave4_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No changes to `docs/05_data_contract.md`.
- No changes to the canonical bundle files or runtime semantics.
- No changes to backend pipeline, Julia-only execution, or hydraulic solver logic.

## Honest Handoff

This wave finished the Navigation and IA cleanup phase from the Studio side. The business projection is now not only cleaner but also self-explanatory: the user can see when the primary view is trustworthy, when it is partial, and where to go for deeper technical inspection. The fallback remains intentionally business-first; it does not regress to a raw engineering canvas when route metadata is missing.
