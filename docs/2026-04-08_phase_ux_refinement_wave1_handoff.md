# Phase UX Refinement Wave 1 Handoff

## Escopo executado

- Corrigi a base compatível do Dash usada nos testes locais para que o Studio volte a montar o shell completo, registrar callbacks duplicados e expor os componentes da primeira dobra sem depender do stack visual instalado.
- Ajustei a leitura do Studio para manter a linguagem de negócio no foco local da conexão, incluindo referências explícitas a `Tanque de água` e `Saída principal` quando a direção do trecho viola as regras congeladas.
- Preservei o round-trip da seleção de arestas no fluxo principal: a projeção do canvas continua escondendo helpers técnicos, mas o resumo local agora mantém a conexão realmente editada como foco durante a rodada de callback.
- Normalizei o `callback_map` para os testes estruturais/smoke encontrarem callbacks por `input_id` e por `output_prefix`, tanto no modo compatível quanto no stack completo.

## Mudanças principais

- `src/decision_platform/ui_dash/_compat.py`
  - amplia o fallback de componentes para cobrir `Location`, `Details`, `Summary`, `A`, `Span`, `H4`, listas e labels usados pela shell atual;
  - preserva `children` declarados por keyword;
  - expõe `props` como atributos do componente;
  - registra `callback_map` com chaves únicas mesmo quando há `allow_duplicate` nos mesmos outputs.
- `src/decision_platform/ui_dash/app.py`
  - remove o fallback textual `Rota {id}` na humanização de blockers sem contexto, mantendo o copy esperado nos painéis de readiness;
  - explicita labels de negócio no guidance local do canvas para conexões inválidas envolvendo `W` e `S`;
  - separa seleção de aresta em foco da seleção projetada no canvas, preservando o round-trip de edição estrutural sem recolocar arestas internas na superfície principal;
  - normaliza o `callback_map` ao final de `build_app` para estabilizar smoke/structure tests em ambos os modos de execução.

## Validação executada

- `PYTHONPATH=. pytest tests/decision_platform/test_ui_smoke.py tests/decision_platform/test_studio_structure.py -q`

Resultado:

- `96 passed, 1 skipped in 368.24s`

## Artefatos

- suíte alvo verde para smoke e estrutura do Studio;
- handoff desta onda atualizado em `docs/2026-04-08_phase_ux_refinement_wave1_handoff.md`.

## Limites honestos

- Esta onda ficou concentrada em restaurar corretude e estabilidade do Studio; não avancei em Runs ou Decisão além do necessário para os testes do shell.
- Não produzi evidência Playwright nova; a evidência desta onda é a suíte alvo verde.
- Não toquei no pipeline Julia, no contrato de dados canônico nem na fila além do acoplamento indireto exercitado pelos testes.

## Próximo passo sugerido

- Com a base do Studio verde novamente, a próxima onda pode atacar UX de fila/Runs ou perfis de decisão sem continuar gastando tempo em plumbing de callbacks ou captura.
