# Phase UX Refinement Wave 3 Handoff

## Escopo executado

- Consolidei o fluxo route-first do Studio com um composer local explícito no primeiro fold, sem depender de combinação implícita de cliques para criar a rota principal.
- Adicionei preview visível da rota em preparação tanto no painel local quanto no canvas, mantendo a superfície principal no grafo de negócio.
- Trouxe para o composer as particularidades preventivas mais críticas para readiness: intenção, vazão mínima, dosagem mínima, medição direta e observação visível.
- Mantive o workbench avançado como fallback, não como caminho padrão, e preservei a ocultação de hubs/nós internos na leitura primária.

## Mudanças principais

- `src/decision_platform/ui_dash/app.py`
  - adiciona estado explícito do composer (`studio-route-composer-state`) com normalização própria;
  - adiciona preview de rota em preparação com leitura de negócio e sinal preventivo de readiness;
  - transforma o fluxo local em passos explícitos: definir origem, definir destino, carregar trecho selecionado, confirmar rota e limpar composer;
  - renderiza preview visual no canvas via aresta temporária `route-composer-preview` quando origem e destino do composer estão visíveis;
  - confirma a criação da rota aplicando já no fluxo local intenção e particularidades preventivas relevantes.
- `tests/decision_platform/test_ui_smoke.py`
  - cobre o novo composer local e a confirmação da rota com preview revisado;
  - valida a presença da nova UI do composer na primeira dobra do Studio.
- `tests/decision_platform/test_studio_structure.py`
  - valida a estrutura do composer e a projeção da aresta de preview no canvas primário.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q`

Resultado:

- `98 passed, 1 skipped in 385.50s`

## Limites honestos

- O composer local ficou mais claro e robusto, mas ainda não oferece um editor visual avançado de múltiplos trechos; ele continua focado em uma rota de negócio por vez.
- Mantive callbacks legados ligados a `studio-route-draft-source-id` como trilha residual para não reabrir a arquitetura nesta onda, embora o caminho principal agora seja o composer explícito.
- Não gerei evidência bitmap/browser nesta onda; a evidência principal segue sendo a suíte alvo verde e o handoff atualizado.

## Próximo passo sugerido

- A próxima onda do Studio pode trabalhar a prevenção de erro e a legibilidade do impacto operacional da rota no readiness final, sem abandonar o composer local recém estabilizado.
