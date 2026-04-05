# Phase 3 Wave 3 - Runs UI Operations

## Objective

Close the local operator gap of the serial queue MVP by allowing the `Runs` tab to enqueue the current scenario, execute the next queued job, cancel queued jobs, and request reruns from terminal runs over the existing serial backend.

## Delivered

- the `Runs` tab can enqueue the current scenario directly into the persisted local `run_job` queue
- the same tab can trigger `run_next_queued_job(...)` and refresh the selected run detail from backend state
- queued jobs still cancel through the existing serial backend contract
- terminal runs still rerun through a new `run_id`, with the UI now operating the same backend path
- official mode remains Julia-only and still fails closed when the real Julia probe is disabled

## Validation

```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_queue_acceptance.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_artifacts.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -q -p no:cacheprovider -k "dash_app_builds_layout_and_callbacks_even_when_fail_closed or dash_app_exposes_authoring_save_reopen_controls"
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q -p no:cacheprovider
```

## Honest Limits

- the worker remains strictly serial; no parallel execution, queue distribution, or advanced orchestration was introduced
- this wave does not reopen the `Studio` baseline, canonical save/reopen flow, or Julia-only official semantics
- the `Runs` UI is still a minimal local operator surface, not a full queue console
