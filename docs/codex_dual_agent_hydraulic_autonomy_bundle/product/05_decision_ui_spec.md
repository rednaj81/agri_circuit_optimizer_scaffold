# Interface de apoio à decisão

## Objetivo
Permitir a análise humana de cenários e candidatos viáveis.

## Visões mínimas

### 1. Lista de cenários
- nome
- status do último run
- data
- candidato oficial
- custo
- engine_used

### 2. Fila de processamento
- jobs em fila
- jobs em execução
- jobs finalizados
- jobs com erro
- progresso

### 3. Studio
- edição de nós e arestas
- painel de propriedades
- validações

### 4. Catálogo de candidatos
- filtros
- ranking
- viabilidade
- família topológica
- custo
- fallback
- score total e por dimensão

### 5. Comparação
- candidato oficial
- runner-up
- selecionado manualmente

### 6. Circuito
- render 2D
- destaque de rota
- componentes críticos
- gargalos
- arestas conflitantes

### 7. Explicabilidade
- por que venceu
- por que perdeu
- regras ativadas
- penalidades
- resumo em linguagem clara

## Pesos e filtros
A UI deve permitir:
- editar pesos
- reranquear
- filtrar por família, custo, fallback, score, viabilidade
- persistir estado na sessão
