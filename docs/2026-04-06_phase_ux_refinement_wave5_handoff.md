# Phase UX Refinement Wave 5 - Studio Context Stack Simplification

## Objective

Deepen `ux_phase_2` by simplifying the Studio contextual stack: reduce repeated cards and messages while keeping the canvas as the primary entry point and preserving honest readiness feedback.

## Delivered

- Simplified `Foco do canvas` so it now reads as a shorter contextual flow: selection state, current problem or opportunity, why that focus matters, transition to Runs, and quick actions.
- Removed duplicated sections that previously split the same idea across `Impacto operacional`, `Regras deste foco`, and `Readiness deste foco`; the new hierarchy keeps those signals in a single contextual read.
- Differentiated secondary selection guidance for node editing, edge editing, and empty selection, replacing the old shared fallback text with specific next-step language for each case.
- Kept the Studio anchored to the business graph and to the current selection, without adding new panels or promoting technical disclosures.
- Updated smoke coverage to protect the simplified hierarchy of the contextual stack and the distinct guidance for node, edge, and no-selection states.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "studio_focus_panel or studio_selection_panel or primary_surfaces_explain_empty_states_without_debug_language" --basetemp tests/_tmp/pytest-basetemp-ux-wave5-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave5-full
```

Result:

- `5 passed, 47 deselected in 0.63s`
- `52 passed in 446.67s (0:07:26)`

## Evidence

- Structured Studio snapshot: `docs/2026-04-06_phase_ux_refinement_wave5_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to Julia-only official execution, queue semantics, or backend optimization logic.
- No change to `docs/05_data_contract.md`.
- No exposure of technical hubs or derived nodes on the Studio primary surface.

## Honest Handoff

This wave focused on subtraction, not expansion. The contextual stack is now shorter and more state-specific, especially around empty selection versus node or edge editing. The remaining limitation is still visual capture: the wave uses a structured snapshot instead of a screenshot because local capture remained blocked by policy.
