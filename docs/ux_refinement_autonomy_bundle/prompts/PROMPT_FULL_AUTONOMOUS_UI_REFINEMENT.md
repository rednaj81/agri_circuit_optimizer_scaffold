Use the current repository HEAD as source of truth.
Do not rely on older handoffs that predate the current decision_platform state.

Read first:
1. docs/ux_refinement_autonomy_bundle/README.md
2. docs/ux_refinement_autonomy_bundle/01_current_state_and_baseline.md
3. docs/ux_refinement_autonomy_bundle/02_ux_findings_and_problem_statement.md
4. docs/ux_refinement_autonomy_bundle/02b_market_grade_ux_doctrine.md
5. docs/ux_refinement_autonomy_bundle/03_frozen_decisions.md
6. docs/ux_refinement_autonomy_bundle/04_target_user_flows.md
7. docs/ux_refinement_autonomy_bundle/05_information_architecture.md
8. docs/ux_refinement_autonomy_bundle/06_ui_refinement_backlog.md
9. docs/ux_refinement_autonomy_bundle/07_autonomous_agent_roles.md
10. docs/ux_refinement_autonomy_bundle/08_acceptance_and_exit_criteria.md
11. docs/ux_refinement_autonomy_bundle/automation/phase_plan.yaml

Current product assumptions:
- decision_platform already exists and is the active product direction
- selected_candidate, selected_candidate_explanation, engine_comparison, studio, queue/run model, comparison view and technical_tie are already concepts in the product
- the next work is refinement and productization, not new architecture

Mission:
evolve decision_platform toward a more pleasant, clean, guided professional UX.

Critical product direction:
- this must become closer to market software, not a cleaned-up engineering console
- the Studio must represent the business graph only
- internal technical hubs, derived hydraulic nodes and solver-oriented intermediates must stay hidden from the primary Studio experience
- if the solver needs extra internal graph structure, it must be derived behind the scenes
- the initial Studio workflow must start from drawing the routes that need service and defining route-specific particularities
- do not use hubs, centrais or strategic helper objects as first-class entities on the opening Studio surface
- route intent should support mandatory, optional and desirable semantics in product language instead of forcing every route to be hard-constrained
- direct manipulation on the canvas is a first-class requirement
- the next waves must prioritize the Studio interaction model over more shell polish
- the first-fold Studio reading must make who supplies whom explicit in business language
- advanced workbench paths should become fallback paths for uncommon edits, not the normal route for common actions
- raw JSON, `html.Pre`, and logs must move behind progressive disclosure and audit-only areas

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
8. business-facing Studio instead of technical graph exposure
9. market-grade visual polish and hierarchy

Expected implementation direction:
- projects / studio / runs / decision / audit as clearer product spaces
- progressive disclosure of technical detail
- explicit "ready to run" and "needs attention" states
- explicit technical tie handling
- explicit winner vs runner-up explanation in UI
- clearer connectivty/infeasibility prevention before running
- cleaner session persistence and chosen-candidate handling
- direct manipulation in Studio over fragmented raw forms
- business entities on the main canvas, technical internals hidden
- final circuit view focused on relevant business topology only

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
- visual evidence for major UI changes when possible

Start by:
1. auditing the current UX against the target flows
2. explicitly identifying which current surfaces still feel like technical tooling instead of product
3. identifying which visible nodes/entities must disappear from the Studio and final view because they are technical internals
4. identifying which routine Studio tasks still depend too much on the advanced workbench instead of direct canvas interaction
5. identifying where the supply chain of the business graph is still implicit instead of explicit
6. defining the next wave with the highest-value UX improvements in that direction
7. implementing that wave
8. committing
9. summarizing progress and remaining friction
