# Stop rules

O loop principal deve parar quando:

1. houver 3 avaliações consecutivas do Auditor em:
   - low_significance
   - no_progress
   - regression

ou

2. houver 10 ondas completas

Depois disso deve rodar exatamente mais 1 onda de:
- polimento
- estabilização
- correção de erros
- fechamento para teste humano

## Baselines seladas

Quando uma fase estiver explicitamente selada como baseline histórica:

- não abrir novas ondas incrementais de rotina nessa fase
- não usar a fase selada como trilha paralela de manutenção de baixo valor
- permitir exceção apenas para correção crítica de integridade de evidências
- redirecionar a continuidade funcional e operacional normal para a fase ativa

Aplicação atual:

- `phase_1` e `phase_2` são baselines seladas
- a continuidade funcional ativa deve seguir somente em `phase_3`
- qualquer exceção em `phase_1` deve ser tratada como recuperação extraordinária de evidências, não como nova onda incremental
