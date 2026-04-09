# Phase UX Refinement Wave 8 Handoff

## Escopo entregue

- Promovi correções frequentes de readiness e conectividade para o painel dominante do Studio, sem reabrir arquitetura nem inflar a lateral.
- Mantive a sidebar curta da wave 7 e preservei a estabilidade do canvas consolidada na wave 6.

## Implementação

- `src/decision_platform/ui_dash/app.py`
  - Adicionado `studio-workspace-context-direct-actions` no bloco contextual principal do Studio.
  - Promovidas ações contextuais diretas para o primeiro fold:
    - `studio-workspace-require-measurement-button`
    - `studio-workspace-create-route-button`
    - `studio-workspace-reverse-edge-button`
  - Reaproveitados callbacks já existentes para:
    - exigir medição direta no trecho em foco sem disclosure;
    - carregar criação de rota a partir do trecho em foco;
    - inverter trecho crítico a partir do painel dominante.
  - Os botões permanecem sempre no layout para não quebrar validação do Dash, mas aparecem só quando o contexto do trecho pede a ação.

- `tests/decision_platform/test_ui_smoke.py`
  - Cobertura do novo painel de ações diretas.
  - Cobertura do atalho de medição direta disparado pelo painel dominante.
  - Ajuste das assinaturas de callback afetadas pela promoção dos novos inputs.

- `tests/decision_platform/test_studio_structure.py`
  - Cobertura estrutural dos novos controles no layout principal.

## Validação

Executado:

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave8-full
```

Resultado:

- `123 passed in 349.61s (0:05:49)`

## Evidência

- `output/playwright/wave8-studio-direct-actions.json`

## Limitações

- A wave resolve tarefas frequentes direto no painel dominante, mas não substitui o contexto detalhado para revisão ampla de readiness.
- A evidência registrada nesta wave é estrutural e orientada a comportamento; não há screenshot literal do app.

