# Phase UX Refinement Wave 1 - Navigation Shell and Canvas-First IA Refresh

## Objective

Execute the approved `ux_phase_1` wave against the checked-out codebase by making the primary `decision_platform` path read clearly as `Studio -> Runs -> Decisão -> Auditoria`, while keeping technical payloads secondary and preserving the business graph as the main Studio surface.

## Delivered

- Kept the primary navigation constrained to the four product spaces required by the UX bundle: `Studio`, `Runs`, `Decisão`, and `Auditoria`.
- Added a product-space banner that tracks the active tab and explains purpose, current objective, and next action in product language instead of leaving the shell implicit.
- Added a canvas-first Studio guidance panel so the first fold starts from the business graph focus and its readiness gate, not from raw technical context.
- Tightened the Studio focus and connectivity panels so each one explains what unlocks progress, what still blocks the run gate, and what to do next from the current selection.
- Preserved technical JSON and bundle payloads behind progressive disclosure and in `Auditoria`, without moving them back into the primary product path.
- Extended smoke coverage for the active-tab product banner, the new canvas guidance panel, and the stronger focus/connectivity guidance wording.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "surfaces_only_four_primary_product_spaces or product_space_banner_uses_consistent_product_language_for_each_space or product_space_banner_callback_tracks_active_primary_tab or studio_tab_surfaces_readiness_and_selection_context or studio_canvas_guidance_panel_keeps_canvas_as_primary_entry or studio_connectivity_panel_surfaces_routes_and_measurement_near_canvas or studio_focus_panel_uses_canvas_selection_as_primary_context or runs_tab_combines_queue_and_execution_summary or decision_tab_contains_advanced_sections_without_extra_primary_tabs" --basetemp tests/_tmp/pytest-basetemp-ux-wave1-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1-full-current
```

Result:

- `9 passed, 41 deselected in 1.14s`
- `50 passed in 482.60s (0:08:02)`

## Evidence

- Structured UI snapshot refreshed from the current checked-out layout: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash/Cytoscape.
- No change to Julia-only official execution, fail-closed behavior, solver logic, queue contract, or ranking behavior.
- No change to the data contract in `docs/05_data_contract.md`.
- No reintroduction of `html.Pre`, raw JSON, or audit payloads as the main reading surface of `Studio`, `Runs`, or `Decisão`.

## Honest Handoff

The repository state handed to this session was already inconsistent with the nominal wave numbering: the branch `HEAD` (`7c4f34453a126adb5b0217ebdf8133be93d2947d`) already contained later UX-refinement commit subjects, while `src/decision_platform/ui_dash/app.py` and `tests/decision_platform/test_ui_smoke.py` still had additional uncommitted UI worktree edits. This session treated that checked-out worktree as the source of truth, validated the real behavior now present, refreshed the wave-1 evidence for the approved navigation/IA scope, and sealed only the scoped UI/test/evidence delta instead of pretending the branch history matched a clean wave-1 baseline.
