# Phase UX Refinement Wave 3 - Persistent Active-Space Banner for Shell Closure

## Objective

Close `ux_phase_1` with a shell-level framing element that stays visible and synchronized across `Studio`, `Runs`, `Decisão` and `Auditoria`, so the operator always knows where they are, what that space resolves and what must happen before moving on.

## Delivered

- Refined `render_product_space_banner` in `src/decision_platform/ui_dash/app.py` into a persistent shell banner with sticky positioning, keeping the active-space framing visible while the operator scrolls through the primary surfaces.
- Added a shell switcher inside the banner with direct links for `Studio`, `Runs`, `Decisão` and `Auditoria`, without introducing any new top-level product spaces.
- Standardized the shell copy so every active-space banner now communicates the same two product questions: `O que esta área resolve` and `Condição de saída`.
- Kept the active-space banner synchronized with the existing primary-tab state, which already receives updates from query-param navigation and internal cross-space CTAs.
- Extended `tests/decision_platform/test_ui_smoke.py` to cover sticky banner presence, switcher link availability, banner copy consistency and alignment with navigation resolution.
- Generated updated shell evidence for the phase-close wave in `docs/2026-04-06_phase_ux_refinement_wave3_ui_snapshot.json`.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "surfaces_only_four_primary_product_spaces or product_space_banner_uses_consistent_product_language_for_each_space or product_space_banner_exposes_shell_switcher_for_all_primary_spaces or product_space_banner_callback_tracks_active_primary_tab or product_space_banner_stays_aligned_with_navigation_resolution or product_journey_panel_callback_tracks_active_primary_tab_and_state or studio_discovery_callbacks_open_guide_and_audit_tab" --basetemp tests/_tmp/pytest-basetemp-ux-wave3-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-full
```

Result:

- `7 passed, 62 deselected in 1.42s`
- `74 passed in 421.08s (0:07:01)`

## Evidence

- Structured shell-close snapshot: `docs/2026-04-06_phase_ux_refinement_wave3_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No new primary spaces beyond `Studio`, `Runs`, `Decisão` and `Auditoria`.
- No deep internal redesign of Studio, queue or Decision beyond shell-level framing.

## Honest Handoff

This wave is intentionally narrow and closes `ux_phase_1` at the shell level. The main gain is persistence and orientation: the operator now gets a sticky active-space banner that remains visible while reading deeper panels, with a consistent explanation of what each area resolves and what must happen before leaving it. The product shell is more self-explanatory now, but the deeper per-area complexity still belongs to later phases rather than this closure wave.
