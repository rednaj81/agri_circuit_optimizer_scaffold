# Handoff operacional para o Codex

## Sequência de entrega
1. carregar dados
2. validar cenário
3. gerar opções por estágio
4. podar opções dominadas
5. implementar V1
6. implementar V2
7. implementar V3
8. gerar relatórios
9. fechar testes de aceite

## Recomendação
O agente deve implementar o runner primeiro em modo `--dry-run`, validando:
- leitura
- resumo do cenário
- estatísticas básicas

Só depois deve começar a construir o modelo matemático.
