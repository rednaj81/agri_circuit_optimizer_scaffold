# Phase 3 Wave 2 - Run Telemetry Handoff

## Objective

Complete the minimum operational telemetry and human inspection surface for the serial local queue without reopening parallel orchestration, structural Studio authoring, or the closed phase_1/phase_2 baselines.

## Implemented

- normalized persisted `run_job` telemetry in `src/decision_platform/api/run_pipeline.py` so completed, failed, canceled, and rerun entries keep:
  - `engine_requested`
  - `engine_used`
  - `engine_mode`
  - `julia_available`
  - `watermodels_available`
  - `real_julia_probe_disabled`
  - `execution_mode`
  - `official_gate_valid`
  - `started_at`
  - `finished_at`
  - `duration_s`
  - `policy_mode`
  - `policy_message`
  - `failure_reason`
  - `failure_stacktrace_excerpt`
- added backward-compatible normalization on `job.json` reads so persisted queue state can be reopened without recomputing execution
- expanded queue summary with `queue_state`, active/queued/terminal run ids, next queued run id, latest run id, and latest update timestamp
- exposed a richer `Runs` detail payload in `src/decision_platform/ui_dash/app.py`, including a `telemetry` block and an `inspection` block with resolved paths
- kept the worker explicitly serial and preserved Julia-only fail-closed behavior for official runs

## Validation

```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_queue_acceptance.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase2_exit_acceptance.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_runs_ui_smoke.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -q -p no:cacheprovider
```

## Scope Guard

- no parallel worker, scheduler, or distributed lock was introduced
- no structural Studio capability was expanded beyond the frozen phase_2 baseline
- no canonical bundle contract or `docs/05_data_contract.md` change was made
- official mode still fails closed when Julia probing is disabled or invalid for the official gate

## Notes

- initial queued or canceled jobs no longer trigger an eager real Julia/WaterModels probe; full engine availability is persisted from execution results when the run actually executes
- the new `tests/decision_platform/test_phase3_runs_ui_smoke.py` isolates the phase_3 run inspection smoke coverage from the broader UI smoke baseline
