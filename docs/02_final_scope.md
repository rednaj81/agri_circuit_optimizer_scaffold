# Escopo final consolidado

## Nós
- `W`: tanque de água
- `P1`, `P2`, `P3`: tanques flexíveis de produto/premix
- `M`: misturador
- `I`: incorporador
- `IR`: retorno/recirculação do incorporador
- `S`: saída externa

## Regras de negócio principais
- `P1`, `P2`, `P3` podem alternar produtos e armazenar premix.
- O incorporador recebe água, incorporação manual e deve ter recirculação.
- A saída externa idealmente pode receber qualquer origem relevante.
- Linhas e bombas podem ser compartilhadas.
- Limpeza entre operações existe com custo fixo no MVP.
- Fluxômetros são componentes funcionais, não apenas custo.
- Bombas e fluxômetros têm faixas de vazão.
- Componentes têm bitolas e perdas associadas.
- Há restrições de vazão mínima entregue e de dosagem mínima com margem de erro.

## Não objetivos do MVP
- curvas completas de bomba
- CFD
- compatibilidade química
- simultaneidade
- automação temporal detalhada
