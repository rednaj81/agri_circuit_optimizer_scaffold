# Phase UX Refinement Wave 1 Handoff

## Scope

- Phase: `phase_ux_refinement`
- Wave: `1`
- Mode: `ux_refinement`
- Focus: `ux_phase_3` with explicit condensation of Runs and objective visual relief of the Studio sidebar, plus redundant decision-panel reduction.

## What changed

- Narrowed the Studio sidebar and reduced inter-card spacing so the canvas regains perceptual dominance.
- Condensed `render_studio_readiness_panel` into a compact readiness strip plus secondary disclosures, replacing the previous tall stack of large cards.
- Rebuilt the Runs primary fold into compact operational tiles for `run em foco`, `fila agora`, `histórico terminal`, `próxima ação segura` and `cenário x execução`.
- Kept detailed run history, status language and scenario-vs-run limits behind disclosures instead of presenting them as the first surface.
- Condensed the Decision primary fold by removing repeated winner/runner-up/tie restatements from the main strip and keeping the second strip focused on human choice, export, dominant risk and open comparison.
- Updated UI smoke assertions to follow the compact composition without relaxing the Julia-only fail-closed behavior.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile src\decision_platform\ui_dash\app.py`
- `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_phase3_runs_ui_smoke.py tests\decision_platform\test_phase3_queue_acceptance.py tests\decision_platform\test_ui_smoke.py -q`

## Result

- Target achieved for this wave: Runs now reads as an operational front in the first fold, the Studio sidebar is materially lighter, and Decision no longer repeats the same winner/runner-up/tie story under multiple headings.

## Residual risks

- This wave improved structural density through Dash composition and spacing, but it does not include fresh browser screenshots in this handoff.
- The Studio sidebar is lighter, but a future polish wave can still simplify the command-center disclosure labels and reduce secondary copy further.
- Runs remains information-dense by necessity when a selected run carries lineage, failure or rerun context; further reduction would need careful guardrails to avoid hiding recovery signals.

## Honest handoff

- Meaningful UX progress was made in this wave.
- No architecture was reopened.
- The Julia-only official path was not altered.
- The work stayed within the accepted files and kept raw JSON/log surfaces behind progressive disclosure.
