# 2026-04-03 — Fail Closed, Quality Rules e Bridge Julia

## Contexto

A plataforma `decision_platform` já existia em paralelo ao baseline legado, mas ainda tinha quatro gaps relevantes:

- o bridge podia cair silenciosamente em emulação Python
- `quality_rules.csv` ainda não dirigia o score de fato
- a seleção de componentes era quase puramente heurística por ordenação fixa
- o gerador topológico crescia rápido demais quando o cenário pedia muitas gerações

O cenário `data/decision_platform/maquete_v2/` já declarava:

- `hydraulic_engine.primary: watermodels_jl`
- `hydraulic_engine.fallback: none`

Logo, o comportamento anterior era incorreto.

## Decisões

### 1. O bridge agora respeita estritamente o contrato do cenário

Foi introduzido `fail closed`:

- se o cenário pede `watermodels_jl` com `fallback: none`, a execução falha de forma explícita
- se o cenário permite `python_emulated_julia`, a queda para emulação fica registrada no resultado

Metadados exportados:

- `engine_requested`
- `engine_used`
- `engine_mode`
- `julia_available`
- `watermodels_available`
- `engine_warning`

### 2. Julia executável foi detectado, mas o stack Julia ainda depende de ativação externa

Nesta máquina o `julia` foi instalado via `juliaup`, mas surgiram dois bloqueios ambientais:

- o alias `julia.exe` da Store não funciona bem no sandbox, então o projeto passou a procurar o binário real do `juliaup`
- a instalação de pacotes Julia (`WaterModels`, `JuMP`, `HiGHS`) falhou localmente por problemas de TLS/credenciais e permissões no depot/registry

Isso significa:

- Julia real está parcialmente ativado
- o bridge já está pronto para usar o caminho real
- mas `WaterModels` ainda não ficou disponível localmente nesta sessão

### 3. `quality_rules.csv` agora dirige o score

As regras da tabela passaram a ser aplicadas depois da avaliação hidráulica bruta, em camada separada do engine.

Isso foi intencional por dois motivos:

- o mesmo conjunto de regras serve tanto para engine Julia real quanto para fallback Python
- o score deixa de depender de hardcodes espalhados pelo motor

Novos campos:

- `quality_score_breakdown`
- `quality_flags`
- `rules_triggered`

### 4. A seleção de componentes foi melhorada sem virar solver interno

O instalador passou a usar um ranking por categoria baseado em:

- cobertura de vazão
- faixa de confiança para medidores
- custo
- qualidade base
- perdas e hold-up de limpeza
- uso de fallback apenas quando necessário

Também foi adicionado:

- `selection_log` por candidato
- `selection_log` por link

### 5. A exploração topológica ficou mais fiel ao cenário e ainda executável

O gerador agora lê de fato:

- `population_size`
- `generations`
- `keep_top_n_per_family`
- `allow_family_hopping`

Mas a fronteira por geração é podada de forma determinística para evitar explosão combinatória. Isso preserva reprodutibilidade e mantém o custo computacional aceitável.

## Trade-offs

- O lado Julia ainda não pôde ser validado com `WaterModels` ativo nesta máquina.
- O script Julia foi enriquecido e já usa `JuMP`, `HiGHS` e `WaterModels` no entrypoint, mas a fidelidade do modelo nativo Julia ainda precisa de validação com os pacotes realmente instalados.
- A UI ficou muito mais útil como ferramenta de decisão, porém o stack Dash real ainda não pôde ser instalado localmente por bloqueio do `pip`.

## Estado operacional após esta rodada

- `maquete_v2` original: falha fechada corretamente
- cópia com `fallback: python_emulated_julia`: roda e exporta catálogo
- `tests/decision_platform`: passando

## Próximos passos

1. Concluir a ativação de `WaterModels/JuMP/HiGHS` fora das restrições deste sandbox.
2. Validar `engine_used = watermodels_jl` em execução real.
3. Refinar o engine Julia para reduzir a diferença entre avaliação nativa e fallback Python.
4. Instalar o stack Dash real e validar callbacks interativos no navegador.
