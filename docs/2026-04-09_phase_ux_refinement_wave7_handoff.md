# Phase UX Refinement Wave 7 Handoff

## Objetivo da onda

Encurtar a lateral do Studio de forma real depois da estabilização do canvas, deixando a primeira dobra mais contextual e rebaixando o restante do conteúdo para fallback secundário.

## Implementação

- simplificado `render_studio_workspace_panel` em `src/decision_platform/ui_dash/app.py` para abrir a lateral com um único bloco dominante de contexto, reunindo foco atual, sinal de readiness e rota/composer em vez de repetir essas mensagens em faixas paralelas
- `studio-workspace-supply-strip`, `studio-business-flow-panel` e `studio-context-detailed-panels` passaram a iniciar fechados, deixando cadeia detalhada, readiness completo, foco estendido e conectividade como camada secundária real
- mantidas as ações diretas do canvas na primeira dobra, mas sem recolocar duplicação de readiness crítico ou cadeia de suprimento como blocos sempre visíveis
- removido vazamento de `route:R...` do texto dominante da sidebar ao usar a leitura de conexão em foco

## Validação

- `PYTHONPATH='src;.' .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave7-full-rerun`
- resultado: `121 passed in 408.49s (0:06:48)`

## Evidência de apoio

- `output/playwright/wave7-studio-sidebar-state.json`
  - confirma `studio-context-detailed-panels`, `studio-workspace-supply-strip`, `studio-route-editor-shell` e `studio-business-flow-panel` fechados no estado inicial
  - registra o texto do novo bloco `studio-workspace-context-panel` sem ids crus como leitura principal

## Limitações

- a onda não altera o modelo funcional do Studio; o ganho é estrutural e ergonômico na lateral
- o contexto detalhado continua existindo inteiro sob disclosure, então ainda há bastante conteúdo avançado disponível quando o usuário expande essa trilha
- o worktree do repositório segue com alterações não relacionadas fora dos arquivos desta wave
