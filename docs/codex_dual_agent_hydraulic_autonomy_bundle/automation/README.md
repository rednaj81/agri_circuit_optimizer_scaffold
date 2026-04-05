# Automação do loop de agentes

Este diretório define um loop controlado para Codex com:
- Architect
- Developer
- Auditor

## Loop

1. Architect lê estado atual e define a onda.
2. Developer implementa a onda.
3. Auditor avalia a onda.
4. Se continuar, volta ao Architect.

## Política
- máximo de 10 ondas
- parada por 3 avaliações consecutivas sem avanço relevante
- 1 onda final de polimento/estabilização

## Implementação proposta
Use Codex via MCP server e Agents SDK para orquestrar as interações.
O arquivo `codex_dual_agent_loop.py` é um esqueleto de automação local para isso.
