# 03. Arquitetura-alvo — modo multitopologia

## 3.1 Princípio

O projeto deve passar a suportar múltiplas famílias topológicas.

## 3.2 Famílias mínimas a suportar

### A. star_manifolds
A família já existente:
- ramos de sucção
- coletor de sucção
- banco de bombas
- banco de medidores
- coletor de descarga
- ramos de descarga

### B. bus_with_pump_islands
Nova família:
- barramento principal
- taps/ramais dos tanques conectando ao barramento
- ilhas de bomba + medição em arestas específicas
- loops superiores/laterais opcionais
- possibilidade de caminhos alternativos entre trechos do barramento

## 3.3 Estratégia recomendada

### Etapa 1
Criar um **topology engine** que aceite uma topologia fixa descrita por arquivos de arestas e regras.

### Etapa 2
Implementar ao menos duas famílias:
- `star_manifolds`
- `bus_with_pump_islands`

### Etapa 3
Adicionar comparação entre famílias em um mesmo cenário.

## 3.4 Motor conceitual

O motor passa a operar em duas camadas.

### Camada estrutural
Seleciona ou carrega:
- nós
- arestas candidatas
- componentes instalados por aresta
- quantidade total de mangueira
- componentes usados

### Camada operacional
Para cada rota:
- escolhe um conjunto de arestas ativas
- escolhe uma bomba ativa (ou nenhuma, se a rota permitir)
- escolhe um fluxômetro de leitura ativo (ou nenhum, se a rota não exigir)
- verifica seletividade
- verifica medição
- verifica hidráulica simplificada

## 3.5 Regra de seletividade por caminho

Para cada rota `r = A -> B`:
- deve existir um caminho ativo dirigido entre `A` e `B`
- o caminho não pode criar:
  - sucção alternativa relevante
  - destino alternativo relevante
  - descarga simultânea em múltiplos tanques
  - loop ativo não intencional
- arestas fora do caminho ativo podem existir fisicamente, mas devem estar operativamente inativas para aquela rota, salvo se forem neutras e explicitamente permitidas

## 3.6 Grupos de conflito

Introduzir `group_id` / `conflict_group_id` para arestas mutuamente exclusivas por rota.

Exemplos:
- dois atalhos alternativos entre os mesmos pontos
- duas direções possíveis para a mesma bomba física
- dois fluxômetros alternativos para a mesma leitura
- dois taps que não podem operar juntos naquela família topológica

## 3.7 Topologia fixa vs síntese livre

### Prioridade desta rodada
- validar topologias fixas candidatas
- comparar famílias

### Não é prioridade ainda
- síntese livre sobre supergrafo totalmente aberto com todos os arcos possíveis