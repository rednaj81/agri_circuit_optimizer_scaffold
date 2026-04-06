# Phase UX Refinement Wave 1 - Navigation and IA Cleanup

## Objective

Clarify the main product path of `decision_platform` so that `Studio`, `Runs`, `Decisão`, and `Auditoria` read as a guided flow, with primary summaries ahead of raw technical surfaces.

## Delivered

- Consolidated the main navigation into four visible product spaces: `Studio`, `Runs`, `Decisão`, and `Auditoria`.
- Reframed the shell with a guided hero that explains the operator journey from scenario preparation to audit trail and added direct deep links for each primary space.
- Kept the business graph as the primary Studio surface and left technical payloads behind `Details` disclosure blocks instead of on the first fold.
- Preserved scenario-readiness and connectivity guidance in `Studio` while keeping the quick focus rail on the business graph side of the experience.
- Added explicit transition actions from `Runs` to `Decisão` so queue review and decision reading now behave like one operator path instead of isolated console panels.
- Added a dedicated `Passagem Runs -> Decisão` panel so winner, runner-up, and `technical tie` state are legible before the deeper comparison tools.
- Preserved the canonical bundle editors and full audit tables in `Auditoria`, outside the primary editing, queue, and decision path.
- Extended smoke coverage to assert hero navigation links, the explicit `Runs` -> `Decisão` path, the new decision-flow panel, conditional Studio recommendation actions, and that technical JSON remains inside progressive disclosure.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1-full
```

Result:

- `42 passed in 490.28s (0:08:10)`

## Evidence

- Structured UI snapshot: `docs/2026-04-05_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash/Cytoscape.
- No change to Julia-only official execution or fail-closed semantics.
- No change to `docs/05_data_contract.md`.
- No hydraulic core, queue contract, or solver logic changes outside the existing UI surfaces.

## Honest Handoff

The checked-out worktree already contained most of the UX refinement implementation in `app.py` and `test_ui_smoke.py` before this session started, including some Studio interaction polish beyond the narrow navigation cleanup scope. This session treated that checked-out state as the source of truth, validated it end to end, refreshed the wave-1 evidence, and documented the real outcome honestly instead of pretending the navigation shell was authored from scratch here.
