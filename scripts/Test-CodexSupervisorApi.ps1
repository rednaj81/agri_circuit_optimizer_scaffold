param(
    [ValidateSet('health', 'state', 'summary', 'logs', 'policy', 'desired-run', 'preflight', 'start', 'stop', 'restart', 'set-policy', 'clear-policy', 'set-desired-run')]
    [string]$Action = 'state',
    [string]$BindHost = '127.0.0.1',
    [int]$Port = 8787,
    [string]$Phase = 'phase_0',
    [string]$Backend = 'codex-exec-external',
    [int]$MaxWaves = 10,
    [string]$Model = 'gpt-5.4',
    [string]$ReasoningEffort = '',
    [int]$ConsecutiveLowValueStop = 3,
    [int]$StallTimeoutSeconds = 3600,
    [int]$BootstrapGraceSeconds = 300,
    [switch]$RestartOnTerminalStop
)

$ErrorActionPreference = 'Stop'

$baseUrl = "http://$BindHost`:$Port"

switch ($Action) {
    'health' { Invoke-RestMethod -Method Get -Uri "$baseUrl/health" | ConvertTo-Json -Depth 20; break }
    'state' { Invoke-RestMethod -Method Get -Uri "$baseUrl/state" | ConvertTo-Json -Depth 20; break }
    'summary' {
        $state = Invoke-RestMethod -Method Get -Uri "$baseUrl/state"
        [pscustomobject]@{
            process_running = $state.process.running
            pid = $state.process.pid
            run_id = $state.process.run_id
            run_root = $state.process.run_root
            active_wave_index = $state.supervisor_state.active_wave_index
            active_role = $state.supervisor_state.active_role
            waves_completed = $state.supervisor_state.waves_completed
            last_updated_at = $state.health.last_updated_at
            seconds_since_update = $state.health.seconds_since_update
            health_state = $state.health.state
            stalled = $state.health.stalled
            reason = $state.health.reason
            stop_reason = $state.health.stop_reason
        } | ConvertTo-Json -Depth 10
        break
    }
    'logs' { Invoke-RestMethod -Method Get -Uri "$baseUrl/logs" | ConvertTo-Json -Depth 20; break }
    'policy' { Invoke-RestMethod -Method Get -Uri "$baseUrl/policy" | ConvertTo-Json -Depth 20; break }
    'desired-run' { Invoke-RestMethod -Method Get -Uri "$baseUrl/desired-run" | ConvertTo-Json -Depth 20; break }
    'clear-policy' { Invoke-RestMethod -Method Delete -Uri "$baseUrl/policy" | ConvertTo-Json -Depth 20; break }
    'set-policy' {
        $policyBody = @{
            max_waves = $MaxWaves
            consecutive_low_value_stop = $ConsecutiveLowValueStop
            low_value_labels = @('low_significance', 'no_progress', 'regression')
            final_stabilization_wave = $true
        } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$baseUrl/policy" -ContentType 'application/json' -Body $policyBody | ConvertTo-Json -Depth 20
        break
    }
    'set-desired-run' {
        $desiredRunBody = @{
            active = $true
            phase = $Phase
            backend = $Backend
            max_waves = $MaxWaves
            model = $Model
            reasoning_effort = $ReasoningEffort
            restart_on_terminal_stop = [bool]$RestartOnTerminalStop
            stall_timeout_seconds = $StallTimeoutSeconds
            bootstrap_grace_seconds = $BootstrapGraceSeconds
        } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$baseUrl/desired-run" -ContentType 'application/json' -Body $desiredRunBody | ConvertTo-Json -Depth 20
        break
    }
    default {
        $body = @{
            phase = $Phase
            backend = $Backend
            max_waves = $MaxWaves
            model = $Model
            reasoning_effort = $ReasoningEffort
        } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "$baseUrl/$Action" -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 20
        break
    }
}
