Use the current repository HEAD as source of truth.
Do not rely on older handoffs that predate the current decision_platform state.

Read first:
1. docs/ux_refinement_autonomy_bundle/README.md
2. docs/ux_refinement_autonomy_bundle/01_current_state_and_baseline.md
3. docs/ux_refinement_autonomy_bundle/02_ux_findings_and_problem_statement.md
4. docs/ux_refinement_autonomy_bundle/03_frozen_decisions.md
5. docs/ux_refinement_autonomy_bundle/04_target_user_flows.md
6. docs/ux_refinement_autonomy_bundle/05_information_architecture.md
7. docs/ux_refinement_autonomy_bundle/06_ui_refinement_backlog.md
8. docs/ux_refinement_autonomy_bundle/07_autonomous_agent_roles.md
9. docs/ux_refinement_autonomy_bundle/08_acceptance_and_exit_criteria.md
10. docs/ux_refinement_autonomy_bundle/automation/phase_plan.yaml

Current product assumptions:
- decision_platform already exists and is the active product direction
- selected_candidate, selected_candidate_explanation, engine_comparison, studio, queue/run model, comparison view and technical_tie are already concepts in the product
- the next work is refinement and productization, not new architecture

Mission:
evolve decision_platform toward a more pleasant, clean, guided professional UX.

Hard constraints:
- do not reopen architecture
- do not create a new platform
- do not switch stack
- do not discard existing decision traces or artifacts
- commits are required per meaningful phase
- documentation must stay synchronized

Work mode:
- use UX Architect + Product Flow Engineer + UX Auditor mindset
- each wave must produce meaningful user-facing progress
- stop after 3 consecutive low-value waves
- hard threshold: 10 waves
- then do 1 final polish/stabilization wave

Primary UX goals:
1. cleaner navigation
2. clearer studio flow
3. better scenario readiness feedback
4. better run queue/processing clarity
5. stronger decision view with technical tie support
6. less raw technical noise on primary screens
7. better first-use friendliness without harming expert power

Expected implementation direction:
- projects / studio / runs / decision / audit as clearer product spaces
- progressive disclosure of technical detail
- explicit "ready to run" and "needs attention" states
- explicit technical tie handling
- explicit winner vs runner-up explanation in UI
- clearer connectivty/infeasibility prevention before running
- cleaner session persistence and chosen-candidate handling

Non-goals for this phase:
- no solver redesign
- no hydraulic core redesign
- no new platform split
- no broad refactor unrelated to UX

Deliverables expected across phases:
- improved UI surfaces
- updated docs
- commits by phase
- honest phase summaries
- test updates where behavior changes

Start by:
1. auditing the current UX against the target flows
2. defining wave 1 with the highest-value UX improvements
3. implementing wave 1
4. committing
5. summarizing progress and remaining friction
