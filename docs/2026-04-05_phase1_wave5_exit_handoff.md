# Phase 1 Exit Handoff

## Objective

Close `phase_1` formally without adding any new functional scope, leaving a single operational reading for the sealed exit criteria and a clear redirect to `phase_2` for structural studio work.

Wave 7 is a corrective regression fix only: it restores reproducibility of the closure artifacts and does not reopen any functional work inside `phase_1`.

## Point Of Truth

- Validation manifest: `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
  - active block for this phase: `phase_1_exit_validation`
  - historical block for Julia-only runtime evidence: `profiles`
- Runtime guidance: `docs/codex_dual_agent_runtime/supervisor_guidance.json`
- Human handoff: `docs/2026-04-05_phase1_wave5_exit_handoff.md`

## Exit Criteria Already Proven

- versionable scenario bundles with canonical `scenario_bundle.yaml`
- persisted component catalog in canonical `component_catalog.csv`
- canonical `scenario_settings.storage` mapping for `bundle_manifest` and `component_catalog`
- official provenance preserved across `save -> reopen -> run`

## Reproducible Evidence

- Tests:
  - `tests/decision_platform/test_scenario_settings_contract.py`
  - `tests/decision_platform/test_scenario_persistence.py`
  - `tests/decision_platform/test_phase1_exit_acceptance.py`
- Validation command:

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_scenario_settings_contract.py tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_phase1_exit_acceptance.py -q --basetemp tests/_tmp/pytest-basetemp-wave4-exit
```

## Explicit Out Of Scope

- structural creation, duplication, or deletion of nodes and edges
- `tests/decision_platform/test_studio_structure.py`
- queue and background runs
- ranking, scoring, and decision UI expansion

## Next Functional Continuity

`phase_1` is closed at this point. Any new functional progress should open `phase_2` explicitly and keep structural studio work out of the sealed `phase_1` gate.

No additional functional wave should be scheduled inside `phase_1` after this regression correction.

## Honest Handoff

This closeout is documentation-only and operational-only. No changes were made to loader behavior, canonical save behavior, UI behavior, the official runtime path, or the already sealed functional gate tests of `phase_1`.
