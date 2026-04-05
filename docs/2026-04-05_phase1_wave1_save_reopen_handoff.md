# Phase 1 Wave 1 Handoff

## Objective
- Normalize the canonical scenario bundle flow so `save -> reopen` preserves topology, mandatory-route artifacts, edge obligations, and the component catalog with fail-closed manifest handling.

## Implemented
- Enforced node-table contract validation during canonical bundle loading, including duplicate `node_id`, blank `node_type`, and blank `label` rejection.
- Kept manifest-first loading fail-closed for unsupported `bundle_version` and missing files referenced by `scenario_bundle.yaml`.
- Preserved canonical save/reopen coverage for `nodes`, `candidate_links`, `edge_component_rules`, `route_requirements`, `layout_constraints`, and `component_catalog.csv`.
- Made UI/save-reopen provenance more explicit by surfacing requested paths alongside the canonical bundle root and an explicit `requested_dir_matches_bundle_root` signal in the bundle I/O summary.

## Validation
- `.\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_scenario_persistence.py tests/decision_platform/test_phase1_exit_acceptance.py tests/decision_platform/test_ui_smoke.py -q`
- Result: `30 passed in 260.99s`

## Risks And Limitations
- `src/decision_platform/ui_dash/app.py` and `tests/decision_platform/test_ui_smoke.py` already contain a node-studio slice in the working tree. It was not removed in this wave to avoid destructively reverting pre-existing edits, but it remains adjacent to the phase-1 persistence work and should be reviewed by the Auditor as possible scope pressure.
- No Julia-path behavior was changed beyond preserving the existing fail-closed official gate.

## Files Touched For This Wave
- `src/decision_platform/data_io/loader.py`
- `src/decision_platform/ui_dash/app.py`
- `tests/decision_platform/test_scenario_persistence.py`
- `tests/decision_platform/test_phase1_exit_acceptance.py`
- `tests/decision_platform/test_ui_smoke.py`
