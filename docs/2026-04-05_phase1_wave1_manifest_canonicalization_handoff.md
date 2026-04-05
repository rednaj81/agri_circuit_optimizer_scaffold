# Phase 1 Wave 1 Handoff

## Scope
- keep `scenario_bundle.yaml` as the only canonical manifest for persisted decision-platform scenarios
- keep `component_catalog.csv` as the canonical component catalog when a manifest exists
- fail closed when a manifest tries to remap canonical tables/documents to aliases or alternate paths

## Implemented
- hardened `load_scenario_bundle` manifest resolution to reject non-canonical `tables.*` and `documents.*` entries before file loading
- added regression coverage for manifest attempts to point `tables.components` to `components.csv`
- added regression coverage for manifest attempts to point `documents.scenario_settings` to `./scenario_settings.yaml`
- updated the data contract to state that manifest entries must match canonical relative paths exactly

## Validation
- `.venv\\Scripts\\python.exe -m pytest tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_component_catalog_contract.py tests/decision_platform/test_scenario_settings_contract.py tests/decision_platform/test_scenario_contract_validation.py -q`

## Limitations
- this wave does not change the legacy no-manifest compatibility path
- this wave does not touch phase 3 queue/background run behavior or the Julia bridge
