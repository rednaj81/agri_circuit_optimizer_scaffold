# Phase 1 Wave 4 Handoff

## Objective

Seal the current `phase_1` exit gate in a reproducible and auditable state around versionable scenario bundles and persisted component catalog data, without pulling structural studio work into the phase gate.

## Scope Closed In This Wave

- Consolidated the minimum `phase_1` gate around the canonical bundle, `component_catalog.csv`, normalized `scenario_settings.storage`, and official `save -> reopen -> run` provenance.
- Added an automated guard so the `phase_1` gate suite does not depend on `create_node_studio_node`, `duplicate_node_studio_selection`, `delete_node_studio_selection`, `create_edge_studio_link`, or `delete_edge_studio_selection`.
- Updated the runtime validation manifest and README so the current gate evidence is explicit and does not overclaim structural studio scope.

## Reproducible Evidence

- Validation command:

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_scenario_settings_contract.py tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_phase1_exit_acceptance.py -q
```

- Gate files:
  - `tests/decision_platform/test_phase1_exit_acceptance.py`
  - `tests/decision_platform/test_scenario_persistence.py`
  - `tests/decision_platform/test_scenario_settings_contract.py`
- Manifest evidence:
  - `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json` -> `phase_1_exit_validation`

## Exit Signals Covered

- canonical bundle manifest saved as `scenario_bundle.yaml`
- persisted component catalog saved and reopened as `component_catalog.csv`
- `scenario_settings.storage` normalized to the canonical filenames or rejected fail-closed when divergent
- official provenance preserved across `save -> reopen -> run`
- no `phase_1` gate dependency on structural studio helpers

## Out Of Scope Preserved

- structural studio creation/duplication/deletion flows
- queue/background runs
- ranking/scoring expansion
- Julia runtime changes beyond the existing fail-closed behavior

## Honest Handoff

`phase_1` exit evidence is now explicit and reproducible in code, tests, and manifest form, but the repository still contains unrelated dirty/untracked files outside this wave and they remain intentionally excluded from the commit. Structural studio work is still outside the current `phase_1` gate and must continue to be audited separately.
