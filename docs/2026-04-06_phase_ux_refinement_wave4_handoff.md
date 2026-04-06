# Phase UX Refinement Wave 4 - Studio Connectivity-First Context

## Objective

Open `ux_phase_2` with an operational Studio improvement: make the main editing flow start from the canvas and from the current selection, while surfacing readiness blockers and the honesty of the transition to Runs without sending the operator into technical disclosure.

## Delivered

- Reworked the Studio contextual stack so the status banner now lives inside `Foco do canvas`, reducing one loose panel in the right rail and keeping edit feedback attached to the current selection context.
- Expanded `Foco do canvas` to include a dedicated `Passagem para Runs` guidance card and a `Readiness deste foco` section, linking selection, connectivity, mandatory routes, dosing, and run readiness in the same primary surface.
- Made the readiness transition more explicit by changing the main CTA text according to the actual state: `Abrir Runs`, `Abrir Runs quando o cenário estiver pronto`, or `Abrir Runs com bloqueios`.
- Preserved the business-graph-first Studio surface: hubs and derived nodes remain hidden, while the extra guidance stays in product language instead of raw payloads or technical objects.
- Updated UI smoke coverage to lock the embedded status banner, the new readiness framing inside the focus panel, and the more honest run-transition labels.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_readiness_panel or studio_focus_panel or studio_tab_surfaces_readiness_and_selection_context" --basetemp tests/_tmp/pytest-basetemp-ux-wave4-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4-full
```

Result:

- `6 passed, 45 deselected in 0.60s`
- `51 passed in 413.47s (0:06:53)`

## Evidence

- Structured Studio snapshot: `docs/2026-04-06_phase_ux_refinement_wave4_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, queue semantics, or backend optimization logic.
- No change to `docs/05_data_contract.md`.
- No exposure of technical hubs or derived nodes in the primary Studio surface.

## Honest Handoff

This wave delivers real Studio workflow gain instead of more shell polish: the operator now reads selection, edit feedback, readiness, and the handoff to Runs in one contextual stack. The main remaining limitation is visual capture; this wave uses a structured Studio snapshot because screenshot capture had already been blocked by the local policy.
