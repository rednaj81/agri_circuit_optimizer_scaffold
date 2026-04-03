# Guia de edição manual de tabelas

## Princípios
- prefira CSV para tabelas editadas manualmente;
- use YAML só para regras aninhadas;
- toda coluna nova deve ser documentada;
- nunca use textos ambíguos para ranges e flags.

## Dicas

### Bombas
Preencher:
- hard range
- confidence range (se aplicável)
- perda direta
- perda reversa desligada
- custo
- fallback ou não

### Fluxômetros
Preencher:
- faixa hard
- faixa de confiabilidade
- custo
- fallback ou não

### Regras de qualidade
- manter uma regra por linha;
- usar descrições claras;
- não misturar regra dura com regra de score.

### Pesos
- manter perfis prontos;
- a UI depois permitirá ajuste fino.

## Versionamento
Sempre versionar:
- mudanças em dados;
- mudanças em regras de score;
- mudanças em pesos;
- mudanças em layout.
