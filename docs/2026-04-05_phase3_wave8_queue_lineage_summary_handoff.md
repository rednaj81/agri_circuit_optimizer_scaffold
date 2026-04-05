# Phase 3 Wave 8 Handoff

## Objective

Promote persisted rerun lineage and run evidence summaries from the individual run detail into the reopened serial queue view for quick inspection before drill-down.

## Delivered

- queue summary entries now expose a `lineage` block with rerun origin metadata per `run_id`
- queue summary entries now expose an `evidence_summary` block derived from the same persisted files used by the detailed inspection
- reopened queue snapshots now keep `selected_run_summary` aligned with `selected_run_detail`
- the `Runs` UI smoke now proves reopen over a persisted rerun, including queue-level lineage and evidence summary

## Active Verification

- `tests/decision_platform/test_phase3_queue_acceptance.py`
- `tests/decision_platform/test_phase3_runs_ui_smoke.py`

## Scope Guard

- worker remains strictly serial
- no governance rewrite, parallelism, ranking, or decision UI scope was introduced
- `phase_1` and `phase_2` remain sealed historical baselines only
