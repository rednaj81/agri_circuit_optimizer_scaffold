# Phase UX Refinement Wave 3 - Runs Focus-Run Dominance

## Objective

Advance `ux_phase_3` by making `Run em foco` the dominant operational unit in `Runs`, with queue state, terminal history and result readiness supporting that reading instead of competing with it through parallel cards.

## Delivered

- Reworked the main `Runs` surface in `src/decision_platform/ui_dash/app.py` so the first fold now leads with a dominant `Run em foco` panel, not with parallel queue/history cards of similar weight.
- Centralized progress, result readiness, recovery and the dominant action inside the focused-run panel, so the operator can understand the current run without hopping across multiple equivalent blocks.
- Reframed the right rail of `Runs` into two narrower support lanes: `Fila agora` and `Histórico terminal`, which keep queue and recent terminal states explicit without reclaiming primary attention from the focused run.
- Preserved explicit separation between `Cenário`, `Fila agora` and `Resultado` inside a smaller `Leituras separadas` strip embedded under the focused run, instead of another standalone surface.
- Kept raw technical inspection behind disclosure and left `html.Pre`/JSON/debug outputs secondary; the primary read still avoids console-style payloads.
- Updated `tests/decision_platform/test_phase3_queue_acceptance.py` and `tests/decision_platform/test_ui_smoke.py` to assert the new hierarchy and the shift from `Histórico recente` to `Histórico terminal`.

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
- Targeted `test_ui_smoke.py` coverage for the updated Runs surfaces: `17 passed, 89 deselected`.

## Evidence

- Structured Runs snapshot: `docs/2026-04-09_phase_ux_refinement_wave3_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No stack replacement and no queue backend contract change.
- No broad Studio or Decision redesign; the wave stayed concentrated in `Runs`.
- Technical logs, paths and payloads remain secondary.

## Honest Handoff

This wave finally makes `Run em foco` the dominant read in `Runs`: queue state and terminal history still exist, but they now support the focused run instead of competing with it. The main limitation is evidence strength: I attempted to produce a fresh visual capture from a live local Dash process, but the detached local server did not remain available long enough to make that reliable in this environment, so the wave closes with an updated structured snapshot rather than a new screenshot.
