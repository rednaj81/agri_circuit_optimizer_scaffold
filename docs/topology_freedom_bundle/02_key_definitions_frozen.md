# 02. Definições importantes congeladas

Estas definições devem ser tratadas pelo Codex como congeladas para esta rodada, salvo necessidade técnica extrema.

## 2.1 Não adicionar novos tipos de válvula
- continuar usando apenas os tipos já existentes de solenoide
- não introduzir válvula 3 vias
- não introduzir válvula "mágica" de comutação
- se um controle funcional mais rico for necessário, ele deve ser modelado como composição de arestas e estados operacionais, não como novo tipo de componente

## 2.2 Separar topologia instalada de operação
A grande mudança conceitual desta rodada é:

### Topologia instalada
O que existe fisicamente:
- arestas
- mangueiras
- válvulas
- bombas
- fluxômetros
- T's
- bypasses

### Operação por rota
O que fica ativo em uma transferência específica:
- quais arestas conduzem
- qual bomba está energizada
- qual fluxômetro é o ponto de leitura válido
- quais válvulas/taps ficam abertas
- quais caminhos ficam explicitamente fechados ou inativos

## 2.3 Seletividade é propriedade do caminho ativo
Na estrela endurecida, a seletividade foi modelada como:
- um ramo aberto de sucção
- um ramo aberto de descarga

Isso continua válido para a família `star_manifolds`.

Mas para a família `bus_with_pump_islands`, a seletividade deve ser redefinida como:

> existe um subgrafo/caminho ativo para a rota A -> B que não cria origem alternativa, destino alternativo, loop indesejado ou bifurcação de descarga relevante.

## 2.4 Uma rota pode atravessar arestas onde existem bombas ou fluxômetros desligados
Nem toda bomba instalada participa da rota.
Nem todo fluxômetro instalado participa da leitura da rota.

Portanto:
- uma topologia pode ter 3 bombas instaladas e só 1 bomba ativa em uma rota
- uma topologia pode ter 3 fluxômetros instalados e só 1 fluxômetro válido para leitura em uma rota
- o modelo não deve inferir automaticamente que todo componente instalado em um caminho "está valendo" operacionalmente

## 2.5 Não forçar i/ir como driver principal da topologia
Recirculação/agitação local (`I -> IR`) pode ser tratada em classe de serviço separada da arquitetura core.
Ela não deve distorcer a síntese principal se puder ser atendida por uma bomba dedicada ou subcircuito local.

## 2.6 Preservar compatibilidade com o que já existe
- manter `star_manifolds` operacional
- não quebrar loaders atuais sem necessidade
- preferir extensão compatível ao invés de substituição abrupta

## 2.7 Primeira meta: validar topologias fixas
Antes de tentar uma síntese livre total em grafo geral, o primeiro objetivo deve ser:
- representar topologias fixas candidatas
- validar se atendem as rotas
- comparar BOM, mangueira, válvulas, medição e operabilidade

Só depois disso vale expandir para síntese livre entre famílias.