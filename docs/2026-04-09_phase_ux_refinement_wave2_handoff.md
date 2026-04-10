# Phase UX Refinement Wave 2 - Runs First-Fold Simplification

## Objective

Continue `ux_phase_3` by reducing the cognitive load of Runs: make the first fold answer faster what is happening now, what the safe next action is, and why `failed`, `canceled`, waiting states, and Decision readiness are not the same thing.

## Delivered

- Simplified the first fold of `Runs` so the workspace now concentrates on `run em foco`, a stronger state headline, and a tinted `Próxima ação segura` block instead of spreading the primary read across multiple competing cards.
- Relegated terminal history from the first fold into `Histórico terminal secundário`, preserving access while stopping it from competing with the focus run when the operator already has a dominant action.
- Increased semantic contrast in the workspace between `failed`, `canceled`, `queued`, `preparing`, `running`, `exporting`, `completed`, and `reexecução` through state-specific headlines, CTA labels, and recovery copy.
- Tightened `run em foco` fallback reasoning so the panel no longer falls back to a generic “no strong run” explanation when the selected detail already provides a meaningful execution state.
- Kept `html.Pre`, raw JSON, logs, and paths out of the primary UX path; technical traces remain secondary through disclosure.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "runs_workspace_panel_distinguishes_scenario_gate_from_execution_state or runs_workspace_panel_prioritizes_queue_focus_and_primary_transition or runs_workspace_panel_distinguishes_failure_recovery_from_decision_ready or runs_workspace_panel_contrasts_failed_and_canceled_focus_states or runs_workspace_panel_uses_refresh_cta_for_intermediate_execution_states or run_jobs_overview_panel_explains_status_language_for_terminal_and_rerun_states or run_job_detail_panel_distinguishes_failed_canceled_and_rerun_guidance" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-targeted-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase3_queue_acceptance.py tests/decision_platform/test_phase3_runs_ui_smoke.py -q -p no:cacheprovider -k "runs_ui_surfaces_operational_queue_and_detail_language or runs_tab_reopens_persisted_operational_telemetry" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-phase3-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-full-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase3_queue_acceptance.py tests/decision_platform/test_phase3_runs_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-phase3-full
```

Result:

- `7 passed, 102 deselected in 0.62s`
- `2 passed, 12 deselected in 31.45s`
- `109 passed in 327.90s (0:05:27)`
- `14 passed in 58.98s`

## Evidence

- Structured Runs snapshot: `docs/2026-04-09_phase_ux_refinement_wave2_ui_snapshot.json`
- Browser capture attempt was made, but the local Playwright navigation call was cancelled by the tool session; the wave keeps a structured snapshot instead of claiming a screenshot that did not land.

## Scope Guardrails

- No architecture reopening.
- No stack replacement beyond the existing Dash/Cytoscape surface.
- No change to Julia-only official execution policy or fail-closed behavior.
- No change to the accepted Studio baseline except preservation of the gate into Runs.
- No change to hydraulic core logic or `docs/05_data_contract.md`.

## Honest Handoff

This wave improves real scanning speed in Runs rather than just changing copy. The main first-fold gain is that `run em foco` now dominates the surface while history is demoted and the safe next action is visually harder to miss. The remaining risk is that the workspace still depends on text-heavy cards more than a truly bespoke visual treatment; that is acceptable for `ux_phase_3`, but any next step should avoid slipping back into denser operational clutter.
