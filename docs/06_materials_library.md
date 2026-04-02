# Biblioteca de materiais

A biblioteca de materiais é a base para o solver compor soluções factíveis.

## Categorias esperadas
- `pump`
- `meter`
- `valve`
- `check_valve`
- `hose`
- `connector`
- `adaptor`

## Requisitos de representação

Cada item deve carregar, quando aplicável:
- custo
- disponibilidade
- classe de bitola
- faixa de vazão
- perda equivalente
- volume interno
- atributos funcionais

## Observação de modelagem

O preprocessador pode combinar vários itens atômicos em uma opção de estágio.
Exemplo:
- ramal de origem = válvula + check + mangueira + adaptador
