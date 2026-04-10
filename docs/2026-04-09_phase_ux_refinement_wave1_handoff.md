# Phase UX Refinement Wave 1 - Runs Queue and Execution UX

## Objective

Advance `ux_phase_3` in the new authorized cycle by making Runs read like a product surface: clearer queue-now versus focus-run versus recent terminal history, clearer product-language statuses, and a more honest gate from Runs to Decision.

## Delivered

- Added a first-fold `Estados da operação` layer in Runs so `queued`, `preparing`, `running`, `exporting`, `completed`, `failed`, `canceled`, and `reexecução` are translated into product language with the dominant operator gesture.
- Strengthened the workspace CTA logic around the focus run so the primary action now changes according to the selected run state: wait, execute, rerun with correction, confirm cancellation, or open Decision when the result is truly usable.
- Refined `Run em foco` to distinguish `failed` from `canceled`, keep rerun lineage explicit on the main surface, and explain `Passagem Runs -> Decisão` without forcing raw logs, paths, or payloads into the primary read.
- Removed artifact-directory and scenario-path noise from the main run detail surface and kept those addresses inside secondary technical disclosure only.
- Preserved the Studio gate separation: the workspace still makes it explicit when the limit is in the scenario and when the operator should stay inside Runs to resolve execution context.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "runs_workspace_panel_prioritizes_queue_focus_and_primary_transition or run_job_detail_panel_prioritizes_events_and_artifacts_over_logs or run_jobs_overview_panel_clarifies_queue_now_vs_recent_history or run_jobs_overview_panel_surfaces_preparing_and_recovery_states or run_jobs_overview_panel_explains_status_language_for_terminal_and_rerun_states or run_job_detail_panel_distinguishes_failed_canceled_and_rerun_guidance or run_job_detail_panel_covers_preparing_and_exporting_states" --basetemp tests/_tmp/pytest-basetemp-ux-wave1-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase3_queue_acceptance.py tests/decision_platform/test_phase3_runs_ui_smoke.py -q -p no:cacheprovider -k "runs_ui_surfaces_operational_queue_and_detail_language or runs_tab_reopens_persisted_operational_telemetry" --basetemp tests/_tmp/pytest-basetemp-ux-wave1-phase3
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1-full-ui-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase3_queue_acceptance.py tests/decision_platform/test_phase3_runs_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1-phase3-full
```

Result:

- `7 passed, 101 deselected in 0.58s`
- `2 passed, 12 deselected in 31.30s`
- `108 passed in 332.71s (0:05:32)`
- `14 passed in 59.49s`

## Evidence

- Structured Runs snapshot: `docs/2026-04-09_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement beyond the existing Dash/Cytoscape surface.
- No change to Julia-only official execution policy or fail-closed behavior.
- No Studio redesign outside the already accepted baseline.
- No change to hydraulic core logic or `docs/05_data_contract.md`.

## Honest Handoff

This wave produces real UX movement in Runs rather than more shell polish. The main gain is semantic clarity around focus-run state, recovery, rerun lineage, and when Decision is honestly unlocked. The surface is still component-dense, and the next wave should push further on winner versus runner-up and technical tie without letting Runs regress into raw operational detail.
