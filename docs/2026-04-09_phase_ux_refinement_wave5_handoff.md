# Phase UX Refinement Wave 5 Handoff

## Objetivo da onda

Consolidar a entrada route-first do Studio em linguagem de produto, permitir troca direta do trecho em foco na superfície principal e reduzir o viés técnico do foco inicial.

## Implementação

- adicionado no primeiro fold do Studio um seletor primário de trecho com rótulos de negócio em `src/decision_platform/ui_dash/app.py`
- o banner do trecho em foco passou a explicar por que aquele trecho foi sugerido, sem expor `route:R...` como linguagem principal
- criada a callback `_apply_primary_route_focus` para trocar o foco principal direto do canvas, atualizando o trecho em foco e o nó de contexto sem abrir a bancada avançada
- a sincronização do dropdown primário passa a seguir o trecho em foco atual e a preservar labels de negócio ao alternar entre rotas relevantes

## Validação

- `PYTHONPATH='src;.' .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave5-current`
- resultado: `99 passed in 394.12s (0:06:34)`

## Evidências

- captura estruturada com foco inicial e troca direta de trecho: `output/playwright/wave5-studio-focus-switch-capture.json`
- relatório HTML browser-ready com leitura perceptiva da troca de foco: `output/playwright/wave5-studio-focus-switch-report.html`
- payload live do layout do app em execução: `output/playwright/wave5-studio-focus-switch-layout.json`

## Limitações

- a evidência desta onda continua estruturada e browser-ready, não screenshot PNG do app rodando em navegador automatizado
- o store interno ainda usa `route:<id>` para operar callbacks, mas a superfície primária e o relatório perceptivo desta onda deixam esses identificadores fora da leitura principal
- o worktree segue com alterações não relacionadas fora dos arquivos desta onda
