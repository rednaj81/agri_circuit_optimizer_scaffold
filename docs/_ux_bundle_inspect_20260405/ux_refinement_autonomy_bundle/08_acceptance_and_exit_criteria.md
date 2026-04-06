# Critérios de aceite e saída

## Aceite mínimo da próxima evolução
1. Usuário consegue criar cenário no studio sem depender de edição manual crua
2. Usuário entende se o cenário está pronto para rodar
3. Fila de runs é compreensível sem abrir logs brutos
4. Candidato oficial e runner-up ficam claros
5. `technical_tie` fica explícito e permite decisão humana
6. Motivo principal de inviabilidade aparece claramente
7. A decisão final pode ser exportada sem ambiguidade
8. A navegação não parece um conjunto de telas técnicas desconexas

## Saída do ciclo autônomo
Encerrar quando ocorrer um destes casos:

### A. Sucesso
- fluxo limpo e consistente
- UX aprovada pelo auditor
- documentação atualizada
- commits por fase feitos

### B. Estagnação
- 3 ondas seguidas sem avanço relevante
- regressão
- mudanças cosméticas apenas
- pouco ganho prático

### C. Threshold
- máximo de 10 ondas
- depois 1 ciclo final de polimento e estabilização
