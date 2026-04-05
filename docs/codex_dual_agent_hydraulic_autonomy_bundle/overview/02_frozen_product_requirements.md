# Requisitos congelados do produto

## Requisitos obrigatórios

1. **Engine Julia only**
   - nenhuma execução produtiva com fallback Python
   - fallback só é aceitável para desenvolvimento local explícito
   - em produção ou cenários oficiais, se Julia falhar, deve falhar fechado

2. **Studio visual**
   - criação/edição de nós
   - criação/edição de arestas
   - criação de grupos de conflito
   - criação de pontos de bomba, medidor e válvula
   - definição de coordenadas 2D

3. **Banco de componentes**
   - catálogo editável
   - estoque
   - custo
   - ranges hidráulicos
   - faixas de confiança de fluxômetros
   - perdas em forward/reverse
   - hold-up de limpeza
   - tags qualitativas

4. **Rotas obrigatórias**
   - definidas por cenário
   - associadas a origem/destino
   - com requisitos de vazão, medição, dosagem e criticidade

5. **Fila de execução**
   - cenários enfileirados
   - execução em background
   - sem interferência entre jobs
   - visualização de status, logs e artefatos por cenário

6. **Auditoria forte**
   - cada execução deve ter:
     - engine_used
     - status
     - motivo de falha
     - artefatos exportados
     - logs
     - tempo de execução

7. **Catálogo de soluções**
   - lista de candidatos viáveis e inviáveis
   - ranking por perfis de peso
   - comparação lado a lado
   - export de BOM, score, render e explicação do vencedor

## Critérios de qualidade

- UX simples e amigável
- dados editáveis por tabela
- decisões explicáveis
- sem mascarar fallback
- evidência clara do uso real de Julia
- estabilidade antes de abrir novas funcionalidades grandes
