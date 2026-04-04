[CmdletBinding()]
param(
    [int]$RefreshSeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeRoot = Join-Path $repoRoot 'docs\codex_dual_agent_runtime'
$supervisorPath = Join-Path $runtimeRoot 'supervisor_state.json'
$loopStatePath = Join-Path $runtimeRoot 'loop_state.json'

while ($true) {
    Clear-Host
    Write-Host "Codex Dual Agent Supervisor"
    Write-Host "repo-root: $repoRoot"
    Write-Host "timestamp: $(Get-Date -Format o)"
    Write-Host ""

    if (Test-Path -LiteralPath $supervisorPath) {
        $supervisor = Get-Content -LiteralPath $supervisorPath -Raw | ConvertFrom-Json
        Write-Host "phase: $($supervisor.phase_id)"
        Write-Host "backend: $($supervisor.backend)"
        Write-Host "active-wave: $($supervisor.active_wave_index)"
        Write-Host "active-role: $($supervisor.active_role)"
        Write-Host "waves-completed: $($supervisor.waves_completed)"
        Write-Host "stop-reason: $($supervisor.stop_reason)"
        Write-Host "updated-at: $($supervisor.last_updated_at)"
        Write-Host ""
        Write-Host "sessions:"
        foreach ($property in $supervisor.agent_sessions.PSObject.Properties) {
            $session = $property.Value
            Write-Host ("- {0}: session_id={1} last_wave={2} status={3}" -f $property.Name, $session.session_id, $session.last_wave_index, $session.last_status)
        }
    }
    else {
        Write-Host "supervisor_state.json ainda nao encontrado."
    }

    if (Test-Path -LiteralPath $loopStatePath) {
        $loopState = Get-Content -LiteralPath $loopStatePath -Raw | ConvertFrom-Json
        $lastWave = $loopState.waves | Select-Object -Last 1
        if ($lastWave) {
            Write-Host ""
            Write-Host "last-wave:"
            Write-Host "- index: $($lastWave.wave_index)"
            Write-Host "- phase: $($lastWave.phase_id)"
            Write-Host "- auditor-verdict: $($lastWave.auditor_verdict)"
            Write-Host "- run-root: $($lastWave.run_root)"
        }
    }

    Start-Sleep -Seconds $RefreshSeconds
}
