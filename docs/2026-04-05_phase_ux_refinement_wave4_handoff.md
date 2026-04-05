# Phase UX Refinement Wave 4 - Decision Language Hardening

## Objective

Remove raw backend failure codes from the primary `Decisão` experience and replace them with faithful product-language explanations for inviability, `technical_tie`, and contrast signals, without changing ranking, selection, or runtime behavior.

## Delivered

- Added a shared translation layer in `src/decision_platform/ui_dash/app.py` to humanize primary infeasibility reasons and route issues before they reach the first decision fold.
- Replaced raw codes such as `mandatory_route_failure`, `connectivity`, `hydraulics`, and `measurement_required_without_compatible_meter` with operator-facing explanations that preserve the underlying meaning.
- Aligned the language of `Escolha oficial`, `Runner-up e contraste`, `Sinais para decisão humana`, and `Candidato em foco` so the decision surface no longer mixes product copy with backend identifiers.
- Kept technical disclosure available through existing JSON/details areas; only the primary language changed.
- Preserved `technical_tie`, winner, runner-up, and all ranking semantics exactly as delivered by the backend.
- Updated smoke coverage to block regressions where raw infeasibility codes or backend field labels leak back into the main decision surface.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "primary_decision_panels_hide_raw_metric_keys_in_main_surface" --basetemp tests/_tmp/pytest-basetemp-ux-wave4-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave4-full
```

Result:

- `1 passed, 37 deselected in 0.55s`
- `38 passed in 421.16s`

## Evidence

- Structured decision-language snapshot: `docs/2026-04-05_phase_ux_refinement_wave4_ui_snapshot.json`

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to ranking, official-candidate selection, infeasibility computation, or `technical_tie` behavior.
- No change to the Julia-only official path, fail-closed behavior, or queue/runs semantics.
- No reintroduction of logs, raw JSON, or technical identifiers as primary UX.

## Honest Handoff

This wave fixed a real UX leakage rather than adding polish for its own sake. The backend still decides inviability exactly as before, but the operator no longer sees raw failure codes in the first decision read. The translation is intentionally narrow and faithful: it explains the operational impact while leaving the technical trail intact in disclosure for deeper diagnosis.
