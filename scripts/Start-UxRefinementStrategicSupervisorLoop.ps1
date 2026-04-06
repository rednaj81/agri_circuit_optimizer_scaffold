param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787,
    [int]$IntervalSeconds = 1200,
    [int]$DurationHours = 18,
    [string]$ActiveUxPhaseId = "ux_phase_1"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiRoot = Join-Path $repoRoot "docs\codex_dual_agent_runtime\api"
$watchdogScript = Join-Path $PSScriptRoot "Invoke-CodexSupervisorWatchdog.ps1"
$strategicScript = Join-Path $PSScriptRoot "Invoke-UxRefinementStrategicSupervisor.ps1"
$waitScript = Join-Path $PSScriptRoot "Wait-CodexSupervisorState.ps1"
$loopLog = Join-Path $apiRoot "ux_strategic_supervisor_loop.log"
$deadline = (Get-Date).AddHours($DurationHours)

New-Item -ItemType Directory -Force -Path $apiRoot | Out-Null

function Write-LoopLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format o), $Message
    Add-Content -LiteralPath $loopLog -Value $line -Encoding utf8
    Write-Host $line
}

while ((Get-Date) -lt $deadline) {
    Write-LoopLog "cycle_start"
    powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $watchdogScript -BindHost $BindHost -Port $Port
    powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $strategicScript -BindHost $BindHost -Port $Port -ActiveUxPhaseId $ActiveUxPhaseId

    $remainingSeconds = [Math]::Max(0, [int][Math]::Floor(($deadline - (Get-Date)).TotalSeconds))
    if ($remainingSeconds -le 0) {
        break
    }

    $waitTimeoutSeconds = [Math]::Min($IntervalSeconds, $remainingSeconds)
    Write-LoopLog "cycle_wait timeout_seconds=$waitTimeoutSeconds"
    powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $waitScript -BindHost $BindHost -Port $Port -TimeoutSeconds $waitTimeoutSeconds -PollSeconds 30 | Out-Null
}

Write-LoopLog "loop_completed"
