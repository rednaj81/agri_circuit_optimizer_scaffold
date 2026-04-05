# Phase 1 Wave 2 Handoff

## Objective
- Close the remaining gap in safe bundle authoring by preventing node or edge edits that break canonical scenario references, while preserving valid `candidate_links.csv` edits through the official `save -> reopen` flow.

## Implemented
- Hardened node authoring in the UI helper so `node_id` renames fail closed when `candidate_links.csv` or `route_requirements.csv` still reference the original node.
- Added minimal edge authoring on top of the existing `candidate_links.csv` payload only, with explicit validation for `link_id`, `from_node`, `to_node`, `archetype`, duplicate ids, unknown endpoints, and self-loop rejection.
- Kept valid edge edits persistent through the canonical bundle save/reopen path without changing manifest precedence or provenance signals.
- Added contract coverage for unknown endpoints in both `candidate_links.csv` and `route_requirements.csv`.

## Validation
- `.\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_scenario_contract_validation.py tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_ui_smoke.py -q`
- Result: `45 passed in 291.12s`

## Scope Guard
- No Julia runtime, queue/background, ranking, scoring, or orchestration behavior was changed.
- The edge editing added in this wave is constrained to the already persisted `candidate_links.csv` payload and does not open free-form topology authoring beyond the current bundle contract.

## Files Touched For This Wave
- `src/decision_platform/ui_dash/app.py`
- `tests/decision_platform/test_scenario_contract_validation.py`
- `tests/decision_platform/test_scenario_persistence.py`
- `tests/decision_platform/test_ui_smoke.py`
