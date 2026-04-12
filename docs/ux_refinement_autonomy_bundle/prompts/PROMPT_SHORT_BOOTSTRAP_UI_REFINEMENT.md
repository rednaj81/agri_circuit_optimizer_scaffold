Use the current HEAD of the branch as source of truth. Do not reopen architecture.

Read:
1. docs/ux_refinement_autonomy_bundle/README.md
2. docs/ux_refinement_autonomy_bundle/02b_market_grade_ux_doctrine.md
3. docs/ux_refinement_autonomy_bundle/03_frozen_decisions.md
4. docs/ux_refinement_autonomy_bundle/04_target_user_flows.md
5. docs/ux_refinement_autonomy_bundle/07_autonomous_agent_roles.md
6. docs/ux_refinement_autonomy_bundle/08_acceptance_and_exit_criteria.md
7. current README.md
8. src/decision_platform/ui_dash/app.py

Goal:
refine the UX of decision_platform into a cleaner, more guided, more pleasant product while preserving architecture and stack.

Non-negotiable UX direction:
- the Studio must show only the business graph editable by the user
- internal technical hubs/intermediate nodes must stay out of the primary Studio surface
- the initial Studio flow must start from the routes that need to be served and the particularities of those routes
- do not present hubs, centrais or strategic helper structures as first-class editing objects on the first surface
- route intent may be mandatory, optional or desirable, and the UX must express that in product language
- direct manipulation on the canvas is preferred over raw forms
- routine Studio work should move toward local canvas actions instead of advanced workbench dependency
- the first fold must make "who supplies whom" explicit in business language
- raw JSON, `html.Pre` and logs are not acceptable as the main UI
- the product must feel closer to market software than to an engineering console

Start by:
- auditing current UX surfaces
- identifying the highest-impact friction points
- planning phase 1 of the UX refinement
- then implement incrementally with commits
