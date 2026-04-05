# Phase UX Refinement Wave 1 - Navigation and IA Cleanup

## Objective

Clarify the main product path of `decision_platform` so that `Studio`, `Runs`, `Decisão`, and `Auditoria` read as a guided flow, with primary summaries ahead of raw technical surfaces.

## Delivered

- Consolidated the main navigation into four visible product spaces: `Studio`, `Runs`, `Decisão`, and `Auditoria`.
- Reframed the shell with a guided hero that explains the operator journey from scenario preparation to audit trail.
- Kept the business graph as the primary Studio surface and moved raw JSON/debug payloads behind `Details` disclosure blocks.
- Added explicit Studio readiness next steps so the operator sees what to fix before enqueueing a run.
- Added queue guidance text in `Runs` so empty, idle, and pending states read as operational guidance instead of a console dump.
- Kept winner, runner-up, technical tie, comparison, candidate circuit, and detailed rationale grouped under the `Decisão` product space.
- Preserved the canonical bundle editors and full audit tables in `Auditoria`, outside the primary editing and decision path.
- Extended smoke coverage to assert the four visible tabs, the new primary summary panels, and that debug JSON remains inside progressive disclosure.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave1
```

Result:

- `28 passed in 369.72s`

## Evidence

- Structured UI snapshot: `docs/2026-04-05_phase_ux_refinement_wave1_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash/Cytoscape.
- No change to Julia-only official execution or fail-closed semantics.
- No change to `docs/05_data_contract.md`.
- No hydraulic core or solver logic changes outside the existing UI summaries.

## Honest Handoff

The main UI reorganization for this wave was already present in the checked-out `app.py` and smoke test worktree when this session started. This wave finished the delivery by validating the reworked UX against the real test suite, tightening the primary summaries with next-step/guidance copy, adding disclosure-focused smoke coverage, and recording the wave evidence and handoff.
