# Phase 1 Wave 3 Handoff

## Objective
- Make canonical scenario save deterministic and fail-closed so invalid authored payloads never publish a partial bundle, while persisted storage metadata always aligns with the canonical manifest and component catalog.

## Implemented
- Switched canonical bundle save to a staging-and-publish flow: write to a sibling staging directory, validate by reopening the staged bundle, and only then replace the target output directory.
- Normalized `scenario_settings.storage` during authored save:
  - if missing, the saved bundle repopulates `bundle_manifest: scenario_bundle.yaml` and `component_catalog: component_catalog.csv`
  - if present with divergent values, save fails closed before publishing the canonical bundle
- Preserved canonical component catalog precedence through `component_catalog.csv`, including save/reopen and run flows.
- Added failure-closed coverage for fresh output dirs and for rewrites over an existing valid output directory.

## Validation
- `.\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_scenario_settings_contract.py tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_phase1_exit_acceptance.py tests/decision_platform/test_ui_smoke.py -q`
- Result: `50 passed in 311.48s`

## Scope Guard
- No new studio capability, queue/background runtime, ranking, scoring, or Julia-engine behavior was added.
- The UI save/reopen path was exercised by tests, but the core fix stayed in canonical persistence/storage handling.

## Files Touched For This Wave
- `src/decision_platform/data_io/storage.py`
- `tests/decision_platform/test_scenario_settings_contract.py`
- `tests/decision_platform/test_scenario_persistence.py`
- `tests/decision_platform/test_phase1_exit_acceptance.py`
- `tests/decision_platform/test_ui_smoke.py`
