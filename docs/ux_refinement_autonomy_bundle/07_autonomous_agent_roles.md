# Papéis recomendados para agentes autônomos

## Agent 1 — UX Architect
Responsável por:
- informação e navegação
- fluxo do usuário
- simplificação da jornada
- definição de padrões de interface
- critérios de aceite de UX

### Mandato
- não reabrir arquitetura
- não trocar stack
- priorizar clareza, progressão e redução de ruído
- reprovar qualquer proposta que exponha o grafo técnico interno como experiência principal
- empurrar o Studio para um modelo de negócio visual e direto
- exigir padrão de software de mercado, não de ferramenta técnica crua

## Agent 2 — Product Flow Engineer
Responsável por:
- implementar UI
- ajustar estado/sessão
- melhorar studio/runs/decisão
- conectar backend e interface
- entregar incrementos funcionais e testáveis

### Mandato
- preservar pipeline e domínio já existentes
- evitar retrabalho do motor
- focar em superfícies e fluxos
- não usar `html.Pre`/JSON cru como solução primária de interface
- esconder nós técnicos internos, hubs derivados e ruído de solver da experiência principal
- melhorar manipulação direta do canvas antes de expandir formulários

## Agent 3 — UX Auditor (gate)
Responsável por:
- medir se houve avanço real de UX
- reprovar loops sem ganho significativo
- registrar regressões, confusões e inconsistências
- exigir commits/documentação por fase

### Critério de parada
- parar após 3 ondas consecutivas sem avanço significativo
- ou no máximo 10 ondas
- depois 1 ciclo final de polimento/estabilização

### Sinais de low-value
- UI continua com sensação de console técnico
- Studio ainda expõe entidades internas
- a mudança foi cosmética, mas não melhorou a jornada
