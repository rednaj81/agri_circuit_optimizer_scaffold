# Phase UX Refinement Wave 1 - Navigation and Information Architecture Cleanup

## Objective

Execute `ux_phase_1` without reopening architecture: keep `decision_platform` framed as one product journey, make Studio, Runs, Decisão and Auditoria read as the four primary spaces, and push technical context out of the first fold.

## Delivered

- Preserved the four-space product shell in `src/decision_platform/ui_dash/app.py` and kept the main navigation constrained to Studio, Runs, Decisão and Auditoria.
- Consolidated the first fold of Studio, Runs, Decisão and Auditoria into dedicated workspace panels so each space now opens with objective, current state and next action before deeper technical detail.
- Kept queue operations, decision comparison, bundle editors, tables and raw technical JSON available, but moved them behind progressive disclosure (`html.Details`) instead of leaving them as the primary reading surface.
- Added primary workspace transitions across the journey, including the Runs workspace CTA into Decisão and the explicit return paths from Decisão and Auditoria.
- Updated `tests/decision_platform/test_ui_smoke.py` and `tests/decision_platform/test_studio_structure.py` so the UI contract now locks the new workspace hierarchy, disclosure boundaries and CTA wiring.
- Refreshed the structured evidence artifact in `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json` to match the current worktree state.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests\_tmp\pytest-basetemp-ux-wave1-targeted -k "runs_workspace_panel_prioritizes_queue_focus_and_primary_transition or decision_workspace_panel_makes_winner_runner_up_and_tie_legible or audit_workspace_panel_relegates_auditoria_to_advanced_path or decision_tab_contains_advanced_sections_without_extra_primary_tabs or runs_tab_combines_queue_and_execution_summary or audit_tab_holds_bundle_editors_and_technical_surfaces or dash_app_exposes_structural_studio_controls or product_space_banner_stays_aligned_with_navigation_resolution or studio_discovery_callbacks_open_guide_and_audit_tab"
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests\_tmp\pytest-basetemp-ux-wave1-current
```

Result:

- `9 passed, 69 deselected in 1.41s`
- `78 passed in 428.22s (0:07:08)`

## Evidence

- Structured shell and first-fold snapshot: `docs/2026-04-06_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, fail-closed behavior, queue semantics or backend decision logic.
- No reintroduction of `html.Pre`, raw JSON or raw logs as the primary reading surface of the touched spaces.

## Honest Handoff

The local worktree already contained the main UX wave delta in `app.py` when this session started. I treated that state as the source of truth, reconciled the remaining smoke expectation to the renamed Runs detailed panel, reran the relevant UI suites, and refreshed the handoff plus structured evidence so they now describe the real first-fold behavior across Studio, Runs, Decisão and Auditoria. The wave closes with meaningful IA progress, but evidence remains a structured snapshot rather than a rendered screenshot.
