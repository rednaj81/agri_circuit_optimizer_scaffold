# Phase UX Refinement Wave 2 - Guided Primary States and Product Language

## Objective

Close the remaining information-hierarchy gaps in `decision_platform` by making the first fold of `Studio`, `Runs`, `Decisão`, and `Auditoria` read in product language, with explicit purpose, state, and next action before any technical disclosure.

## Delivered

- Strengthened `Studio` readiness with explicit "Objetivo desta área" and "Ação principal" guidance cards, plus stage-oriented copy (`Montar a base do cenário`, `Conectar o grafo principal`, `Remover bloqueios`, `Liberar a fila`) before the user opens `Runs`.
- Clarified the `Studio` projection panel so the boundary between business-layer reading and technical audit becomes explicit on the first fold.
- Humanized primary blocker and warning copy in `Studio` so the first fold no longer exposes terse strings such as `L900 entra em W` or `Nos sem conexao no grafo visivel: ...` as the main UX language.
- Refined `Runs` queue and transition panels so queue state, readiness, run status, and next step now read in product language (`Sem pendências`, `Na fila`, `Concluída`, `Modo da rodada`) instead of raw backend labels.
- Added purpose/action guidance to the execution summary so the operator can tell whether the latest run is already decision-ready before opening deeper comparison.
- Added guided purpose/action cards to the `Runs` and `Decisão` transition panels so the path `Studio -> Runs -> Decisão` explains what each area resolves before the operator dives into details.
- Added the same first-fold framing to the official decision panel and the main Audit bundle panel, keeping Audit clearly positioned as canonical evidence space rather than a raw persistence dump.
- Clarified filtered and no-result decision states while preserving the existing technical evidence behind disclosure, and translated the primary decision-state label to `Empate técnico` / `Winner claro`.
- Extended smoke coverage to protect the new guided microcopy, humanized primary labels, and the first-fold hierarchy across Studio, Runs, and Decisão.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_projection_panel_explains_business_layer_boundary or primary_runs_panels_hide_raw_backend_keys_in_main_surface or primary_decision_panels_hide_raw_metric_keys_in_main_surface or audit_bundle_panel_preserves_technical_space_but_explains_next_step or studio_readiness_panel_humanizes_primary_blockers_and_warnings" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-targeted2
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-full2
```

Result:

- `5 passed, 42 deselected in 0.43s`
- `47 passed in 481.22s (0:08:01)`

## Evidence

- Structured UI snapshot: `docs/2026-04-05_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to the Julia-only official execution path or fail-closed semantics.
- No change to `docs/05_data_contract.md`.
- No backend optimization, queue semantics, or solver changes beyond product-surface copy and state framing.

## Honest Handoff

This wave stayed strictly on UX framing. It did not add new product areas or backend behavior; it closed the gap where the first fold still mixed raw status labels, terse warnings, and implicit next steps. Technical detail remains available, but the primary read now explains purpose, current state, and next action more directly across the Studio, Runs, and Decisão path.
