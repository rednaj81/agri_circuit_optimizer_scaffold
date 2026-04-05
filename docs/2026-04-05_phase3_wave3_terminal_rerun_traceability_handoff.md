# Phase 3 Wave 3 Handoff

## Objective

Harden the persisted serial queue contract so explicit rerun works for every terminal `run_job` state and the Runs inspection view exposes the persisted bundle reference used for lineage and reopen-style auditing.

## Delivered

- `rerun_run_job` now accepts any terminal run state from the canonical set: `completed`, `failed`, and `canceled`
- rerun lineage remains persisted in both `job.json` and `source_bundle_reference.json`, including reruns issued from previously canceled jobs
- run inspection now exposes `source_bundle_reference_path` and the parsed `source_bundle_reference` payload alongside status, events, logs, artifacts, and telemetry
- the Runs UI summary/detail helpers reopen this persisted reference data without ad hoc reconstruction
- the worker remains strictly serial and the official Julia-only path remains fail-closed

## Acceptance

- `tests/decision_platform/test_phase3_queue_acceptance.py`
- `tests/decision_platform/test_phase3_runs_ui_smoke.py`

## Honest Limits

- no parallel worker or orchestration capability was introduced
- no changes were made to the sealed `phase_1` or `phase_2` baselines
- this wave strengthens rerun traceability and inspection only; it does not change the execution engine or artifact export surface
