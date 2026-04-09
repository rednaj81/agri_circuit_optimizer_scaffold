# Phase UX Refinement Wave 1 - Runs First Fold Compression

## Objective

Advance `ux_phase_3` by turning `Runs` into a faster operational read: first fold must answer what is queued, what is running, what failed and what the operator can do now, while keeping scenario, run/job and result as separate readings and pushing raw technical traces behind disclosure.

## Delivered

- Reworked the first fold of `Runs` in `src/decision_platform/ui_dash/app.py` around four direct signals: `O que está na fila`, `O que está rodando`, `O que falhou` and `O que pode fazer agora`.
- Added a short separation strip for `Cenário`, `Run/job` and `Resultado`, so the operator does not need to infer whether a message belongs to readiness, queue execution or a reusable outcome.
- Reduced repeated operational narration in the queue overview and replaced it with compact signal cards plus a smaller metrics row.
- Kept logs, paths, payloads and full technical inspection behind disclosure in the detailed and audit surfaces; the raw JSON/debug surfaces remain secondary.
- Trimmed repetitive copy inside the run detail summary so the panel keeps progress, action, recovery and result visible without repeating the same state under multiple headings.
- Updated UI assertions in `tests/decision_platform/test_phase3_queue_acceptance.py` and `tests/decision_platform/test_ui_smoke.py` to cover the new first-fold language and the retained disclosure structure.

## Validation

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m py_compile src\decision_platform\ui_dash\app.py
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_queue_acceptance.py -q
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_runs_ui_smoke.py -q
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -k "runs_tab_combines_queue_and_execution_summary or runs_workspace_panel_surfaces_queue_history_and_decision_gate or runs_workspace_panel_uses_refresh_cta_for_intermediate_execution_states or run_job_detail_panel_prioritizes_events_and_artifacts_over_logs or run_jobs_overview_panel_summarizes_current_queue_and_history or run_jobs_overview_panel_surfaces_preparing_and_recovery_states" -q
```

Result:

- `py_compile` passed.
- `tests/decision_platform/test_phase3_queue_acceptance.py`: `13 passed`.
- `tests/decision_platform/test_phase3_runs_ui_smoke.py`: `1 passed`.
- Targeted `test_ui_smoke.py` runs coverage for the updated Runs panels: `4 passed`.

## Evidence

- Structured Runs snapshot: `docs/2026-04-09_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement and no change to the Julia-only official execution path.
- No broad Studio redesign; only shared language and transition safety remained touched.
- No reopening of Decision beyond preserving the honest gate from Runs.

## Honest Handoff

This wave materially reduces the text density of `Runs`, but it is still a Dash card surface, not a dedicated mission-control redesign. The first fold is now faster to scan and clearer about queue versus execution versus result, yet the detailed panel still carries a fair amount of operational language and the full `test_ui_smoke.py` file was not rerun end-to-end because it exceeded the local timeout budget; targeted Runs assertions and the phase-3 suites did pass.
