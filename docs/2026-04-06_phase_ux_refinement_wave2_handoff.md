# Phase UX Refinement Wave 2 - Guided First-Fold States Across Studio, Runs and Decision

## Objective

Deepen `ux_phase_1` by making the first fold of `Studio`, `Runs` and `Decisão` more self-explanatory: each primary area should communicate its dominant state, its main next action and whether the operator should stay in place, go back or advance.

## Delivered

- Refined `render_studio_readiness_panel` in `src/decision_platform/ui_dash/app.py` so the first fold now exposes a dominant Studio state (`Pronto para Runs`, `Bloqueado no Studio`, `Exige atenção`) and switches the primary CTA between fixing on the canvas and advancing to Runs.
- Extended the Studio workbench-open callback so readiness can push the operator straight into the editing surface instead of forcing tab discovery or technical reading first.
- Refined `render_runs_flow_panel` to distinguish first-fold states for waiting on Studio readiness, active execution, queued work, blocked result, no usable result and decision-ready output.
- Replaced the always-on Decision link in the Runs first fold with a button that is enabled only when a usable execution result exists, while keeping the execution summary panel aligned with the same product-language state.
- Tightened `render_decision_flow_panel` so the dominant CTA now shifts toward `Runs` when no usable decision exists or when the winner is explicitly infeasible, while keeping `Auditoria` as the advanced path when the decision read is already usable.
- Corrected decision-state interpretation so missing `feasible` does not silently turn a technical tie into an infeasible winner.
- Expanded smoke coverage in `tests/decision_platform/test_ui_smoke.py` for the new first-fold states, button enablement rules and updated navigation callback behavior.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_tab_surfaces_readiness_and_selection_context or studio_discovery_callbacks_open_guide_and_audit_tab or studio_readiness_panel_surfaces_runs_transition_with_real_readiness or studio_readiness_panel_humanizes_primary_blockers_and_warnings or runs_tab_combines_queue_and_execution_summary or runs_flow_panel_reflects_studio_gate_and_queue_state or runs_flow_panel_enables_decision_only_with_usable_execution_result or primary_runs_panels_hide_raw_backend_keys_in_main_surface or canvas_context_button_opens_studio_workbench or decision_flow_panel_makes_transition_and_next_action_explicit" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-targeted-rerun
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-full
```

Result:

- `10 passed, 57 deselected in 1.40s`
- `72 passed in 504.20s (0:08:24)`

## Evidence

- Structured first-fold snapshot: `docs/2026-04-06_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, fail-closed policy, queue semantics or backend ranking/decision logic.
- No deep structural refactor of the Studio editor beyond first-fold CTA routing.

## Honest Handoff

This wave makes the first fold more operationally honest. `Studio` now tells the operator whether to fix the scenario in place or move to `Runs`. `Runs` no longer implies that `Decisão` is always the next move; the button now reflects whether a usable result actually exists. `Decisão` now points back to `Runs` when the read is absent or blocked, instead of prematurely biasing toward `Auditoria`. The deeper surfaces are still dense, but the top-of-screen flow is more linear and less dependent on reading technical detail to know what to do next.
