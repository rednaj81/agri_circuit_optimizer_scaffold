# Phase UX Refinement Wave 2 - Primary States and Progressive Disclosure

## Objective

Close the remaining information-hierarchy gaps in `decision_platform` by making empty states, no-selection states, and no-result states read in product language across `Studio`, `Runs`, `Decisão`, and `Auditoria`, while keeping technical evidence behind progressive disclosure.

## Delivered

- Reworked empty and no-selection states in the main product surfaces so they now explain what is missing and what the operator should do next instead of stopping at terse "none selected" copy.
- Kept `Studio` focused on the business graph while clarifying that an empty focus state should be resolved directly on the canvas, not through raw technical forms.
- Refined `Runs` queue, run-detail, and execution panels so they now explain the purpose of the area, the current state, and the next operator move even before there is a selected run or a completed execution.
- Clarified `Decisão` no-result states for official winner, runner-up contrast, candidate summary, breakdown, and filtered-catalog views so the user can tell whether the issue is missing execution context or filters hiding all candidates.
- Humanized the main Audit bundle panel so it clearly reads as a canonical evidence space with a boundary from the primary flow, while preserving the raw JSON bundle summary behind disclosure.
- Extended smoke coverage to lock the new product-language empty states, filtered-decision guidance, and the Audit boundary copy.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave2-current
```

Result:

- `45 passed in 460.22s (0:07:40)`

## Evidence

- Structured UI snapshot: `docs/2026-04-05_phase_ux_refinement_wave2_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to the Julia-only official execution path or fail-closed semantics.
- No change to `docs/05_data_contract.md`.
- No backend optimization, queue, or solver changes beyond product-surface copy and state framing.

## Honest Handoff

This wave stayed strictly on UX framing. It did not add new product areas or backend behavior; it closed the gap where the main tabs still relied on sparse empty states or generic "none available" messages that forced the operator to infer the next step. Technical detail remains available, but the first read of each space now explains purpose, current state, and next action more directly.
