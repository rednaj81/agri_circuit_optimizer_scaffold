# Phase UX Refinement Wave 2 - Studio Readiness to Runs Flow

## Objective

Make the main path between `Studio` and `Runs` explicit in the product surface so the operator can tell when the scenario is really ready to enqueue, when it still needs structural fixes, and how the local queue should be read without falling back to raw technical output.

## Delivered

- Strengthened `Studio` readiness with an explicit headline, blocker/warning counters, and a dedicated `Passagem para Runs` block in the primary panel.
- Added a direct `Ir para Runs` CTA from the main Studio readiness surface without exposing technical fields or reopening the information architecture.
- Added a mirrored `Passagem Studio -> Runs` panel inside `Runs` so queue reading now starts from the real Studio readiness state instead of only from the queue internals.
- Added a `Voltar ao Studio` CTA in `Runs` to make the corrective path explicit whenever readiness still signals structural issues.
- Kept logs, JSON, and technical paths behind progressive disclosure; the first screen of `Runs` now prioritizes queue summary, readiness-to-run context, execution summary, and run-in-focus guidance.
- Preserved the existing Dash/Cytoscape architecture, Julia-only official path, fail-closed runtime behavior, and hidden technical graph entities in the Studio primary canvas.
- Extended smoke coverage to protect the new readiness-to-runs copy, the cross-tab CTAs, and the continued separation between primary UX and technical disclosure.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_readiness_panel_surfaces_runs_transition_with_real_readiness or runs_flow_panel_reflects_studio_gate_and_queue_state or studio_discovery_callbacks_open_guide_and_audit_tab or runs_tab_combines_queue_and_execution_summary" --basetemp tests/_tmp/pytest-basetemp-ux-wave2-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-full
```

Result:

- `4 passed, 34 deselected in 0.81s`
- `38 passed in 424.06s`

## Evidence

- Structured UI snapshot: `docs/2026-04-05_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to the Julia-only official execution path or fail-closed semantics.
- No change to `docs/05_data_contract.md`.
- No change to solver, runner, ranking, or official-candidate logic beyond UX framing of already-existing state.

## Honest Handoff

This wave stayed on the product surface and did not introduce backend behavior. The key change was making readiness and queue entry read as one guided flow across `Studio` and `Runs`, with explicit CTAs and real blocker/warning counts tied to the existing readiness rules. Technical disclosure remains available, but it no longer competes with the first operational read of the scenario and queue state.
