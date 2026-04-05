# Phase UX Refinement Wave 3 - Studio Business Projection

## Objective

Finish the Studio cleanup by replacing the partial node filter with an explicit business projection: `zone=internal` and `zone=hub` nodes leave the primary surface, while the main canvas stays readable through projected business routes.

## Delivered

- Replaced the partial Studio filter with an explicit metadata-based rule that hides all nodes marked as internal or hub in the primary canvas.
- Removed `HS`, `HD`, `J1`-`J4`, and `U1`-`U3` from the primary Studio surface and kept only business-facing nodes such as `W`, `P1`-`P4`, `M`, `I`, `S`, and `IR`.
- Changed the primary Studio edges from raw physical links to route-based business projections built from `route_requirements`, so the canvas remains connected and understandable after collapsing internal structure.
- Kept the technical structural editors and canonical bundle persistence intact, but moved `from_node` and `to_node` alongside the other contractual fields into progressive disclosure.
- Updated smoke/UI coverage to protect the full hidden-node set and the existence of projected business routes in the Studio primary surface.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio and not slow" --basetemp tests/_tmp/pytest-basetemp-ux-wave3-fast
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3
```

Result:

- `8 passed, 23 deselected in 1.03s`
- `31 passed in 379.12s`

## Evidence

- Structured Studio projection snapshot: `docs/2026-04-05_phase_ux_refinement_wave3_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No changes to `docs/05_data_contract.md`.
- No changes to backend pipeline, hydraulic logic, or the Julia-only official runtime.
- No changes to the scenario bundle files under `data/decision_platform/maquete_v2/`.

## Honest Handoff

This wave closed the remaining Studio projection gap. The primary surface is now intentionally a business view, not a thinly cleaned technical graph: internal junctions and hubs no longer appear as primary editing objects, and the canvas stays understandable because the route projection comes from canonical route metadata rather than ad hoc cosmetic hiding. The full technical structure remains available in the advanced Studio fields and in Auditoria.
