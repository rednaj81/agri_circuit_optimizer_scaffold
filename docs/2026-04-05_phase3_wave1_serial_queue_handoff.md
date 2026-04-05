# Phase 3 Wave 1 - Serial Queue Handoff

## Objective

Open `phase_3` with the smallest queue/background cut: isolated local `run_job` entries executed by an explicit serial worker, with status transitions, logs, and artifacts bound to the canonical source bundle.

## Implemented

- added a minimal `run_job` backend contract in `src/decision_platform/api/run_pipeline.py`
- each run now persists `job.json`, `events.jsonl`, `run.log`, `source_bundle_reference.json` and `artifacts/`
- added serial worker helpers to create, list, summarize, execute, cancel, and process the next queued job
- preserved official Julia-only semantics when the job requests official execution
- exposed a minimal read-only `Runs` tab in the local app for queue inspection

## Validation

```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_queue_acceptance.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase2_exit_acceptance.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_run_pipeline_cli.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q -p no:cacheprovider
```

## Scope Guard

- no simultaneity was introduced; worker execution remains serial and explicit
- the Studio baseline from `phase_2` was not reopened
- no Julia bridge semantics or `phase_0` validation scripts were changed
