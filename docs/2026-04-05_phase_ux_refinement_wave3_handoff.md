# Phase UX Refinement Wave 3 - Shell Consistency and Active Space Framing

## Objective

Close `ux_phase_1` by removing the remaining ambiguity in the product shell: every primary space should announce where the operator is, what that space resolves, and what to do before leaving it, without relying on technical disclosure.

## Delivered

- Added a persistent `product-space-banner` below the hero so `Studio`, `Runs`, `Decisão`, and `Auditoria` now share the same first-fold framing regardless of the active tab.
- Defined explicit product-language content for each main space (`Grafo de negócio e readiness do cenário`, `Fila local e execução em foco`, `Winner, runner-up e contraste com contexto`, `Trilha canônica e evidência técnica`) to reduce residual ambiguity between tabs.
- Reused the same banner structure for all four spaces with consistent `O que resolver aqui` and `Antes de sair desta área` guidance, making the shell easier to maintain than hand-tuning context per tab entry point.
- Wired the banner to primary navigation updates so tab changes and cross-surface CTAs keep the active-space framing synchronized with the current product area.
- Extended smoke coverage to lock the persistent banner, its callback refresh behavior, and the product-language contract for the four spaces.

## Validation

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider -k "product_space_banner or dash_app_surfaces_only_four_primary_product_spaces" --basetemp tests/_tmp/pytest-basetemp-ux-wave3-targeted
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave3-full
```

Result:

- `3 passed, 47 deselected in 1.14s`
- `50 passed in 487.68s (0:08:07)`

## Evidence

- Structured shell snapshot: `docs/2026-04-05_phase_ux_refinement_wave3_ui_snapshot.json`
- Screenshot attempt was blocked by the local execution policy; the structured snapshot records that limitation explicitly.

## Scope Guardrails

- No architecture reopening.
- No replacement of Dash or Cytoscape.
- No change to the Julia-only official execution path or fail-closed semantics.
- No change to `docs/05_data_contract.md`.
- No backend optimization, queue, or solver changes beyond shell framing and UI consistency.

## Honest Handoff

This wave stayed inside the shell. It did not open `ux_phase_2`; instead it closed `ux_phase_1` by making the active product space explicit and consistent across the four main areas. The remaining limitation is visual capture: a real screenshot was attempted but blocked by the environment policy, so the wave closes with a structured shell snapshot rather than a rendered image.
