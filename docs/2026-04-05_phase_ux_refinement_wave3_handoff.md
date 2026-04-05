# Phase UX Refinement Wave 3 - Decision Hierarchy Cleanup

## Objective

Make the top of `Decisão` answer the three first operator questions immediately: who is the official winner, who is the runner-up, and whether the situation is a `technical_tie`, while keeping dense technical breakdowns and raw state behind secondary layers.

## Delivered

- Reworked the primary `Decisão` fold so the top row now separates `Escolha oficial` from `Runner-up e contraste`, instead of mixing the winner with catalog state too early.
- Added a dedicated `Sinais para decisão humana` panel to surface viability, penalties, critical routes, fallback pressure, and adjacent risk signals in product-facing language.
- Kept `technical_tie` explicit in the primary decision contrast instead of leaving it implicit in deeper comparison areas.
- Preserved `comparison`, `candidate circuit`, `breakdown`, and raw JSON, but pushed them behind disclosure or lower-priority zones so they no longer compete with the first decision read.
- Kept ranking, winner selection, runner-up computation, and `technical_tie` logic untouched; this wave only changed the UI hierarchy and wording of the existing decision evidence.
- Extended smoke coverage to protect the new primary decision panels and to ensure the raw backend keys stay outside the main decision surface.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_tab_contains_advanced_sections_without_extra_primary_tabs or primary_decision_panels_hide_raw_metric_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave3-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-full
```

Result:

- `2 passed, 36 deselected in 0.57s`
- `38 passed in 420.80s`

## Evidence

- Structured decision snapshot: `docs/2026-04-05_phase_ux_refinement_wave3_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to ranking, winner selection, runner-up computation, or `technical_tie` semantics.
- No change to the Julia-only official execution path, fail-closed behavior, or queue/runs contracts.
- No reintroduction of `html.Pre`, raw JSON, or dense technical grids as primary decision UI.

## Honest Handoff

This wave stayed strictly in presentation. The real gain was reducing the cognitive jump from queue execution to human choice: the primary `Decisão` surface now leads with winner, runner-up contrast, and decision signals, while catalog depth, circuit depth, and JSON remain available but secondary. No functional ranking behavior was altered.
