# Phase UX Refinement Wave 3 - Product-First First Fold for Runs, Decision and Audit

## Objective

Close `ux_phase_1` by making `Runs`, `Decisão` and `Auditoria` read more like product spaces and less like internal tooling on the first fold, while keeping the shell aligned with the real flow state and pushing extra operational or technical context behind progressive disclosure.

## Delivered

- Refined the first-fold workspace panels for `Runs`, `Decisão` and `Auditoria` in `src/decision_platform/ui_dash/app.py` so each one now makes `O que esta área resolve`, `Estado atual` and `Próxima ação` explicit instead of relying on operator inference.
- Updated `render_runs_workspace_panel(...)` to frame Runs as an operational product space first, with objective and state guidance before queue detail.
- Updated `render_decision_workspace_panel(...)` so the first fold now states the purpose of the decision space and the current decision state before the operator reads winner and runner-up specifics.
- Updated `render_audit_workspace_panel(...)` so the first fold now states what Audit resolves, its current role in the journey and when it should stay secondary to Studio, Runs or Decisão.
- Reduced technical density in secondary Runs and Audit panels without removing access to evidence:
  - `render_run_jobs_overview_panel(...)` now keeps queue history, status distribution and worker-mode context inside `run-jobs-overview-history-details`.
  - `render_execution_summary_panel(...)` now keeps bundle path, profile and operational-error context inside `execution-summary-context-details`.
  - `render_bundle_io_panel(...)` now keeps canonical root and manifest addresses inside `bundle-io-address-details`.
- Updated `tests/decision_platform/test_ui_smoke.py` to cover the new first-fold objective/state wording and to assert that the newly technical blocks sit inside `html.Details`.
- Refreshed the structured evidence artifact in `docs/2026-04-06_phase_ux_refinement_wave3_ui_snapshot.json`.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "runs_workspace_panel_prioritizes_queue_focus_and_primary_transition or primary_runs_panels_hide_raw_backend_keys_in_main_surface or run_jobs_overview_panel_clarifies_queue_now_vs_recent_history or decision_workspace_panel_makes_winner_runner_up_and_tie_legible or audit_bundle_panel_preserves_technical_space_but_explains_next_step or audit_workspace_panel_relegates_auditoria_to_advanced_path" --basetemp tests/_tmp/pytest-basetemp-dev-wave3-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-dev-wave3-full
```

Result:

- `6 passed, 72 deselected in 0.73s`
- `87 passed in 592.06s (0:09:52)`

## Evidence

- Structured first-fold and disclosure snapshot: `docs/2026-04-06_phase_ux_refinement_wave3_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No changes to Julia-only execution, fail-closed policy, solver logic or hydraulic behavior.
- No reintroduction of raw JSON, traces or backend-oriented payloads into the primary first fold of Runs, Decisão or Auditoria.

## Honest Handoff

This wave closes `ux_phase_1` at the per-space first fold rather than at the shell only. The product now speaks more clearly in the opening panels of Runs, Decisão and Auditoria, and the extra operational evidence that still matters is available through nested disclosure instead of taking over the main reading path. The dense technical editors, tables and JSON remain available in the deeper Audit and Decision surfaces by design; this wave only reduced what competes with the primary orientation layer.
