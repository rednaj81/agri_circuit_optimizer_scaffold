# Pacote de documentação — extensão da maquete

Este pacote foi preparado para ser **descompactado dentro de `docs/`** do projeto `agri_circuit_optimizer_scaffold`.

Sugestão de uso:
1. copie este diretório para `docs/maquete_extension_bundle/`;
2. leia `00_INDEX.md`;
3. use `prompts/PROMPT_CODEX_MAQUETE_COMPLETO.md` como prompt real para implementação;
4. use `prompts/PROMPT_CODEX_MAQUETE_DISPARO_CURTO.md` como mensagem curta de abertura do chat no Codex;
5. use `tasks/` como plano de execução incremental.

## Objetivo do pacote

Expandir o escopo para a **validação física da maquete**, cobrindo:
- inclusão do `P4`;
- estoque real da maquete;
- mangueira modular de 1 m, com total disponível de 20 m;
- cálculo geométrico simplificado de comprimento de ramais;
- fator de curva / folga de instalação;
- conectores T como estoque real da BOM;
- modo hidráulico simplificado do tipo **gargalo + comprimento**;
- cenário de teste `maquete_core`;
- testes de aceite específicos da maquete.

## Estrutura

- `00_INDEX.md` — índice do pacote
- `01_CENARIO_MAQUETE_ESCOPO.md` — escopo congelado da maquete
- `02_SOLUCAO_TECNICA_NOVOS_ITENS.md` — como atuar em cada novo item
- `03_EVOLUCAO_DO_MODELO.md` — mudanças recomendadas no código
- `04_DADOS_E_CONTRATO_MAQUETE.md` — extensões do contrato de dados
- `05_HIDRAULICA_SIMPLIFICADA_MAQUETE.md` — regra hidráulica recomendada
- `06_CENARIO_TESTE_MAQUETE_CORE.md` — especificação do cenário de validação
- `07_TESTES_DE_ACEITE_MAQUETE.md` — testes recomendados
- `08_RESULTADO_ESPERADO_DA_MAQUETE.md` — leitura esperada da solução
- `prompts/` — prompt completo + prompt curto para Codex
- `tasks/` — tarefas estruturadas
- `examples/` — exemplos de arquivos de cenário para a maquete
