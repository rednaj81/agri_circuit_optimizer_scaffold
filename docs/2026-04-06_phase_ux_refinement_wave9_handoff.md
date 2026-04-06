# Phase UX Refinement Wave 9 - Language and State Convergence

## Objective

Open `ux_phase_5` in a controlled way by harmonizing labels, status vocabulary and empty-state guidance across Studio, Runs, Decisão and Auditoria, without reopening the interaction flows already stabilized in earlier waves.

## Delivered

- Standardized top guidance cards toward `Próxima ação` in the primary summary panels that still used `Ação principal`, which removes one of the last cross-surface wording divergences between Studio, Runs, Decisão and Auditoria.
- Harmonized operational status vocabulary in Runs so the queue now uses `Pronto`, `Em execução` and `Sem contexto` instead of older mixed labels such as `Sem pendências`, `Executando` and `Sem leitura`.
- Humanized the raw Audit status pill through `_humanize_audit_status`, so the Audit surface no longer exposes `idle`/`error` as the first user-facing status marker.
- Cleaned residual inconsistent decision language in `Candidato em foco`, including accented product wording for `Inviável agora`, `Rota crítica` and `Próxima ação`.
- Updated smoke coverage to lock the converged wording in Studio readiness, Runs executive reading, Decision candidate focus and Audit bundle guidance.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_readiness_panel_surfaces_runs_transition_with_real_readiness or primary_runs_panels_hide_raw_backend_keys_in_main_surface or candidate_summary_panel_surfaces_primary_blocker_and_next_action or audit_bundle_panel_preserves_technical_space_but_explains_next_step" --basetemp tests/_tmp/pytest-basetemp-ux-wave9-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave9-full
```

Result:

- `4 passed, 62 deselected in 0.66s`
- `66 passed in 462.67s (0:07:42)`

## Evidence

- Structured convergence snapshot: `docs/2026-04-06_phase_ux_refinement_wave9_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, queue backend, decision algorithm or Studio graph semantics.
- No new panels, no new primary flows and no return to raw technical surfaces.
- No rework of backend rules, ranking logic or data contract.

## Honest Handoff

This wave is intentionally narrower than the major flow changes before it. The value is not a new path; it is removal of the small language mismatches that made the product feel like stitched-together waves instead of one surface. After this convergence pass, the UI reads more uniformly when it says something is ready, blocked, in execution, unavailable or awaiting next action. That leaves wave 10 with a cleaner responsibility: stabilization and final polish, not semantic cleanup.
