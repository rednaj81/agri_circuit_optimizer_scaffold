param(
    [string]$TaskName = "CodexDualAgentSupervisor",
    [switch]$RemoveTask
)

$ErrorActionPreference = "SilentlyContinue"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiRoot = Join-Path $repoRoot "docs\\codex_dual_agent_runtime\\api"
$serverStatePath = Join-Path $apiRoot "server_state.json"
$processStatePath = Join-Path $apiRoot "process_state.json"
$desiredRunPath = Join-Path $apiRoot "desired_run.json"

function Stop-IfRunning {
    param([int]$Pid)
    if ($Pid -gt 0) {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            & taskkill /PID $Pid /T /F | Out-Null
        }
        else {
            Stop-Process -Id $Pid -Force -ErrorAction SilentlyContinue
        }
    }
}

function Stop-MatchingPythonProcesses {
    param([string]$Pattern)
    try {
        Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | ForEach-Object {
            $cmd = [string]$_.CommandLine
            if ($cmd -like "*$Pattern*") {
                Stop-IfRunning -Pid ([int]$_.ProcessId)
            }
        }
    }
    catch {
    }
}

function Disable-DesiredRun {
    if (-not (Test-Path -LiteralPath $desiredRunPath)) {
        return
    }
    try {
        $desiredRun = Get-Content -LiteralPath $desiredRunPath -Raw | ConvertFrom-Json
        if (-not $desiredRun) {
            return
        }
        $desiredRun.active = $false
        $desiredRun.updated_at = [DateTime]::UtcNow.ToString("o")
        $desiredRun | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $desiredRunPath -Encoding utf8
    }
    catch {
    }
}

Disable-DesiredRun

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
    'Invoke-UxRefinementStrategicSupervisor.ps1',
    'Start-UxRefinementStrategicSupervisorLoop.ps1',
    'Prepare-UxRefinementAutonomy.ps1',
    'Start-UxRefinementAutonomy.ps1',
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

Stop-MatchingPythonProcesses -Pattern 'automation\codex_supervisor_api.py'

if ($RemoveTask) {
    & schtasks.exe /Delete /TN $TaskName /F | Out-Null
}

Write-Host "Codex automation cleanup requested."
