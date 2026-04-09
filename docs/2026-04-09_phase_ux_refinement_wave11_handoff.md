# Phase UX Refinement Wave 11 Handoff

## Escopo entregue

- Abri formalmente `ux_phase_3` deslocando a superfície principal para Runs.
- A primeira dobra de Runs agora separa leitura de fila atual, execução em foco e histórico recente como áreas operacionais distintas, sem depender de logs brutos.

## Implementação

- `src/decision_platform/ui_dash/app.py`
  - Reorganizado `render_runs_workspace_panel` para priorizar três faixas operacionais no topo:
    - `Fila atual`
    - `Execução em foco`
    - `Histórico recente`
  - Mantido o gate do cenário e a recuperação como camadas secundárias, fora da leitura principal da primeira dobra.
  - Preservada a saída consolidada de `ux_phase_2` no Studio sem mudanças amplas na baseline anterior.

- `tests/decision_platform/test_ui_smoke.py`
  - Cobertura atualizada para a nova leitura de Runs.
  - Mantida a verificação de estados intermediários, recuperação após falha e separação entre gate do cenário e execução.

## Validação

Executado:

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave11-runs-rerun
```

Resultado:

- `106 passed in 356.35s (0:05:56)`

## Transição de fase

- `docs/2026-04-09_phase_ux_refinement_phase3_open.md` registra a abertura formal de `ux_phase_3`.
- O foco seguinte passa a ser queue readability, execução em foco e transição para Decisão, preservando o Studio como baseline estabilizada.

## Limitações

- Esta wave abre a fase de Runs pela superfície principal, mas não reestrutura ainda as camadas detalhadas de jobs, artifacts e evidências técnicas.
- A validação continua estrutural e de smoke; não houve automação visual interativa completa da fila em navegador.

