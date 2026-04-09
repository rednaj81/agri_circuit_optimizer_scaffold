# UX Phase 2 Exit

## Decisão

- `ux_phase_2` está pronta para transição para `ux_phase_3`.

## Critérios verificados

- `business graph only`: atendido.
  - O canvas principal continua ocultando hubs, centrais, nós derivados e outros internos técnicos.
- `route-first suficiente`: atendido.
  - O Studio entra por foco de trecho/rota e mantém composer, criação de rota e particularidades locais no fluxo principal ou em fallback curto.
- `direct canvas editing para tarefas comuns`: atendido.
  - O operador consegue mover foco, inverter trecho, criar rota do trecho e corrigir medição direta sem depender do workbench avançado como caminho padrão.
- `readiness mais legível`: atendido.
  - O primeiro fold fecha em estado atual, próxima ação e passagem para Runs, com affordances curtas para ações bloqueadas ou disponíveis.
- `ausência de internos técnicos na superfície primária`: atendido.
  - Não houve reintrodução de IDs crus ou payload técnico como leitura principal.
- `canvas estabilizado`: atendido.
  - Limites de zoom, sensibilidade, foco de edge e posições estáveis permanecem protegidos por teste.
- `lateral curta e disclosures fechados por padrão`: atendido.
  - O conteúdo secundário continua recolhido no estado inicial.

## Evidência de validação

- Suite executada:

```powershell
$env:PYTHONPATH='src;.'; .\.venv\Scripts\python.exe -m pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q -p no:cacheprovider --basetemp tests/_tmp/pytest-basetemp-ux-wave10-full
```

- Resultado:
  - `124 passed in 326.06s (0:05:26)`

## Riscos residuais

- A evidência continua majoritariamente estrutural; ainda não há cobertura forte de automação visual live do Studio em navegação real.
- O contexto detalhado do Studio segue amplo quando expandido, embora esteja corretamente relegado a fallback.
- A transição para Runs ainda depende da fase seguinte para lapidar queue/execution UX; esta saída cobre apenas o fechamento da superfície de Studio.

## Próxima frente sugerida

- Migrar para `ux_phase_3` com foco em Runs queue e execution UX, preservando o Studio como superfície estabilizada.

