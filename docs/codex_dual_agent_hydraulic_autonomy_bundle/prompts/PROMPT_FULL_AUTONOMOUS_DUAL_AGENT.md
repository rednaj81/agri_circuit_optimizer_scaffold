Base desta execução:
- use o branch atual do projeto
- siga AGENTS.md
- siga docs/codex_dual_agent_hydraulic_autonomy_bundle/
- trate a decision platform como runtime principal do futuro produto
- preserve o baseline legado só como referência histórica

Quero que você conduza a evolução com:
- 2 agentes principais:
  - Architect
  - Developer
- 1 agente Auditor como gate obrigatório

Loop:
Architect -> Developer -> Auditor -> Architect

Política:
- máximo de 10 ondas
- parada se o Auditor marcar por 3 ondas consecutivas:
  - low_significance
  - no_progress
  - regression
- depois disso, rodar exatamente mais 1 onda final de:
  - polimento
  - estabilização
  - correção de erros
  - fechamento para teste humano
- commit obrigatório ao final de cada onda
- handoff obrigatório ao final de cada onda

Objetivo do produto:
elevar a aplicação a nível profissional de plataforma hidráulica com:
- studio visual de criação de nós e arestas
- banco de componentes
- rotas obrigatórias e arestas obrigatórias criadas no studio
- execução apenas por Julia, sem fallback no caminho oficial
- processamento em background com fila de cenários
- cenários abríveis individualmente
- jobs rodando sem interferência entre si
- interface de apoio à decisão com filtros, pesos, ranking e visualização 2D do circuito

Congele estas prioridades:
1. Julia only no caminho oficial
2. background queue por cenário/run
3. studio visual de nós e arestas
4. banco de componentes
5. rotas obrigatórias e edge obligations
6. decisão humana assistida
7. explicabilidade do vencedor
8. estabilidade antes de abrir novas frentes

Forma de trabalhar:
- o Architect define a meta da onda, critérios de aceite e arquivos-alvo
- o Developer implementa, testa, documenta e commita
- o Auditor julga significância, regressão e aderência
- se o Auditor pedir correção imediata dentro da mesma onda, faça a correção antes do commit, se o desvio for pequeno
- se o desvio for estrutural, devolva para a próxima onda

O que NÃO fazer:
- não mascarar fallback
- não afirmar validações não executadas
- não abrir arquitetura inteira de uma vez sem critérios de fase
- não ficar em ciclos infinitos sem handoff/commit
- não ignorar a regra de parada

Critérios de sucesso do programa:
- depois das ondas, eu devo conseguir abrir a UI
- modelar cenários no studio
- editar banco de componentes
- definir rotas obrigatórias
- enfileirar runs
- acompanhar runs em background
- abrir um cenário individual
- ver ranking de soluções viáveis
- ver explicação do candidato oficial
- comparar candidatos
- exportar artefatos
- confiar que o caminho oficial é Julia-only

Use os arquivos deste bundle como fonte de verdade:
- overview/
- product/
- automation/
- data_samples/

Comece com:
1. auditoria curta do estado atual do branch
2. identificação da fase atual
3. definição da Onda 1
4. execução do loop conforme as regras
