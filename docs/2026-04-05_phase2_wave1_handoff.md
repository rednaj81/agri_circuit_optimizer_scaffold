# Phase 2 Wave 1 Handoff

## Objective

Open `phase_2` explicitly with the minimum structural studio slice: create, duplicate and delete nodes, create and delete edges, and preserve the canonical `save -> reopen` bundle flow without reopening `phase_1`.

## Delivered

- The structural studio entrypoints are available in the UI and in helper functions for create, duplicate and delete on nodes plus create and delete on candidate links.
- Structural edits continue to persist only through the canonical scenario bundle files already defined by the current contract, with `scenario_bundle.yaml` and `component_catalog.csv` preserved as the canonical persistence path.
- Node deletion remains fail-closed when `candidate_links.csv` or `route_requirements.csv` still reference the selected node.
- Storage coverage now includes a direct round-trip test for structural create/delete through `save_authored_scenario_bundle`, complementing the UI and acceptance coverage already present at `HEAD`.

## Validations

- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_studio_structure.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase2_exit_acceptance.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_scenario_persistence.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase1_exit_acceptance.py tests\decision_platform\test_phase1_exit_artifacts.py -q`

## Scope Guardrails

- No new persistence format was introduced.
- `docs/05_data_contract.md` was left unchanged.
- No queue/background runs, ranking expansion or decision UI expansion were touched.
- The official runtime remains fail-closed and Julia-only on the official path.

## Honest Handoff

Most of the `phase_2` structural implementation was already present in the checked-out `HEAD` before this session. This wave focused on validating that sealed state, adding missing storage-level regression coverage for canonical structural round-trips, and documenting the explicit `phase_2` opening and guardrails.
