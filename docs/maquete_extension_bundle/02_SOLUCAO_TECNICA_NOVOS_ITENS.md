# Solução técnica por novo item

## 1. Inclusão do `P4`

### O que muda
- `nodes.csv` ganha o nó `P4`.
- `routes.csv` passa a incluir rotas obrigatórias e opcionais envolvendo `P4`.
- templates de origem e destino passam a incluir `P4` em `allowed_node_ids`.
- testes de loader, cenário e end-to-end precisam validar `P4`.

### Solução técnica
- atualizar `nodes.csv`, `routes.csv`, `source_branch_templates.csv` e `destination_branch_templates.csv` do novo cenário;
- manter o contrato atual do loader, apenas com um nó a mais;
- adicionar teste que verifica que `P4` aparece como origem e como destino elegível no cenário da maquete.

---

## 2. Estoque físico da maquete

### O que muda
O cenário deixa de ser somente um exercício de topologia e passa a ser também um problema de **estoque real de montagem**.

### Solução técnica
Representar cada item de estoque como **SKU explícito em `components.csv`**:

- `pump_suction_base_g1`
- `pump_extra_g1`
- `meter_small_g1`, `meter_mid_g1`, `meter_high_g1`
- `bypass_g1`
- `solenoid_base_g1`
- `valve_extra_g1`
- `check_base_g1`
- `check_extra_g1`
- `tee_base_g1`
- `tee_extra_g1`
- `hose_g1_1m`
- `empty_slot`

O modelo deve continuar respeitando `available_qty` por SKU.

---

## 3. Estratégia para não estourar as 8 solenoides base

### Problema
Se todo ramal de origem e todo ramal de destino exigir solenoide, a arquitetura em camadas tende a consumir mais do que 8 válvulas.

### Solução técnica congelada
Usar **templates diferentes para origem e destino** no cenário da maquete:

- ramos de origem:
  - `W` protegido com válvula + antirretorno
  - `P1..P4`, `M`, `I` com válvula
- ramos de destino:
  - `P1..P4`, `M`, `I`, `IR` **sem válvula obrigatória**
  - `S` com válvula obrigatória

### Efeito esperado
- 7 válvulas nos ramos de origem (`W`, `P1`, `P2`, `P3`, `P4`, `M`, `I`)
- 1 válvula no destino `S`
- total esperado: **8 válvulas base**

Essa decisão deve ser refletida **nos dados do cenário**, não em regra hard-coded do código.

---

## 4. Mangueira modular de 1 m

### Problema
O modelo atual trabalha com opções de mangueira já discretizadas por SKU (por exemplo 5 m e 10 m). A maquete precisa de um estoque mais realista: **mangueira a granel, cortada conforme a necessidade**.

### Solução técnica
- manter um SKU base: `hose_g1_1m`;
- no preprocessamento, calcular o comprimento necessário do ramal/tronco;
- converter esse comprimento em `n` módulos de 1 m;
- armazenar `component_counts = {"hose_g1_1m": n, ...}` dentro da opção gerada;
- derivar custo, volume interno e consumo de estoque a partir de `n`.

### Regra recomendada
`hose_modules = ceil(required_hose_m / hose_module_m)`

Com `hose_module_m = 1`, isso vira arredondamento para cima em metros inteiros.

---

## 5. Cálculo geométrico do comprimento dos ramais

### Problema
Sem geometria, o cenário da maquete não testa a montagem física.

### Solução técnica
Adicionar coordenadas aos nós e aos manifolds.

Para cada ramal:
1. calcular a distância reta entre o nó e o manifold relevante;
2. multiplicar por `bend_factor`;
3. somar `connection_margin_m`;
4. aplicar mínimo de 1 m;
5. arredondar para cima em módulos de mangueira.

### Fórmula sugerida
`required_hose_m = max(minimum_branch_hose_m, euclidean_distance(node, manifold) * bend_factor + connection_margin_m)`

---

## 6. Fator de curva / folga de instalação

### Motivação
Você quer evitar que o modelo escolha comprimentos justos demais, que na prática gerariam dobras ou conexões forçadas.

### Solução técnica
Usar dois parâmetros de cenário:
- `bend_factor`
- `connection_margin_m`

### Efeito
Mesmo que a distância reta seja pequena, o modelo reservará um pouco mais de mangueira para instalação realista.

---

## 7. Conectores T como BOM real

### Problema
Os conectores T deixam de ser detalhe implícito e passam a ser estoque real da maquete.

### Solução técnica congelada
- **cada ramal de origem** consome 1 T;
- **cada ramal de destino** consome 1 T;
- **os troncos não devem consumir T** no modo da maquete.

### Justificativa
Com 7 ramos de origem e 8 de destino, o sistema usa 15 T ao todo:
- 10 base
- 5 extras

Isso casa exatamente com o estoque informado.

### Mudança de implementação necessária
O gerador de opções de tronco deve ganhar um modo em que **troncos consomem apenas mangueira**, e não conector T.

---

## 8. Bombas de sucção 300 L/min

### Solução técnica
Usar `q_max_lpm = 300` para as bombas da maquete, assumindo a simplificação combinada de tratar ml como litros no modelo.

### Observação
Essa capacidade é ampla para o cenário; o objetivo aqui não é calibrar a física da bomba real, mas manter coerência com o protótipo físico.

---

## 9. Fluxômetros

### Solução técnica
A maquete terá três medidores base:
- um pequeno
- um médio
- um alto

A lógica de V2 continua válida:
- rotas com `measurement_required = true` não podem usar bypass;
- o medidor deve respeitar dose mínima, erro máximo e faixa operacional.

### Assunção congelada
Não haverá `meter_extra` na primeira rodada da maquete.

---

## 10. Novo modo hidráulico: `bottleneck_plus_length`

### Problema
A lógica antiga de perda aditiva fixa em L/min por componente não representa bem a maquete.

### Solução técnica
No modo `bottleneck_plus_length`:
- T, válvulas e reduções atuam principalmente como **limite de capacidade (`q_max_lpm`)**;
- a mangueira atua como o principal fator dependente do comprimento;
- a capacidade efetiva do ramal/tronco já sai do preprocessamento corrigida pelo comprimento local.

### Consequência positiva
O MILP continua linear, porque o preprocessamento entrega opções já com:
- `hose_length_m`
- `component_counts`
- `q_max_lpm_effective`

---

## 11. Compatibilidade com o cenário atual

### Solução técnica
Não substituir a lógica antiga. Em vez disso:
- introduzir um `hydraulic_loss_mode` em `settings.yaml`;
- quando `hydraulic_loss_mode = additive_lpm`, manter o comportamento atual;
- quando `hydraulic_loss_mode = bottleneck_plus_length`, ativar a nova lógica da maquete.

Isso evita quebrar cenários e testes antigos.
