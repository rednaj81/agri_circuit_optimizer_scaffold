# 06. Plano de execução técnica para o Codex

## Bloco 1 — Infraestrutura multitopologia
1. adicionar infraestrutura para `topology_family`
2. aceitar uma família nova `bus_with_pump_islands`
3. criar loader para `edges.csv` e `topology_rules.yaml`
4. manter compatibilidade com `star_manifolds`

## Bloco 2 — Representação operacional por rota
1. criar payload por rota baseado em arestas
2. construir validador de caminho por rota
3. implementar conservação de fluxo / caminho dirigido
4. implementar seleção de bomba ativa e medidor de leitura

## Bloco 3 — Seletividade por caminho
1. substituir ou complementar a regra atual de seletividade
2. criar grupos de conflito
3. garantir que ramais/caminhos alternativos incompatíveis não fiquem ativos simultaneamente
4. tratar vazamento de seletividade como inviabilidade

## Bloco 4 — Família `bus_with_pump_islands`
1. representar a topologia manual do usuário em `edges.csv`
2. incluir barramento principal
3. incluir loops superiores/laterais
4. incluir ilhas de bomba/medição
5. incluir taps valvulados para os tanques

## Bloco 5 — Cenários de comparação
1. `maquete_core_star` ou manter `maquete_core` como referência da estrela
2. `maquete_bus_manual` com a topologia manual do usuário
3. opcionalmente um `maquete_bus_relaxed_ir` separando `I -> IR` como serviço

## Bloco 6 — Relatórios
Relatórios devem mostrar:
- família topológica usada
- arestas instaladas
- arestas ativas por rota
- bomba ativa por rota
- medidor de leitura por rota
- conflitos detectados
- gargalo do caminho
- BOM total
- BOM por família
- comparação entre arquiteturas

## Bloco 7 — Regressão
Não quebrar:
- example
- maquete_core
- V2/V3 atuais da estrela