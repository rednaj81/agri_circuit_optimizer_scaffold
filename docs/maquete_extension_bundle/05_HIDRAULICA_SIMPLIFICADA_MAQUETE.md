# Hidráulica simplificada da maquete — modo `bottleneck_plus_length`

## Objetivo

Substituir a lógica principal de perda fixa aditiva por uma lógica mais aderente à maquete:

- componentes como T, válvulas e reduções limitam a capacidade da rota como **gargalo**;
- o comprimento da mangueira reduz a capacidade local do ramal/tronco;
- a viabilidade da rota passa a depender da menor capacidade efetiva entre os estágios.

## Regra conceitual

### 1. Capacidade local da opção
Cada opção de ramal ou tronco deve sair do preprocessamento com uma capacidade efetiva local.

#### Passo A — gargalo estrutural
A capacidade local base da opção é:

`q_local_base = min(q_max_lpm dos componentes que formam a opção)`

Isso já representa:
- T
- válvulas
- checks
- adaptadores
- mangueira

#### Passo B — ajuste por comprimento da mangueira
Se a opção usa `L` metros de mangueira e a taxa da mangueira é `hose_loss_pct_per_m`, então:

`length_factor = max(min_length_factor, 1 - hose_loss_pct_per_m * L)`

`q_local_effective = q_local_base * length_factor`

### Observação
Esse cálculo é feito **por opção**, no preprocessamento.

## 2. Capacidade efetiva da rota
Depois de escolhidas as opções da rota:
- branch de origem
- tronco de sucção
- bomba
- medidor/bypass
- tronco de descarga
- branch de destino

A capacidade efetiva da rota fica:

`q_route_effective = min(q_effective de cada estágio selecionado)`

A rota é viável se:

`q_route_effective >= q_min_delivered_lpm`

E a folga hidráulica fica:

`hydraulic_slack_lpm = q_route_effective - q_min_delivered_lpm`

## 3. Por que esta abordagem é melhor para a maquete

### Vantagens
- mantém o modelo interpretável;
- continua compatível com MILP via preprocessamento + parâmetros;
- representa melhor a ideia de estrangulamento por bitola/componente;
- trata o comprimento da mangueira como principal fator degradante variável;
- evita a sensação de “cada componente vai tirando mais LPM de forma arbitrária”.

## 4. Papel dos componentes na maquete

### T / válvula / check / redução
- entram principalmente via `q_max_lpm`;
- não precisam acumular grande penalidade fixa adicional.

### Mangueira
- entra por comprimento;
- continua contando para BOM e volume interno;
- é o principal driver físico variável.

### Bomba
- entra via `q_max_lpm` nominal.

### Fluxômetro
- entra via `q_max_lpm` e pelas regras de dose/erro.

## 5. Compatibilidade com o modo anterior

O cenário da maquete deve usar:

`hydraulic_loss_mode: bottleneck_plus_length`

Os cenários antigos podem seguir com:

`hydraulic_loss_mode: additive_lpm`

## 6. Recomendação de implementação

### No preprocessamento
- calcular `hose_length_m` de cada branch/trunk;
- calcular `q_local_effective` da opção;
- armazenar esse valor como o `q_max_lpm` efetivo da opção gerada;
- guardar também o `q_local_base_lpm` para diagnóstico.

### No modelo
- usar o `q_max_lpm` efetivo da opção, sem reinventar a fórmula dentro do MILP;
- manter `hydraulic_slack_lpm` como relatório e critério leve de robustez.

## 7. Escopo conscientemente fora desta rodada

- curva real de bomba
- altura manométrica
- NPSH
- viscosidade
- efeito dinâmico de nível do tanque
- perda singular detalhada por cotovelo real
- dobramento físico explícito da mangueira no layout 2D

Esses itens podem virar uma rodada futura, mas não são necessários para validar a maquete.
