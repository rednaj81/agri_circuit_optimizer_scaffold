# Arquitetura-alvo

## Visão em alto nível

### Frontend
Uma interface de decisão com:
- studio visual de nós/arestas
- edição de parâmetros
- banco de componentes
- comparação de candidatos
- visualização 2D
- fila de cenários
- inspeção de cenário e execução individual

### Backend Python
Responsável por:
- API
- persistência
- gerenciamento de cenários
- fila de jobs
- integração com Julia
- export de artefatos
- autenticação/autorização futura, se necessário

### Engine Julia
Responsável por:
- montagem do problema hidráulico
- avaliação de viabilidade
- otimização / search assistido
- cálculo de métricas por rota
- cálculo de BOM, limpeza, vazão e constraints
- retorno de artefatos estruturados

## Componentes-alvo

1. **Scenario Service**
   - CRUD de cenários
   - versionamento
   - import/export tabular

2. **Node/Edge Studio**
   - edição visual
   - validações
   - salvar layout e semântica

3. **Component Catalog**
   - CRUD do catálogo
   - filtros e disponibilidade

4. **Route Service**
   - CRUD de rotas obrigatórias/opcionais
   - edge obligations
   - criticidade

5. **Run Orchestrator**
   - enfileirar jobs
   - cancelar/repetir
   - acompanhar progresso

6. **Julia Engine Adapter**
   - invocação Julia
   - isolamento do ambiente
   - coleta de logs e resultados

7. **Decision UI**
   - ranking
   - filtros
   - pesos
   - comparação
   - explicabilidade

## Restrições arquiteturais

- Julia only no caminho oficial de run
- jobs isolados por cenário/run
- resultados reproduzíveis
- cada cenário acessível individualmente
- nenhuma execução em background deve bloquear a edição ou inspeção de outros cenários
