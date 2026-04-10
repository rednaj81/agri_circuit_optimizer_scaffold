# Phase UX Refinement Wave 7 Handoff

## Scope

- Phase: `phase_ux_refinement`
- Wave: `7`
- Opened phase: `ux_phase_4`
- Focus: first-fold Decision hierarchy and honest inheritance of `blocked_on_evidence` from `ux_phase_3`.

## What changed

- Opened `ux_phase_4` explicitly in documentation without pretending `ux_phase_3` had become fully closed.
- Reduced repetition in the first fold of Decision by collapsing the secondary strip into a single assisted flow: next human action, comparison in open review, and export guidance.
- Kept winner, runner-up, decision state and safe next move visible in the primary fold.
- Preserved Studio and Runs without new functional expansion.
- Added tests covering the new Decision hierarchy and the honest phase-opening documents.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile src\decision_platform\ui_dash\app.py`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase4_decision_acceptance.py tests\decision_platform\test_ui_smoke.py -q`

## Result

- `ux_phase_4` is formally open.
- Decision now reads faster in the first fold without repeating the same conclusion across multiple cards.
- The inherited `blocked_on_evidence` status from `ux_phase_3` remains explicit in docs and governance.
