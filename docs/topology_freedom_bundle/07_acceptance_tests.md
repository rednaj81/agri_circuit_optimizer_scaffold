# 07. Testes e critérios de aceite

## 7.1 Testes mínimos novos

### T1 — loader multitopologia
- carrega `edges.csv`
- carrega `topology_rules.yaml`
- valida campos obrigatórios
- valida topologia por família

### T2 — validador de caminho em topologia fixa
Dado um grafo instalado:
- encontra caminho A -> B
- respeita direção
- respeita grupos de conflito
- escolhe bomba ativa válida
- escolhe medidor de leitura válido

### T3 — bus_with_pump_islands manual
Cenário com a topologia manual desenhada pelo usuário deve:
- carregar
- validar
- gerar relatório de operabilidade por rota

### T4 — comparação entre famílias
Mesmo conjunto de rotas:
- `star_manifolds`
- `bus_with_pump_islands`
Relatório deve mostrar diferenças de:
- válvulas
- T's
- mangueira
- bombas
- fluxômetros
- rotas atendidas
- rotas obrigatórias atendidas

### T5 — medição por rota em caminho multi-ilha
Uma rota que passa por mais de um fluxômetro instalado deve:
- escolher exatamente um ponto de leitura
- não falhar só porque outros fluxômetros estão no caminho mas inativos para leitura

### T6 — bomba instalada mas inativa
Uma rota que passe por trecho onde exista uma bomba instalada porém desligada deve:
- ser permitida, se a família topológica disser que isso é válido
- ou ser rejeitada, se a regra da família disser que não é válido
Essa diferença deve ser parametrizada em `topology_rules.yaml`

### T7 — serviço separado
Se `I -> IR` estiver em grupo `service`:
- o core não deve ficar inviável apenas por isso
- o relatório deve separar atendimento de rotas `core` e `service`

## 7.2 Critérios de aceite

A rodada só deve ser considerada pronta quando:
1. `star_manifolds` continuar funcionando
2. `bus_with_pump_islands` estiver implementada e validável
3. existir comparação entre as duas famílias
4. o cenário manual do usuário puder ser testado explicitamente
5. relatórios mostrarem caminho ativo por rota
6. testes passarem