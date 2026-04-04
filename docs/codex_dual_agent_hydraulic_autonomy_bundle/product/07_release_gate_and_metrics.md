# Gate de release e métricas

## Gate mínimo para liberar versão de teste humano
- engine oficial Julia funcionando
- UI sobe e opera
- cenário da maquete editável
- queue/background run funcional
- candidato oficial explicável
- artefatos completos
- sem regressões relevantes nos testes críticos

## Matriz de validação da fase 0

Registro de saída humano e auditável:

- `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json`
- `docs/codex_dual_agent_runtime/phase_0_exit.md`

Decisão de stop da phase_0:

- a `phase_0` está encerrada
- não abrir novas ondas funcionais dentro desta fase
- qualquer nova evolução deve abrir a próxima fase e preservar a política `Julia-only` já validada

Fluxo canônico:
- contrato declarativo: `scripts/decision_platform_runtime_validation_profiles.json`
- script-base: `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1`
- profile `official_preflight`: `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official -OfficialPreflight`
- profile `official`: `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official`
- profile `diagnostic`: `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe`
- profile `diagnostic_comparison`: `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison`
- aliases opcionais quando `make` existir no host: `decision-platform-validate-official`, `decision-platform-validate-diagnostic`, `decision-platform-validate-diagnostic-comparison`
- fonte de verdade: `summary.json` sempre, `engine_comparison.json` apenas quando a comparação diagnóstica for solicitada
- o profile `official_preflight` é apenas triagem operacional de ambiente e política; ele checa override proibido, `julia --version`, cenário oficial e o inventário `Project.toml`/`Manifest.toml` do projeto Julia local, mas não executa o pipeline completo e não substitui o gate oficial
- o validador remove o diretório de saída antes da run para evitar artefato stale
- o validador cruza `summary.json` com os artefatos principais do candidato oficial antes de declarar sucesso
- o validador falha se o modo pedido não bater com o perfil declarativo e com a política exportada pelo pipeline
- o validador atualiza `docs/codex_dual_agent_runtime/phase_0_validation_manifest.json` com o último resultado bruto por profile
- o detalhamento humano aprovado das garantias, limites e evidências desta fase fica centralizado em `docs/codex_dual_agent_runtime/phase_0_exit.md`

### 0. Preflight oficial rápido
- objetivo: detectar cedo erro de ambiente, override proibido, Julia/WaterModels indisponível ou configuração oficial inválida antes do gate completo
- comando canônico:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official -OfficialPreflight`
- profile declarativo:
  `official_preflight`
- regra:
  não tratar este preflight como validação oficial suficiente
- evidência esperada:
  apenas relatório do script com triagem de `julia_available`, `watermodels_available`, política, configuração do cenário e inventário do projeto Julia local
- rejeições obrigatórias do preflight:
  `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE` ativo, Julia indisponível, WaterModels indisponível ou política oficial inválida
- observação:
  a validação oficial da fase 0 continua sendo apenas o profile `official` com Julia real e execução completa do pipeline

### 1. Gate oficial Julia-only
- objetivo: provar que o caminho oficial continua fail-closed e exporta o candidato oficial sem fallback implícito
- comando canônico:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode official`
- profile declarativo:
  `official`
- alias opcional:
  `make decision-platform-validate-official`
- comando de teste:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_runs_with_real_julia_and_exports_final_artifacts -q --basetemp tests/_tmp/pytest-basetemp-julia-gate`
- regra: não usar `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE`
- evidência mínima em artefato:
  `summary.json` com `execution_mode=official`, `official_gate_valid=true`, timestamps e duração
- rejeições obrigatórias do validador:
  `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE` ativo, `official_gate_valid=false` ou presença indevida de `engine_comparison.json`

### 2. Aceite diagnóstico lean
- objetivo: validar exports centrais, coerência do candidato oficial e métricas de rota sem depender do runtime Julia real
- comando canônico:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe`
- profile declarativo:
  `diagnostic`
- alias opcional:
  `make decision-platform-validate-diagnostic`
- comando de teste:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q --basetemp tests/_tmp/pytest-basetemp-accept`
- ambiente:
  `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1`
- janela operacional observada nesta máquina: cerca de `40 s`
- regra: a saída diagnóstica não pode gerar `engine_comparison.json` por padrão
- evidência mínima em artefato:
  `summary.json` com `execution_mode=diagnostic`, `official_gate_valid=false` e menção explícita ao override
- validações obrigatórias do validador:
  `policy_mode=diagnostic_override_probe_disabled`, `real_julia_probe_disabled=true`, artefatos principais coerentes com `summary.json` e `engine_comparison.json` ausente quando a comparação não foi pedida

### 3. Comparação diagnóstica explícita
- objetivo: provar que a comparação Julia vs Python continua disponível apenas por opt-in explícito
- comando canônico:
  `pwsh -NoProfile -File scripts/run_decision_platform_runtime_validation.ps1 -Mode diagnostic -DisableRealJuliaProbe -IncludeEngineComparison`
- profile declarativo:
  `diagnostic_comparison`
- alias opcional:
  `make decision-platform-validate-diagnostic-comparison`
- comando de teste:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_diagnostic_engine_comparison_remains_explicit_opt_in -q --basetemp tests/_tmp/pytest-basetemp-accept-diag`
- ambiente:
  `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1`
- janela operacional observada nesta máquina: cerca de `70 s`
- regra: `engine_comparison.json` e `engine_comparison_candidates.csv` só aparecem nesta trilha
- evidência mínima em artefato:
  `engine_comparison.json` com `execution_policy` e `runtime` marcando o override e a invalidez para o gate oficial
- validações obrigatórias do validador:
  `engine_comparison.json` e `engine_comparison_candidates.csv` presentes e coerentes com a política diagnóstica exportada

### 4. Suite de suporte
- smoke rápido:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m fast -q --basetemp tests/_tmp/pytest-basetemp-fast`
- UI diagnóstica:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_ui_smoke.py -m "not requires_julia" -q --basetemp tests/_tmp/pytest-basetemp-ui`
- gate Julia:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform -m requires_julia -q --basetemp tests/_tmp/pytest-basetemp-julia`

## Ruído operacional aceito
- `PytestCacheWarning` não deve aparecer na execução padrão documentada
- diretórios temporários devem ficar sob `tests/_tmp/`
- qualquer uso de `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE` deve ficar restrito às trilhas diagnósticas
- se o runtime oficial estiver sem Julia real, o comportamento esperado continua sendo fail-closed
- qualquer artefato gerado com override diagnóstico precisa declarar explicitamente que não representa validação oficial

## Métricas mínimas
- taxa de runs concluídos
- tempo médio por run
- taxa de cenários viáveis
- família vencedora mais frequente
- uso de fallback
- score médio por perfil
- regressões detectadas pelo auditor
