# Phase UX Refinement Wave 8 - Decision Readability for Assisted Choice

## Objective

Open `ux_phase_4` by making the Decision surface readable in the first fold: winner, runner-up, technical tie and no-result states should be legible without pushing the operator into dense comparison blocks or raw technical evidence.

## Delivered

- Added a dedicated `_decision_primary_state` helper in `src/decision_platform/ui_dash/app.py` so the Decision surface now classifies four primary product states consistently: no usable decision, infeasible winner, technical tie and clear winner.
- Reframed `Passagem Runs -> Decisão` around `Winner oficial`, `Runner-up de referência` and `Estado da decisão`, which makes the assisted-choice story readable before the deeper comparison area.
- Updated `Winner oficial` to explain both why the leading candidate is currently on top and why it may still be blocked, keeping infeasibility explicit in the product-language summary instead of hiding it behind technical details.
- Tightened `Runner-up e contraste` so it now distinguishes between `no usable decision` and `winner exists but runner-up is missing`, instead of treating every missing contrast as the same generic fallback.
- Extended smoke coverage for the Decision surface to protect no-run, infeasible-winner and missing-runner-up states in addition to technical tie and standard winner-versus-runner-up reading.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_flow_panel or primary_decision_panels_hide_raw_metric_keys_in_main_surface or decision_summary_panel_surfaces_infeasible_winner_without_console_language or decision_contrast_panel_guides_when_runner_up_is_missing or primary_surfaces_explain_empty_states_without_debug_language" --basetemp tests/_tmp/pytest-basetemp-ux-wave8-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave8-full
```

Result:

- `7 passed, 57 deselected in 0.16s`
- `64 passed in 467.76s (0:07:47)`

## Evidence

- Structured Decision snapshot: `docs/2026-04-06_phase_ux_refinement_wave8_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, queue backend, run semantics or decision algorithm.
- No refactor of Studio, Runs, Audit or global shell.
- No promotion of raw JSON, logs or dense technical payloads to the first fold of Decision.

## Honest Handoff

This wave finally gives the Decision screen a clearer assisted-choice hierarchy. The main gain is not new backend data; it is a more honest reading of what the current result actually supports. The operator can now tell faster whether there is no usable decision yet, whether the winner is visible but blocked, whether the result is still a technical tie, or whether the winner has enough separation to proceed. The dense comparison and technical trace remain available, but they no longer need to carry the burden of basic orientation.
