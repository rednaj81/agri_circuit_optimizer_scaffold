# Testes de aceite recomendados para a maquete

## Grupo A — contrato e carregamento

### A1. Loader aceita o cenário `maquete_core`
Validar que:
- todos os arquivos do cenário existem;
- `P4` está presente;
- as colunas extras de geometria e mangueira não quebram o loader;
- `I -> IR` continua obrigatório;
- nada entra em `W` e nada sai de `S`.

### A2. Resumo do cenário
Validar que `scenario_summary` reconhece o novo cenário e retorna contagens compatíveis.

## Grupo B — preprocessamento geométrico

### B1. Branches recebem comprimento derivado
Para um ou mais nós, validar que:
- `hose_length_m` foi calculado;
- `hose_modules_used` é inteiro;
- o mínimo de 1 m foi aplicado.

### B2. Troncos não consomem T no modo da maquete
Validar que:
- `tee` é consumido por ramos;
- troncos não consomem conector quando `hydraulic_loss_mode = bottleneck_plus_length` no cenário da maquete.

### B3. Consumo total de mangueira
Validar que o preprocessamento computa consumo coerente de mangueira por opção e que o modelo consegue consolidar isso na BOM.

## Grupo C — cenário end-to-end

### C1. `maquete_core` resolve end-to-end
Validar que:
- todas as rotas obrigatórias são atendidas;
- `I -> IR` existe e é servida;
- rotas com medição obrigatória não usam bypass;
- vazão mínima é respeitada.

### C2. Sem `pump_extra`
No cenário principal, validar que a solução não usa `pump_extra`.

### C3. Sem `valve_extra`
No cenário principal, validar que a solução não usa `valve_extra`.

### C4. Uso de `tee_extra`
Validar que:
- a solução usa `tee_extra` apenas se necessário;
- no layout sugerido, o uso total de T é consistente com o número de ramos selecionados.

### C5. Limite de mangueira
Validar que:
- `hose_total_used_m <= 20`.

## Grupo D — hidráulica da maquete

### D1. Sensibilidade a comprimento
Criar uma variante do cenário com manifolds mais distantes e validar que:
- a folga hidráulica piora;
- ou a solução consome mais mangueira;
- ou a rota fica inviável.

### D2. Gargalo por componente
Criar um cenário em que o `tee` tenha `q_max_lpm` menor e validar que:
- o gargalo apareça no relatório hidráulico.

### D3. Medidor inadequado por vazão/dose
Criar um cenário em que um medidor pequeno seja insuficiente e validar que:
- o modelo escolha outro medidor;
- ou declare inviabilidade se não houver opção compatível.

## Grupo E — regressão

Rodar todos os testes anteriores do projeto e garantir que:
- cenários antigos continuam funcionando;
- o modo antigo permanece disponível;
- o fallback enumerativo continua coerente com o Pyomo quando este estiver disponível.
