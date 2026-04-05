# Phase 3 Wave 2 Handoff

## Objective

Advance the serial queue MVP to the minimum human-operable slice: queued-job cancellation, explicit re-run from a previous run, and individual run inspection.

## Delivered

- queued jobs can now be canceled explicitly with `status=canceled`, an event entry, and no execution artifacts
- completed or failed runs can now be re-enqueued explicitly, always through a new `run_id`
- re-run metadata is persisted in both `job.json` and `source_bundle_reference.json`
- the UI `Runs` tab now exposes a selected run with detail, plus minimal `Cancelar` and `Reexecutar` actions
- the worker remains strictly serial and the official path remains Julia-only when requested

## Acceptance

- `tests/decision_platform/test_phase3_queue_acceptance.py`
- `tests/decision_platform/test_phase2_exit_acceptance.py`
- `tests/decision_platform/test_ui_smoke.py -k "authoring_save_reopen_controls or node_studio or edge_studio or dash_app_builds_layout"`
- `tests/decision_platform -m fast -q -p no:cacheprovider`

## Honest Limits

- no real parallelism or orchestration was introduced
- this wave does not reopen the `Studio` baseline or the canonical save/reopen bundle flow
- run creation and worker execution remain local and simple; the UI addition is inspection-first, not a full operator console
