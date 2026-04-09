# Phase UX Refinement Wave 6 Handoff

## Objetivo da onda

Fechar uma rodada curta de correções perceptíveis de ergonomia no Studio e na Decisão sem reabrir arquitetura: estabilizar zoom e foco do canvas, aliviar a primeira dobra da sidebar e cortar redundância relevante da leitura de decisão.

## Implementação

- estabilizado o `node-studio-cytoscape` em `src/decision_platform/ui_dash/app.py` com zoom menos agressivo, faixa de zoom mais curta, `autoRefreshLayout=False`, `boxSelectionEnabled=False` e altura menor para reduzir salto perceptível ao interagir com arestas
- reduzida a densidade da primeira dobra do Studio: a faixa de ações rápidas ficou menor e ações destrutivas/menos frequentes foram empurradas para `Ajustes finos do foco`
- o editor de rota saiu da dobra principal e passou para `studio-route-editor-shell`, abrindo automaticamente só quando há composer ativo
- removida a duplicação de resumo na Decisão: `decision-summary-panel-extended` deixou de repetir `render_decision_summary_panel` e passou a renderizar uma justificativa consolidada com foco em racional, revisão pendente e exportação

## Validação

- `PYTHONPATH='src;.' .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave6-full`
- resultado: `121 passed in 353.64s (0:05:53)`

## Evidência de apoio

- `output/playwright/wave6-ui-ergonomics-check.json`
  - registra a configuração final do canvas
  - confirma o `studio-route-editor-shell` fechado no estado inicial
  - confirma o texto consolidado da justificativa da Decisão

## Limitações

- a onda não gerou screenshot literal; a evidência ficou como verificação estruturada do layout e dos parâmetros finais
- a estabilidade de clique em aresta foi endurecida por configuração de canvas e coberta por teste de posições estáveis, não por automação visual de navegação real
- o worktree do repositório continua com alterações não relacionadas fora dos arquivos desta wave
