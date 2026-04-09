# Phase Studio Decision Simplification - Wave 1 Handoff

## Escopo executado

- Rebaixei o chrome global no `Studio` e na `Decisão` para devolver a primeira dobra ao trabalho principal.
- Fiz o canvas do `Studio` dominar a dobra inicial em Full HD com coluna principal mais larga, altura maior e menos competição visual acima do grafo.
- Condensei a leitura da `Decisão` em comparação rápida entre perfil ativo, winner, runner-up, technical tie, referência oficial e escolha manual.

## O que ficou melhor para o operador comum

- No `Studio`, o fluxo abre com canvas mais dominante, menos banner concorrente e um resumo curto do que editar agora.
- O painel lateral do `Studio` mantém seleção, ações locais, composer e leitura de suprimento no topo; métricas e saída ficaram atrás de disclosure.
- Na `Decisão`, a primeira leitura virou comparação compacta, com menos texto corrido e mais contraste imediato entre os papéis principais.

## Evidências da onda

- Código principal ajustado em `src/decision_platform/ui_dash/app.py`.
- Testes de UX/smoke atualizados em `tests/decision_platform/test_ui_smoke.py`.
- Validação executada:
  - `python -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -m "not slow"`
  - Resultado: `93 passed, 12 deselected`

## Limitações honestas

- Não gerei captura visual nesta onda porque a correção de curso proibiu gastar esforço em plumbing de bitmap/browser.
- A suíte lenta completa desses dois arquivos não foi fechada nesta sessão; a execução integral ultrapassou o tempo disponível de validação local.
- O shell global ainda existe para navegação entre espaços; a simplificação desta onda foi reduzir sua competição visual em `Studio` e `Decisão`, não removê-lo por completo.

## Próximo passo sugerido

- Fechar a próxima onda na `Decisão` aprofundando sinais de diferença entre winner e runner-up sem voltar a texto longo, ou seguir para a fase de `Runs` se o supervisor abrir essa frente.
