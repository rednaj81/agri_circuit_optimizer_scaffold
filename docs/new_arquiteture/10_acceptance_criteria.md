# Critérios de aceite

## Aceite mínimo do backend
1. Carregar cenário da maquete por tabelas.
2. Gerar topologias candidatas em pelo menos 3 famílias.
3. Chamar engine Julia e receber métricas.
4. Persistir catálogo de soluções.
5. Calcular score por perfil de peso.

## Aceite mínimo da UI
1. Editar catálogo de componentes.
2. Editar requisitos de rota.
3. Rodar geração/avaliação.
4. Filtrar soluções viáveis.
5. Ajustar pesos e ver ranking mudar.
6. Clicar numa solução e visualizar o circuito.
7. Exportar BOM e relatório.

## Aceite mínimo do cenário da maquete
1. Existir cenário `maquete_v2` nesta nova arquitetura.
2. Ter fluxômetros com hard range e confidence range.
3. Ter bomba fallback e medidor fallback.
4. Exibir limpeza por rota.
5. Exibir score por qualidade e custo.

## Aceite mínimo de robustez
1. Separar viabilidade de score.
2. Não depender de uma única família topológica.
3. Permitir comparação entre soluções.
4. Documentar claramente limitações remanescentes.
