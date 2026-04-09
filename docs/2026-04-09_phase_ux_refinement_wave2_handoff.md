# Phase UX Refinement Wave 2 - Runs Mission Control Compression

## Objective

Advance `ux_phase_3` by turning `Runs` from a compressed first fold into a leaner mission-control style read: recent history must be primary again, the live queue and the focused run must stay distinct, and the dominant CTA must be obvious without multiplying equivalent cards.

## Delivered

- Reworked the main `Runs` workspace in `src/decision_platform/ui_dash/app.py` into a two-lane mission grid: `Histórico recente` now leads the first fold, while a compact live rail holds `Fila agora`, `Run em foco`, the dominant action and the explicit `Cenário` / `Run/job` / `Resultado` separation.
- Added reusable helpers for recent-run history and state pills, so terminal runs, re-runs and usable results surface with shorter visual markers instead of long explanatory text.
- Restored recent history as a primary autonomous read: the operator can now tell from the first fold whether the last relevant run finished with usable output, failed, was canceled or came from a rerun chain, without opening disclosure.
- Condensed the detailed queue overview into one live panel plus one history panel, reducing parallel cards that repeated the same queue state with different labels.
- Tightened the run-detail summary so progress and recovery are clearer and less card-heavy while keeping logs, paths and raw evidence behind technical disclosure.
- Updated the `Runs` assertions in `tests/decision_platform/test_phase3_queue_acceptance.py` and `tests/decision_platform/test_ui_smoke.py` to reflect the new first-fold hierarchy.

## Validation

```powershell
$env:PYTHONPATH='.'
.\.venv\Scripts\python.exe -m py_compile src\decision_platform\ui_dash\app.py
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_queue_acceptance.py -q
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_runs_ui_smoke.py -q
.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -k "runs or run_job_detail_panel_prioritizes_events_and_artifacts_over_logs or run_jobs_overview_panel_clarifies_queue_now_vs_recent_history or run_jobs_overview_panel_surfaces_preparing_and_recovery_states" -q
```

Result:

- `py_compile` passed.
- `tests/decision_platform/test_phase3_queue_acceptance.py`: `13 passed`.
- `tests/decision_platform/test_phase3_runs_ui_smoke.py`: `1 passed`.
- Targeted `test_ui_smoke.py` coverage for the updated Runs panels: `17 passed, 89 deselected`.

## Evidence

- Structured Runs snapshot: `docs/2026-04-09_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement and no backend contract change in the serial queue model.
- No broad Studio redesign and no new Decision wave; only the honest gate from Runs stayed integrated.
- Raw logs, paths and JSON remain secondary surfaces.

## Honest Handoff

This wave is a stronger operational read than wave 1: history is primary again, the live queue no longer competes with multiple equivalent cards and the focused run reads more like a control lane than another wall of summaries. The UI is still constrained by the existing Dash card system, so this is not a full custom mission-control shell, and I again did not rerun the whole `test_ui_smoke.py` file end-to-end because the suite is too expensive for the local timeout budget; the Runs-focused assertions and phase-3 suites did pass.
