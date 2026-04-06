# Critérios de aceite e saída

## Aceite mínimo da próxima evolução
1. Usuário consegue criar cenário no studio sem depender de edição manual crua
2. O Studio expõe apenas entidades de negócio; nós/hubs técnicos internos não aparecem como superfície principal
3. Usuário entende se o cenário está pronto para rodar
4. Fila de runs é compreensível sem abrir logs brutos
5. Candidato oficial e runner-up ficam claros
6. `technical_tie` fica explícito e permite decisão humana
7. Motivo principal de inviabilidade aparece claramente
8. A decisão final pode ser exportada sem ambiguidade
9. A navegação não parece um conjunto de telas técnicas desconexas
10. A UI principal não depende de JSON cru ou `html.Pre` como mecanismo central de leitura
11. A visualização principal do circuito não mostra nós órfãos ou estruturas técnicas sem valor para o usuário
12. O studio oferece interação direta suficiente para parecer editor visual, não formulário técnico fragmentado

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
- UI ainda com sensação de console técnico após várias ondas
- permanência de entidades internas na superfície principal

### C. Threshold
- máximo de 10 ondas
- depois 1 ciclo final de polimento e estabilização
