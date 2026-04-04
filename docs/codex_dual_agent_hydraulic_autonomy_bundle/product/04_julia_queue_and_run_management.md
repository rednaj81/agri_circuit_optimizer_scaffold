# Execução em Julia, fila e gestão de runs

## Objetivo
Executar cenários em background, com isolamento e acompanhamento.

## Requisitos
- run oficial apenas por Julia
- sem fallback no caminho oficial
- comparação Julia vs Python apenas por opt-in explícito
- `python_emulated_julia` apenas para auditoria, comparação ou testes
- cada cenário pode ter vários runs
- cada run tem status próprio
- runs simultâneos não se bloqueiam mutuamente, salvo locks intencionais
- logs por run
- artefatos por run
- cancelamento e re-run

## Estados de run
- queued
- preparing
- running
- exporting
- completed
- failed
- canceled

## Entidades mínimas
- scenario
- scenario_version
- run_job
- run_event
- artifact
- queue_worker

## Telemetria mínima
- engine_requested
- engine_used
- engine_mode
- julia_available
- watermodels_available
- started_at
- finished_at
- duration_s
- failure_reason
- failure_stacktrace_excerpt

## Regra crítica
Se Julia falhar no caminho oficial:
- falhar fechado
- não cair silenciosamente para Python

Se for necessário rodar comparação diagnóstica:
- habilitar explicitamente a trilha de comparação
- registrar que `python_emulated_julia` não compõe o candidato oficial
