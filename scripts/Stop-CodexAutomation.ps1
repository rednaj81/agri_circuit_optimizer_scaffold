param(
    [string]$TaskName = "CodexDualAgentSupervisor",
    [switch]$RemoveTask
)

$ErrorActionPreference = "SilentlyContinue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiRoot = Join-Path $repoRoot "docs\\codex_dual_agent_runtime\\api"
$serverStatePath = Join-Path $apiRoot "server_state.json"
$processStatePath = Join-Path $apiRoot "process_state.json"

function Stop-IfRunning {
    param([int]$Pid)
    if ($Pid -gt 0) {
        Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
    }
}

if (Test-Path -LiteralPath $processStatePath) {
    try {
        $processState = Get-Content -LiteralPath $processStatePath -Raw | ConvertFrom-Json
        if ($processState.pid) {
            Stop-IfRunning -Pid ([int]$processState.pid)
        }
    }
    catch {
    }
}

if (Test-Path -LiteralPath $serverStatePath) {
    try {
        $serverState = Get-Content -LiteralPath $serverStatePath -Raw | ConvertFrom-Json
        if ($serverState.pid) {
            Stop-IfRunning -Pid ([int]$serverState.pid)
        }
    }
    catch {
    }
}

$targets = @(
    'run_codex_supervisor_api.ps1',
    'run_codex_dual_agent_loop.ps1',
    'Invoke-CodexSupervisorWatchdog.ps1',
    'Start-CodexSupervisorWatchdogLoop.ps1',
    'Invoke-CodexStrategicSupervisor.ps1',
    'Start-CodexStrategicSupervisorLoop.ps1',
    'Wait-CodexSupervisorState.ps1'
)

try {
    Get-CimInstance Win32_Process -Filter "Name = 'pwsh.exe' OR Name = 'powershell.exe'" | ForEach-Object {
        $cmd = [string]$_.CommandLine
        foreach ($target in $targets) {
            if ($cmd -like "*$target*") {
                Stop-IfRunning -Pid ([int]$_.ProcessId)
                break
            }
        }
    }
}
catch {
}

if ($RemoveTask) {
    & schtasks.exe /Delete /TN $TaskName /F | Out-Null
}

Write-Host "Codex automation cleanup requested."
