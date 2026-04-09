# Phase UX Refinement Wave 9 Handoff

## Escopo entregue

- Transformei as ações contextuais do primeiro fold do Studio em affordances previsíveis: elas continuam curtas, mas deixam de sumir sem explicação.
- Fechei a leitura da passagem Studio -> Runs no próprio painel dominante, sem reabrir a lateral nem voltar a multiplicar painéis.

## Implementação

- `src/decision_platform/ui_dash/app.py`
  - O painel `studio-workspace-context-panel` agora mostra:
    - `Próxima ação disponível`
    - `O que libera a seguinte`
    - `Passagem para Runs`
  - Mantive os botões contextuais do foco sempre visíveis no primeiro fold:
    - `studio-workspace-require-measurement-button`
    - `studio-workspace-create-route-button`
    - `studio-workspace-reverse-edge-button`
  - Cada ação passou a ter affordance contextual explícita no bloco `studio-workspace-context-affordances`, deixando claro quando está disponível, quando já foi satisfeita e quando depende de uma condição ainda não atendida.
  - O gate para Runs ficou resumido no próprio contexto dominante, sem exigir disclosure adicional para entender se o operador deve seguir ou continuar corrigindo o Studio.

- `tests/decision_platform/test_ui_smoke.py`
  - Cobertura dos novos estados de descoberta no primeiro fold.
  - Cobertura do cenário sem conexão em foco, garantindo que os controles não desapareçam sem orientação.

## Validação

Executado:

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave9-full
```

Resultado:

- `124 passed in 368.92s (0:06:08)`

## Evidência

- `output/playwright/wave9-studio-context-affordances.json`

## Limitações

- A wave melhora previsibilidade e descoberta no primeiro fold, mas não muda o escopo funcional do Studio.
- A evidência permanece estrutural; não houve screenshot literal do app nesta rodada.

