# Phase 2 Wave 4 - Structural Studio Handoff

## Objective

Close the minimal studio cut by making the canonical scenario structurally editable: create, duplicate, and delete nodes plus create and delete edges, all through the existing canonical bundle save/reopen flow.

## Implemented

- added structural authoring controls to the `Studio` for nodes: create, duplicate, and delete
- added structural authoring controls to the `Studio` for edges: create and delete
- kept all structural edits inside the existing `nodes.csv` and `candidate_links.csv` payloads; no new persistence format was introduced
- blocked node deletion when `candidate_links.csv` or `route_requirements.csv` still reference the selected node
- preserved the existing fail-closed guards for edge ids, endpoints, self-loop, and missing `archetype` rules

## Validation

```powershell
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_studio_structure.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase1_exit_acceptance.py tests\decision_platform\test_scenario_contract_validation.py tests\decision_platform\test_scenario_persistence.py tests\decision_platform\test_ui_smoke.py tests\decision_platform\test_studio_structure.py tests\decision_platform\test_run_pipeline_cli.py -q -p no:cacheprovider
$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q -p no:cacheprovider
```

## Scope Guard

- no Julia-only runtime semantics were changed
- no queue/background runs, orchestration, or new automation layers were introduced
- persistence, provenance, and canonical bundle structure remain the same as the frozen phase 1 baseline
