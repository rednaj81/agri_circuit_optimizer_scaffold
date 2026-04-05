# Codex dual-agent autonomy bundle

Este pacote foi feito para ser descompactado em `docs/` do repositório, criando:

`docs/codex_dual_agent_hydraulic_autonomy_bundle/`

## Objetivo

Definir um sistema de evolução autônoma com:

- 2 agentes principais do Codex:
  - `Architect`
  - `Developer`
- 1 agente de gate/revisão:
  - `Auditor`
- automação de ondas de desenvolvimento com:
  - fases definidas
  - commits por etapa
  - parada por baixa evolução
  - máximo de 10 ondas
  - 1 onda final de polimento/estabilização

## Resultado-alvo do produto

Evoluir a aplicação para uma plataforma profissional de engenharia hidráulica com:

- editor visual de nós e arestas (studio)
- banco de componentes
- definição visual de rotas obrigatórias
- execução apenas por Julia, sem fallback
- processamento em background com fila de cenários
- cenários isolados, abríveis individualmente
- interface de apoio à decisão com filtros, pesos e visualização 2D
- ranking de soluções viáveis por custo, qualidade, vazão, resiliência e outros critérios

## Estrutura do pacote

- `overview/` visão geral, requisitos e arquitetura-alvo
- `product/` especificações do produto
- `agents/` definições dos agentes
- `automation/` política de ondas, stop rules e orquestração
- `templates/` arquivos para copiar para o projeto (`AGENTS.md`, `.codex/agents`, `.codex/skills`)
- `prompts/` prompt completo e prompt curto para disparo
- `data_samples/` tabelas de exemplo para o cenário da maquete

## Como usar

1. Crie/entre no branch de trabalho.
2. Descompacte este bundle dentro de `docs/`.
3. Copie o conteúdo de `templates/root_AGENTS.md` para o `AGENTS.md` do repositório, adaptando se necessário.
4. Copie `templates/.codex/agents/` para `.codex/agents/` no repositório.
5. Opcionalmente copie `templates/.codex/skills/` para `.codex/skills/`.
6. Use primeiro `prompts/PROMPT_SHORT_BOOTSTRAP_FOR_CODEX.md`.
7. Se necessário, em seguida use `prompts/PROMPT_FULL_AUTONOMOUS_DUAL_AGENT.md`.
8. O orquestrador proposto fica em `automation/codex_dual_agent_loop.py`.

## Observações importantes

- O loop principal é `Architect -> Developer -> Auditor -> Architect`.
- O `Auditor` é um gate obrigatório porque sua regra de parada depende dele.
- O ponto de parada é:
  - 3 ondas consecutivas classificadas pelo `Auditor` como:
    - `no_progress`
    - `regression`
    - `low_significance`
  - ou 10 ondas totais
- Quando o loop principal para, roda-se exatamente mais 1 onda de:
  - polimento
  - estabilização
  - tratamento de erros
  - fechamento para teste humano
