# Automação do loop de agentes

Este diretório define um loop controlado para:

- Architect
- Developer
- Auditor

## Padrão operacional

O backend principal segue o mesmo padrão do runner externo já usado em outros repositórios:

- `codex exec` como motor real
- `CODEX_HOME` isolado por run
- runner PowerShell temporário
- execução iniciada a partir de um shell externo ao Codex
- logs, `last-message` e estado persistidos em `docs/codex_dual_agent_runtime/`
- sessões persistentes independentes por papel (`architect`, `developer`, `auditor`)
- handoff explícito entre papéis por onda

Isso evita depender de `openai-agents` + `codex mcp-server` dentro da sessão atual.

## Backends disponíveis

### `codex-exec-external`

Backend real.

Requer:

- `codex` no `PATH`
- `pwsh` ou `powershell` no `PATH`
- um `CODEX_HOME` já autenticado localmente
- execução a partir de um PowerShell externo ao Codex

Arquivos de configuração:

- `automation/execution-profiles.json`
- `automation/execution-profiles.local.json` opcional

### `scaffold`

Backend estrutural.

Serve para:

- validar política de ondas
- validar persistência de `loop_state.json`
- testar `phase_0`, `max_waves` e a onda final de estabilização

Não serve para:

- validar conversa real com modelo
- validar edição real por agentes

## Scripts

- [run_codex_dual_agent_loop.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\run_codex_dual_agent_loop.ps1)
- [run_codex_supervisor_api.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\run_codex_supervisor_api.ps1)
- [Ensure-CodexSupervisorApi.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Ensure-CodexSupervisorApi.ps1)
- [Install-CodexSupervisorTask.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Install-CodexSupervisorTask.ps1)
- [Invoke-CodexSupervisorWatchdog.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Invoke-CodexSupervisorWatchdog.ps1)
- [Start-CodexSupervisorWatchdogLoop.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Start-CodexSupervisorWatchdogLoop.ps1)
- [Get-CodexExecutionProfile.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Get-CodexExecutionProfile.ps1)
- [Test-CodexExternalRunner.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Test-CodexExternalRunner.ps1)
- [Test-CodexSupervisorApi.ps1](C:\d\dev\agri_circuit_optimizer_scaffold\scripts\Test-CodexSupervisorApi.ps1)

## Comandos

Preflight do backend real:

```powershell
.\scripts\Test-CodexExternalRunner.ps1 -PreflightOnly
.\scripts\run_codex_dual_agent_loop.ps1 -Phase phase_0 -Backend codex-exec-external -PreflightOnly
```

Dry run estrutural:

```powershell
.\scripts\run_codex_dual_agent_loop.ps1 -Phase phase_0 -Backend scaffold -MaxWaves 2
```

Teste mínimo do runner externo:

```powershell
.\scripts\Test-CodexExternalRunner.ps1 -Role architect -RunProbe
```

Primeira onda real:

```powershell
.\scripts\run_codex_dual_agent_loop.ps1 -Phase phase_0 -Backend codex-exec-external -Model gpt-5.4 -ReasoningEffort high -MaxWaves 1
```

Supervisor em tempo real:

```powershell
.\scripts\Watch-CodexDualAgentLoop.ps1
```

Subir a API supervisora:

```powershell
.\scripts\run_codex_supervisor_api.ps1
```

Garantir start por healthcheck:

```powershell
.\scripts\Ensure-CodexSupervisorApi.ps1
```

Instalar task do Windows para checagem a cada minuto:

```powershell
.\scripts\Install-CodexSupervisorTask.ps1
```

Rodar o watchdog manualmente:

```powershell
.\scripts\Invoke-CodexSupervisorWatchdog.ps1
```

Rodar o watchdog em loop local:

```powershell
.\scripts\Start-CodexSupervisorWatchdogLoop.ps1
```

Endpoints via cliente PowerShell:

```powershell
.\scripts\Test-CodexSupervisorApi.ps1 -Action health
.\scripts\Test-CodexSupervisorApi.ps1 -Action preflight
.\scripts\Test-CodexSupervisorApi.ps1 -Action start -MaxWaves 10 -Model gpt-5.4 -ReasoningEffort high
.\scripts\Test-CodexSupervisorApi.ps1 -Action state
.\scripts\Test-CodexSupervisorApi.ps1 -Action logs
.\scripts\Test-CodexSupervisorApi.ps1 -Action policy
.\scripts\Test-CodexSupervisorApi.ps1 -Action desired-run
.\scripts\Test-CodexSupervisorApi.ps1 -Action set-policy -MaxWaves 14 -ConsecutiveLowValueStop 4
.\scripts\Test-CodexSupervisorApi.ps1 -Action set-desired-run -MaxWaves 14 -Model gpt-5.4 -ReasoningEffort high
.\scripts\Test-CodexSupervisorApi.ps1 -Action clear-policy
.\scripts\Test-CodexSupervisorApi.ps1 -Action stop
```

## Saídas

Arquivos gerados:

- `docs/codex_dual_agent_runtime/preflight.json`
- `docs/codex_dual_agent_runtime/loop_state.json`
- `docs/codex_dual_agent_runtime/supervisor_state.json`
- `docs/codex_dual_agent_runtime/agent_sessions.json`
- `docs/codex_dual_agent_runtime/probe/`
- `docs/codex_dual_agent_runtime/runs/`
- `docs/codex_dual_agent_runtime/api/server_state.json`
- `docs/codex_dual_agent_runtime/api/process_state.json`
- `docs/codex_dual_agent_runtime/api/desired_run.json`
- `docs/codex_dual_agent_runtime/api/server.stdout.log`
- `docs/codex_dual_agent_runtime/api/server.stderr.log`
- `docs/codex_dual_agent_runtime/api/watchdog.log`
- `docs/codex_dual_agent_runtime/wave_policy.override.json`

Cada onda grava:

- `runs/wave-XX/architect/`
- `runs/wave-XX/developer/`
- `runs/wave-XX/auditor/`
- `runs/wave-XX/handoffs/`

Cada papel mantém sua própria sessão persistente em:

- `docs/codex_dual_agent_runtime/agents/architect/`
- `docs/codex_dual_agent_runtime/agents/developer/`
- `docs/codex_dual_agent_runtime/agents/auditor/`

## Observações

- O probe real deve ser feito em shell externo; dentro do Codex desktop pode haver bloqueio de subprocesso aninhado.
- O runner falha fechado. Não há fallback implícito de `codex-exec-external` para `scaffold`.
- `execution-profiles.local.json` não é versionado por padrão; use o `.example` como base se quiser override local.
- O loop foi desenhado para manter conversas separadas por papel e compartilhar apenas o handoff estruturado entre elas, sempre sobre o mesmo codebase local.
