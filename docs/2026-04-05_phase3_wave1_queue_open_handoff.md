# Phase 3 Wave 1 - Queue Open Handoff

## Objective

Realign the administrative source of truth so `phase_3` is the only active functional phase while preserving the already delivered serial queue slice exactly as implemented in code.

## Active Gate

- current functional acceptance: `tests/decision_platform/test_phase3_queue_acceptance.py`
- current phase plan source: `docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml`
- current runtime guidance: `docs/codex_dual_agent_runtime/supervisor_guidance.json`
- current manifest block: `phase_3_current_validation` in `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`

## Delivered Baseline

- isolated local `run_job` entries executed by an explicit serial worker
- queued-job cancellation without execution artifacts
- explicit re-run of `completed` or `failed` runs through a new `run_id`
- individual run inspection with status, events, log, and artifacts
- queue inspection can be reopened from persisted local state, including isolated UI sessions bound to a specific queue root
- official mode remains Julia-only when requested; diagnostic mode remains explicit and non-official

## Closed Phases

- `phase_1` remains sealed and cannot receive additional functional waves
- `phase_2` remains closed with `tests/decision_platform/test_phase2_exit_acceptance.py` as its frozen exit gate

## Scope Guard

- the worker remains strictly serial
- no parallel orchestration or new queue capability is opened by this handoff
- the `Studio` baseline from `phase_2` remains frozen
- canonical bundle persistence and the official Julia-only runtime path remain unchanged

## Audit Note

- `tests/decision_platform/test_phase3_queue_acceptance.py` now covers reopen-style inspection after execution, rerun, and cancel by rebuilding the queue snapshot and `Runs` UI from the persisted local queue root
