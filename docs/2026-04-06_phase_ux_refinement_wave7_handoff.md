# Phase UX Refinement Wave 7 - Runs Queue and Execution Clarity

## Objective

Open `ux_phase_3` by making Runs easier to read as an execution surface: clarify queue state, active execution, recent history, and when the operator can honestly move from Runs to Decision.

## Delivered

- Reworked `Resumo da fila` so the first read now separates queue-now versus recent history, instead of leaving queue state and historical state mixed in a short generic summary.
- Strengthened `Passagem Studio -> Runs` to explicitly distinguish `Estado do cenário`, `Estado das runs`, and `Próximo passo`, making the boundary between scenario readiness and run lifecycle clearer.
- Isolated `Run em foco` as the main detailed read while moving operational feedback from the queue actions next to `Operações da fila`, reducing competition between selected-run detail and transient queue messages.
- Expanded `Run em foco` to cover intermediate statuses like `preparing` and `exporting` with product-language next actions rather than leaving those states closer to raw backend semantics.
- Made the Decision handoff from Runs more honest by disabling the primary execution CTA when the current execution still has no usable selected candidate and relabeling it as unavailable in that state.
- Kept logs, JSON, and technical traces in disclosure paths only; the wave stayed on first-fold readability and did not touch backend queue semantics.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "runs_tab_combines_queue_and_execution_summary or runs_flow_panel or run_jobs_overview_panel or run_job_detail_panel_covers_preparing_and_exporting_states or execution_summary_panel_only_opens_decision_with_usable_result or primary_runs_panels_hide_raw_backend_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave7-targeted2
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave7-full2
```

Result:

- `6 passed, 52 deselected in 0.63s`
- `58 passed in 448.23s (0:07:28)`

## Evidence

- Structured Runs snapshot: `docs/2026-04-06_phase_ux_refinement_wave7_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to queue backend semantics, Julia-only execution policy, or optimization logic.
- No change to `docs/05_data_contract.md`.
- No Studio refactor beyond preserving existing links.

## Honest Handoff

This wave moves visible UX value out of the diminishing-return Studio loop and into Runs. The main gain is not backend capability; it is first-fold legibility of queue, execution, and readiness-to-decision. Visual evidence remains structured instead of screenshot-based because local capture is still blocked by policy.
