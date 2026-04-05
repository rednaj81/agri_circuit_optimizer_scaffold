# Phase 3 Wave 9 Handoff

## Objective

Persist a ready-to-consume queue summary per `run_id` so reopened queue views can render lineage and evidence summary without rescanning run artifacts to rebuild the listing.

## Delivered

- each `job.json` now persists `queue_summary` with `lineage` and `evidence_summary`
- queue list rendering reuses this persisted `queue_summary` as the primary source for lineage and quick evidence inspection
- reopened snapshots keep `selected_run_summary` aligned with the persisted queue summary and the detailed run inspection

## Active Verification

- `tests/decision_platform/test_phase3_queue_acceptance.py`
- `tests/decision_platform/test_phase3_runs_ui_smoke.py`

## Scope Guard

- worker remains strictly serial
- no governance rewrite, ranking scope, or decision UI expansion was introduced
- `phase_1` and `phase_2` remain sealed historical baselines only
