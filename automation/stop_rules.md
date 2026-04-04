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
