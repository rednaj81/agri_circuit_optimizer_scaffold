# Phase UX Refinement Wave 8 Handoff

## Escopo executado

- Endureci o fluxo alternativo de captura para validar sanidade visual automaticamente.
- Mantive o mesmo caminho reproduzível da onda anterior, mas agora com duas tentativas explícitas de leitura de pixels:
  - `ImageGrab` sobre a região real da janela
  - `PrintWindow` como fallback
- Passei a reprovar automaticamente bitmaps vazios, brancos ou uniformes antes de aceitar a captura como evidência.

## Mudanças principais

- `scripts/capture_edge_window.py`
  - adiciona tentativa `image_grab` para ler pixels reais da tela
  - mantém `print_window` como fallback
  - calcula métricas objetivas de sanidade visual (`unique_colors`, `stddev`, `max_channel_spread`)
  - grava assessment em JSON
  - falha fechado quando nenhuma tentativa gera imagem visualmente útil
- `scripts/Capture-UxRefinementStudio.ps1`
  - passa a gerar `output/playwright/studio-fullhd-wave8.png`
  - passa a gerar `output/playwright/studio-fullhd-wave8-assessment.json`
  - mantém o comando único e reproduzível para subir o Studio e executar a captura

## Validação executada

- `powershell -ExecutionPolicy Bypass -File scripts/Capture-UxRefinementStudio.ps1 -Port 8060 -OutputPath output/playwright/studio-fullhd-wave8.png`

## Resultado

- `output/playwright/studio-fullhd-wave8.png` foi gerado em `1920x1080`
- o próprio fluxo rejeitou a imagem como inválida
- `output/playwright/studio-fullhd-wave8-assessment.json` registrou:
  - `image_grab` falhou com `OSError: screen grab failed`
  - `print_window` gerou imagem com:
    - `unique_colors = 1`
    - `stddev = 0.0`
    - `max_channel_spread = 0`
    - `visually_useful = false`

## Impacto no gate

- O gate visual continua **aberto**.
- A diferença agora é que o fluxo de captura não confunde mais “arquivo existe” com “evidência válida”.
- O bloqueio residual ficou isolado em um único ponto técnico verificável:
  - a sessão Windows atual não entrega pixels úteis nem por `ImageGrab` nem por `PrintWindow` para a janela Chromium do Studio

## Evidência gerada

- `output/playwright/studio-fullhd-wave8.png`
  - bitmap real gerado, porém inválido como evidência
- `output/playwright/studio-fullhd-wave8-assessment.json`
  - sanidade visual objetiva da captura

## Próximo passo sugerido

- Tratar a fase como bloqueada por leitura de pixels da sessão gráfica atual, e não por inexistência de fluxo de captura.
- Qualquer próxima tentativa precisa mudar o mecanismo de captura da sessão Windows em si, não mais o plumbing do Studio.
