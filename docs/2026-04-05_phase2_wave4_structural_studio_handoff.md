# Phase 2 Structural Studio Validation Handoff

## Objective

Close the validation gap on the real Studio path by proving that structural node and edge editing works through the Dash callbacks, with canonical `save -> reopen` behavior and preserved provenance.

## Delivered

- Added callback-level UI coverage in `tests/decision_platform/test_ui_smoke.py` for:
  - structural create, select, edit, duplicate and delete on nodes
  - structural create, select, edit and delete on edges
  - fail-closed behavior for deleting a referenced node
  - fail-closed behavior for invalid edge references
  - fail-closed behavior for legacy layouts without `scenario_bundle.yaml` on the UI save/reopen callback
- Added script-based evidence in `scripts/capture_decision_platform_ui_validation.py` that exercises the real Studio callback map and emits deterministic JSON evidence plus a README.
- Added acceptance coverage in `tests/decision_platform/test_phase2_exit_acceptance.py` that executes the validation script and verifies canonical manifest, canonical component catalog and preserved provenance.

## Validation Commands

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase2_exit_acceptance.py -q
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase1_exit_acceptance.py tests/decision_platform/test_phase1_exit_artifacts.py -q
```

## Scope Guardrails

- No persistence format changed.
- `docs/05_data_contract.md` remains untouched.
- `src/decision_platform/data_io/storage.py` remains untouched.
- No queue/background run, ranking expansion or decision UI expansion work was added.
- The official Julia-only gate remains fail-closed; diagnostic execution is explicit in validation only.

## Honest Handoff

The structural Studio implementation itself was already present in the checked-out codebase. This wave hardened the real UI validation layer around that implementation, using the actual Dash callbacks and canonical save/reopen path instead of only helper-level tests.
