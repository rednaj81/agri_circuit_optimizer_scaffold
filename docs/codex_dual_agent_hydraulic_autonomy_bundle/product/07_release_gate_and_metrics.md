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

### 1. Gate oficial Julia-only
- objetivo: provar que o caminho oficial continua fail-closed e exporta o candidato oficial sem fallback implícito
- comando de pipeline:
  `python -m decision_platform.api.run_pipeline --scenario data/decision_platform/maquete_v2 --output-dir data/output/decision_platform/maquete_v2`
- comando de teste:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_runs_with_real_julia_and_exports_final_artifacts -q --basetemp tests/_tmp/pytest-basetemp-julia-gate`
- regra: não usar `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE`

### 2. Aceite diagnóstico lean
- objetivo: validar exports centrais, coerência do candidato oficial e métricas de rota sem depender do runtime Julia real
- comando:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_pipeline_exports_and_route_metrics -q --basetemp tests/_tmp/pytest-basetemp-accept`
- ambiente:
  `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1`
- janela operacional desta máquina: abaixo de `30 s`
- regra: a saída diagnóstica não pode gerar `engine_comparison.json` por padrão

### 3. Comparação diagnóstica explícita
- objetivo: provar que a comparação Julia vs Python continua disponível apenas por opt-in explícito
- comando:
  `.\.venv\Scripts\python.exe -m pytest tests\decision_platform\test_maquete_v2_acceptance.py::test_maquete_v2_diagnostic_engine_comparison_remains_explicit_opt_in -q --basetemp tests/_tmp/pytest-basetemp-accept-diag`
- ambiente:
  `DECISION_PLATFORM_DISABLE_REAL_JULIA_PROBE=1`
- janela operacional desta máquina: abaixo de `45 s`
- regra: `engine_comparison.json` e `engine_comparison_candidates.csv` só aparecem nesta trilha

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

## Métricas mínimas
- taxa de runs concluídos
- tempo médio por run
- taxa de cenários viáveis
- família vencedora mais frequente
- uso de fallback
- score médio por perfil
- regressões detectadas pelo auditor
