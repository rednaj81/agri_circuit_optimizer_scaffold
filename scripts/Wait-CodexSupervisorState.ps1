param(
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8787,
    [int]$TimeoutSeconds = 600,
    [int]$PollSeconds = 15
)

$ErrorActionPreference = 'Stop'

$baseUrl = "http://$BindHost`:$Port"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$lastSignature = ''

function Get-StateSignature {
    param([object]$State)
    $health = $State.health
    $supervisor = $State.supervisor_state
    return "{0}|{1}|{2}|{3}|{4}|{5}" -f `
        $State.process.running, `
        $supervisor.active_wave_index, `
        $supervisor.active_role, `
        $supervisor.waves_completed, `
        $health.state, `
        $health.last_updated_at
}

while ((Get-Date) -lt $deadline) {
    $state = Invoke-RestMethod -Method Get -Uri "$baseUrl/state" -TimeoutSec 15
    $signature = Get-StateSignature -State $state

    if (-not $lastSignature) {
        $lastSignature = $signature
    }
    elseif ($signature -ne $lastSignature) {
        $state | ConvertTo-Json -Depth 20
        exit 0
    }

    if ($state.health.stalled -or $state.health.state -eq 'terminal' -or -not $state.process.running) {
        $state | ConvertTo-Json -Depth 20
        exit 0
    }

    Start-Sleep -Seconds $PollSeconds
}

Invoke-RestMethod -Method Get -Uri "$baseUrl/state" -TimeoutSec 15 | ConvertTo-Json -Depth 20
