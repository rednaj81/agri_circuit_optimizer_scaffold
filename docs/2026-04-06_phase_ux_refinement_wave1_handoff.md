# Phase UX Refinement Wave 1 - Navigation and Information Architecture Cleanup

## Objective

Open `ux_phase_1` by making the product shell clearer on first contact: Studio, Runs, Decisão and Auditoria should read as one guided journey, with explicit purpose, current state and next action before the operator needs to open technical detail.

## Delivered

- Added a new top-level `Jornada principal` panel in `src/decision_platform/ui_dash/app.py` to frame the four primary product spaces as one guided flow instead of a loose set of tabs.
- Wired the journey panel to live Studio readiness, run queue state and decision state so the shell now shows current status and the next recommended move for each primary area.
- Kept `Studio`, `Runs`, `Decisão` and `Auditoria` as the only visible top-level product spaces and preserved raw technical payloads inside progressive disclosure instead of promoting them into the main shell.
- Extended smoke coverage in `tests/decision_platform/test_ui_smoke.py` to protect the new journey panel structure, its callback refresh behavior and the top-level navigation links.
- Regenerated the structured UI snapshot for wave 1 with the new journey panel markers and validation evidence.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "surfaces_only_four_primary_product_spaces or product_space_banner_uses_consistent_product_language_for_each_space or product_journey_panel_summarizes_all_primary_spaces or product_space_banner_callback_tracks_active_primary_tab or product_journey_panel_callback_tracks_active_primary_tab_and_state or studio_discovery_callbacks_open_guide_and_audit_tab" --basetemp tests/_tmp/pytest-basetemp-ux-wave1-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1-full
```

Result:

- `6 passed, 60 deselected in 1.38s`
- `71 passed in 494.74s (0:08:14)`

## Evidence

- Structured shell snapshot: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, queue semantics or decision algorithm.
- No promotion of raw JSON, logs or technical internal entities to the primary shell.

## Honest Handoff

This wave materially improves the product shell, not the backend behavior. The operator now gets a single journey-oriented reading above the tabs, with explicit purpose and next action for each main space. The result is a clearer entry path from Studio to Runs to Decisão, while Auditoria stays available as secondary depth instead of competing for first-fold attention. The shell is still dense below the fold, but the top-level navigation no longer feels like a set of disconnected technical surfaces.
