# Definições congeladas

Estas definições devem ser seguidas na implementação.

## 1. Filosofia geral
- não forçar topologia única;
- não tratar o problema como um solver monolítico único;
- separar:
  - geração de candidatos;
  - avaliação hidráulica;
  - ranking/decisão.

## 2. Resultado principal
O produto principal é um **catálogo de cenários viáveis** com ranking dinâmico.

## 3. Custo
O custo deve existir em pelo menos 3 níveis:
- custo de montagem / aquisição;
- custo/penalidade de fallback;
- custo operacional simplificado (ex.: limpeza).

## 4. Qualidade
Qualidade não é só viabilidade.
Exemplos:
- uma bomba ativa em sentido correto: melhor score;
- fluxo reverso por bomba desligada: permitido, mas pior score;
- medição dentro da faixa de confiabilidade do fluxômetro: bônus;
- série de bombas para uma rota: penalidade ou menor nota;
- menor limpeza por rota: melhor nota;
- caminho mais simples: melhor operabilidade.

## 5. Fluxômetros
Cada fluxômetro deve ter:
- faixa hard mínima (`hard_min_lpm`);
- faixa hard máxima (`hard_max_lpm`);
- faixa de confiabilidade mínima (`confidence_min_lpm`);
- faixa de confiabilidade máxima (`confidence_max_lpm`).

A rota:
- pode estar na faixa hard e ainda ser viável;
- mas só recebe bônus de qualidade se cair dentro da faixa de confiabilidade.

## 6. Fallback
Deve haver componentes fallback, pelo menos:
- 1 bomba fallback;
- 1 fluxômetro fallback.

Exemplo desejado:
- hard range `0 -> 99999`;
- custo alto;
- score de qualidade baixo;
- usados para manter sempre uma solução possível quando o bloqueio for apenas de catálogo/range.

## 7. Limpeza por rota
A plataforma deve calcular uma métrica de limpeza por rota, ao menos simplificada:
- volume interno estimado do caminho;
- penalidade extra se houver série de bombas ou componentes com retenção;
- possibilidade de usar isso em score e filtros.

## 8. Roteamento operacional
O modelo deve encontrar **caminho hidráulico possível**, não impor caminho fixo.
Uma topologia instalada pode ter:
- várias bombas;
- vários fluxômetros;
- vários loops;
mas a operação da rota escolhe:
- caminho ativo;
- bombas ativas;
- medidor considerado para leitura.

## 9. Interface
A UI deve permitir:
- edição/importação de tabelas;
- execução de geração/avaliação;
- filtro por viabilidade/custo/qualidade;
- pesos dinâmicos;
- ranking;
- renderização 2D.

## 10. Política de robustez
Viabilidade vem antes de score.
Score vem antes de “ótimo final”.
Decisão humana assistida é parte do produto.
