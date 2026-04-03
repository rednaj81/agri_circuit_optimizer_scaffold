# 05. Mudanças no modelo matemático e no solver

## 5.1 Mudança central

Sair de:
- "uma rota usa exatamente um slot de bomba e um slot de medidor na superestrutura estrela"

Para:
- "uma rota precisa encontrar um caminho seletivo e operável dentro de uma topologia instalada"

## 5.2 Novas variáveis conceituais

Para cada rota `r` e aresta `e`:
- `edge_active[r,e] ∈ {0,1}`

Para cada rota `r` e bomba `p`:
- `pump_active[r,p] ∈ {0,1}`

Para cada rota `r` e medidor `m`:
- `meter_reading_active[r,m] ∈ {0,1}`

Para cada aresta `e`:
- `edge_installed[e] ∈ {0,1}`

Opcionalmente:
- `route_feasible[r]`
- `route_uses_topology_family[r,f]`

## 5.3 Restrições mínimas novas

### A. Ativação por instalação
`edge_active[r,e] <= edge_installed[e]`

### B. Caminho da rota
As arestas ativas de `r` devem formar um caminho de `source(r)` até `sink(r)`.

No primeiro passo, pode-se começar com:
- conservação de fluxo em grafo dirigido
- caminho simples ou quase simples
- 1 unidade de fluxo de origem para destino

### C. Bomba por rota
Regra recomendada para a primeira implementação:
- `sum pump_active[r,*] <= max_active_pumps_per_route(r)`
- padrão: `<= 1`

### D. Medição por rota
Se `measurement_required(r)=true`:
- `sum meter_reading_active[r,*] = 1`
- o medidor de leitura precisa estar em uma aresta ativa do caminho

### E. Seleção de leitura
Outros medidores no caminho podem estar instalados, mas não contam para leitura se estiverem marcados como inativos para a rota.

### F. Grupos de conflito
Para cada grupo de conflito `g`:
- `sum edge_active[r,e in g] <= 1`
ou outra forma apropriada, conforme a natureza do grupo

### G. Seletividade
Em vez de contar ramos de sucção/descarga, impor que:
- o caminho ativo não induza múltiplos destinos de descarga
- não haja bifurcação operacional
- arestas marcadas como mutuamente conflitantes não operem em paralelo

## 5.4 Hidráulica simplificada

Manter modelo simples, mas transferi-lo para arestas:
- capacidade máxima por aresta
- capacidade de bomba ativa
- gargalo de caminho
- perda por comprimento de mangueira
- folga hidráulica da rota

Sugestão:
- capacidade efetiva do caminho = mínimo entre capacidades relevantes do caminho e capacidade da bomba ativa ajustada
- rota viável se `flow_required <= effective_capacity`

## 5.5 Objetivo

O objetivo deve ser particionado em duas partes:

### Custo estrutural
- componentes instalados
- mangueira
- T's/conectores
- válvulas
- bombas
- fluxômetros

### Desempenho operacional
- cobertura de rotas obrigatórias
- cobertura de rotas opcionais
- robustez hidráulica
- seletividade válida

## 5.6 Estratégia de implementação recomendada

### Primeiro passo
Criar um **validador/solver de topologia fixa**:
- dado um grafo instalado, ele diz se cada rota é viável

### Segundo passo
Criar um comparador de famílias:
- mesma demanda
- duas topologias candidatas
- comparar BOM, mangueira, válvulas, bombas, medição e viabilidade

### Terceiro passo
Só depois pensar em síntese livre combinando arestas candidatas