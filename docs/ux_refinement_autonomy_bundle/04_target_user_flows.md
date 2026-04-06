# Fluxos-alvo do usuário

## Fluxo 1 — criar novo cenário
1. Criar projeto
2. Criar cenário
3. Abrir studio
4. Criar nós
5. Criar arestas
6. Definir rotas obrigatórias
7. Validar conectividade / completude
8. Salvar revisão
9. Rodar cenário

## Fluxo 2 — acompanhar execução
1. Abrir fila/runs
2. Ver status:
   - queued
   - running
   - succeeded
   - failed
   - cancelled
3. Entrar em um run
4. Acompanhar progresso/log resumido
5. Abrir resultados

## Fluxo 3 — decidir melhor alternativa
1. Abrir resultados do run
2. Ver candidato oficial
3. Ver runner-up
4. Se houver `technical_tie`, visualizar isso claramente
5. Comparar alternativas
6. Filtrar catálogo
7. Escolher opção final
8. Exportar decisão

## Fluxo 4 — revisar cenário inviável
1. Abrir run falho ou catálogo
2. Ver motivo principal de inviabilidade
3. Destacar conectividade/rotas falhas
4. Voltar ao studio
5. Corrigir cenário
6. Criar nova revisão
7. Rodar novamente
