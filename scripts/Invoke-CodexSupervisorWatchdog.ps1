param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$apiRoot = Join-Path $repoRoot "docs\\codex_dual_agent_runtime\\api"
$watchdogLog = Join-Path $apiRoot "watchdog.log"
$clientScript = Join-Path $repoRoot "scripts\\Test-CodexSupervisorApi.ps1"
$ensureScript = Join-Path $repoRoot "scripts\\Ensure-CodexSupervisorApi.ps1"

New-Item -ItemType Directory -Force -Path $apiRoot | Out-Null

function Write-WatchdogLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format o), $Message
    Add-Content -LiteralPath $watchdogLog -Value $line -Encoding utf8
    Write-Host $line
}

function Invoke-ApiJson {
    param(
        [ValidateSet('GET', 'POST', 'DELETE')]
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $uri = "http://{0}:{1}{2}" -f $BindHost, $Port, $Path
    if ($Method -eq 'GET') {
        return Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 10
    }
    if ($Method -eq 'DELETE') {
        return Invoke-RestMethod -Method Delete -Uri $uri -TimeoutSec 10
    }
    $json = if ($null -eq $Body) { '{}' } else { $Body | ConvertTo-Json -Depth 20 }
    return Invoke-RestMethod -Method Post -Uri $uri -ContentType 'application/json' -Body $json -TimeoutSec 15
}

powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $ensureScript -BindHost $BindHost -Port $Port | Out-Null

try {
    $state = Invoke-ApiJson -Method GET -Path '/state'
}
catch {
    Write-WatchdogLog "state_unavailable error=$($_.Exception.Message)"
    exit 1
}

$desired = $state.desired_run
$process = $state.process
$loopState = $state.loop_state
$health = $state.health

if ($null -eq $desired -or -not $desired.active) {
    Write-WatchdogLog "idle desired_run_inactive"
    exit 0
}

$terminalStop = $false
if ($loopState -and $loopState.stop_reason) {
    $terminalStop = $true
}

if ($process -and $process.running) {
    if ($health -and $health.stalled) {
        Write-WatchdogLog "stalled pid=$($process.pid) state=$($health.state) reason=$($health.reason) seconds_since_update=$($health.seconds_since_update)"
    }
    else {
        Write-WatchdogLog "ok pid=$($process.pid) phase=$($process.phase) active_wave=$($state.supervisor_state.active_wave_index) health=$($health.state) seconds_since_update=$($health.seconds_since_update)"
        exit 0
    }
}

if ($terminalStop -and -not $desired.restart_on_terminal_stop) {
    Write-WatchdogLog "stopped_terminal stop_reason=$($loopState.stop_reason)"
    exit 0
}

$startPayload = @{
    phase = if ($desired.phase) { [string]$desired.phase } else { 'phase_0' }
    backend = if ($desired.backend) { [string]$desired.backend } else { 'codex-exec-external' }
    max_waves = if ($desired.max_waves) { [int]$desired.max_waves } else { 10 }
    model = if ($desired.model) { [string]$desired.model } else { 'gpt-5.4' }
    reasoning_effort = if ($desired.reasoning_effort) { [string]$desired.reasoning_effort } else { 'high' }
}

try {
    if ($health -and $health.stalled) {
        $result = Invoke-ApiJson -Method POST -Path '/restart' -Body $startPayload
        Write-WatchdogLog "restart_requested mode=stalled started=$($result.start.started) reason=$($health.reason)"
    }
    else {
        $result = Invoke-ApiJson -Method POST -Path '/start' -Body $startPayload
        Write-WatchdogLog "restart_requested mode=not_running started=$($result.started) reason=$($result.reason)"
    }
    exit 0
}
catch {
    Write-WatchdogLog "restart_failed error=$($_.Exception.Message)"
    exit 1
}
