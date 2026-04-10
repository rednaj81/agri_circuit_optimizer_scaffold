# UX Phase 4 Open - Decision View and Technical Tie Support

## Phase

- `ux_phase_4`

## Opening Decision

- Open accepted.
- The phase can proceed on top of the stabilized Runs -> Decision transition from `ux_phase_3`.

## Baseline Established By Wave 4

- The first fold of `Decisão` now exposes the dominant decision state directly, instead of forcing the operator into broad comparison grids before understanding whether the decision is actually ready.
- `Winner`, `runner-up`, and `Próxima ação segura` have primary weight in the workspace, with `technical_tie` and blocked/no-result states explicitly called out as operational states.
- Technical disclosure remains secondary: comparison density, profile views, and export context are still available, but they no longer compete with the initial decision read.
- Honest gating from Runs remains intact: no-result and infeasible states do not simulate confidence or default to export language.

## Evidence

- `docs/2026-04-09_phase_ux_refinement_wave4_handoff.md`
- `docs/2026-04-09_phase_ux_refinement_wave4_ui_snapshot.json`

## Known Caveat

- A real browser capture was attempted through a local Dash launch on port `8056`, but the process exited before serving the page and no browser screenshot artifact was produced. The phase remains open with structured snapshot evidence and explicit documentation of that blocker.

## Next Boundary

- Continue inside `ux_phase_4`.
- Focus next on deepening the product reading of `winner` versus `runner-up`, explicit `technical_tie` rationale, and the final assisted choice without re-expanding Runs or reopening architecture.
- Keep raw payloads, logs, and JSON out of the primary Decision surface.
