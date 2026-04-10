# Phase UX Refinement Wave 5 - Decision State Coherence

## Objective

Correct the mismatch between blocked decision states and secondary Decision panels so the whole page follows the same semantic model already established in the first fold.

## Delivered

- Added shared Decision-state helpers in `src/decision_platform/ui_dash/app.py` to classify page mode (`winner_clear`, `technical_tie`, `winner_infeasible`, `no_usable_result`) and reuse that logic in export messaging and CTA state.
- Aligned the secondary `Escolha final e export` guidance in the Decision workspace with the actual decision state, so blocked states no longer reuse positive export language.
- Updated `render_decision_contrast_panel`, `render_decision_signal_panel`, and `render_decision_justification_panel` so `technical_tie` stays in assisted mode and `winner_infeasible` / no-result states stay explicitly blocked across support panels.
- Updated the export CTA callback so `winner_infeasible` and no-result states disable export with honest labels, while `technical_tie` now exports as assisted choice instead of as a closed winner.
- Expanded the phase-4 acceptance suite and smoke coverage to assert cross-panel coherence and export-CTA behavior in blocked and assisted states.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "decision_export_cta_tracks_manual_choice_without_overwriting_official_reference or decision_summary_panel_surfaces_infeasible_winner_without_console_language or primary_decision_panels_hide_raw_metric_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave5-targeted-ui-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave5-phase4-targeted-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave5-full-ui
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_phase4_decision_acceptance.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave5-phase4-full
```

Result:

- `3 passed, 108 deselected in 0.52s`
- `6 passed in 0.27s`
- `111 passed in 330.09s (0:05:30)`
- `6 passed in 0.04s`

## Evidence

- Structured state-coherence snapshot: `docs/2026-04-09_phase_ux_refinement_wave5_ui_snapshot.json`
- This wave did not retry browser capture because the previous browser path was already blocked at environment level and the present change was logic coherence across panels, not a new visual shell change. The handoff keeps evidence structured and explicit.

## Scope Guardrails

- No architecture reopening.
- No changes to Dash/Cytoscape stack or Julia-only official execution policy.
- No reopening of Studio or Runs scope beyond preserving the existing transition into Decision.
- No changes to solver, ranking engine, hydraulic core, or `docs/05_data_contract.md`.
- No reintroduction of raw JSON, logs, or payload traces as primary Decision UI.

## Honest Handoff

This wave is a coherence fix, not a wording sweep. The visible gain is that blocked and assisted decision states now control the whole Decision page instead of only the hero. `winner_infeasible` no longer leaks export-ready copy in support panels or CTA labels, `technical_tie` stays explicitly in assisted mode across justification, signals, contrast and export, and no-result states block export honestly. `winner_clear` stays positively exportable, which preserves separation between the real ready state and all blocked states.
