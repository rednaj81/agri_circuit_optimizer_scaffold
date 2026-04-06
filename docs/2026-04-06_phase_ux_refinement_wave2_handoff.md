# Phase UX Refinement Wave 2 - Persistent Framing and Guided Cross-Space Navigation

## Objective

Close the information-architecture gap left after the previous wave by making the main shell itself explain where the operator is, what that area resolves now, and which primary space should come next according to the real Studio, Runs and Decisão state.

## Delivered

- Turned the persistent `product-space-banner` into a state-aware shell surface in `src/decision_platform/ui_dash/app.py`: it now combines the active-space framing with `Estado do fluxo agora` and `Próximo destino sugerido`, instead of only repeating static space descriptions.
- Added `_space_transition_guidance(...)` so Studio, Runs, Decisão and Auditoria can express guided transitions from the current product state, including when the operator should stay in place, go back to Studio or advance to Runs or Decisão.
- Updated the banner callback to consume real readiness, queue and decision summaries, keeping the sticky framing synchronized with tab changes and with the actual scenario/run state.
- Refined the main journey cards so their CTA labels and destinations are no longer generic `Abrir ...`; they now reflect the guided next move, such as `Seguir para Runs`, `Ir para Decisão` or `Voltar para Runs`, while preserving the four-space shell.
- Kept the Studio primary surface focused on the business graph only; this wave stayed in shell framing and navigation guidance and did not reintroduce raw JSON, technical hubs or solver-oriented clutter into the first fold.
- Updated `tests/decision_platform/test_ui_smoke.py` to lock the new banner language, the state-driven guidance and the journey CTA destinations.
- Refreshed the structured evidence artifact in `docs/2026-04-06_phase_ux_refinement_wave2_ui_snapshot.json` with the new shell markers and validation output.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "product_space_banner or product_journey_panel or studio_discovery_callbacks_open_guide_and_audit_tab or studio_tab_surfaces_readiness_and_selection_context" --basetemp tests/_tmp/pytest-basetemp-dev-wave2-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-dev-wave2-full
```

Result:

- `9 passed, 69 deselected in 1.56s`
- `87 passed in 460.22s (0:07:40)`

## Evidence

- Structured shell-navigation snapshot: `docs/2026-04-06_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No change to Dash/Cytoscape stack or Julia-only official execution.
- No backend queue, solver, ranking or hydraulic-model changes.
- No reintroduction of technical internals, raw JSON or debug-first surfaces into the primary Studio path.

## Honest Handoff

This wave stayed in the shell and fixed a genuine IA gap: the sticky framing was still too static, and the main journey cards still behaved like tab shortcuts instead of guided product transitions. The result is more explicit about what each space resolves and when the operator should remain in Studio, move into Runs, open Decisão or return from Decisão/Auditoria to a more appropriate primary space. The deeper surfaces are unchanged; the gain is clarity in the first reading of the product shell, not a new editing or execution flow.
