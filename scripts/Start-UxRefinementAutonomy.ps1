param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787,
    [int]$MaxWaves = 10,
    [string]$Model = "gpt-5.4",
    [string]$ReasoningEffort = "",
    [int]$StallTimeoutSeconds = 3600,
    [int]$BootstrapGraceSeconds = 300,
    [int]$StrategicIntervalSeconds = 1200,
    [int]$StrategicDurationHours = 18,
    [string]$ActiveUxPhaseId = "ux_phase_2"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$prepareScript = Join-Path $PSScriptRoot "Prepare-UxRefinementAutonomy.ps1"
$ensureApiScript = Join-Path $PSScriptRoot "Ensure-CodexSupervisorApi.ps1"
$testApiScript = Join-Path $PSScriptRoot "Test-CodexSupervisorApi.ps1"
$stopScript = Join-Path $PSScriptRoot "Stop-CodexAutomation.ps1"
$uxStrategicScript = Join-Path $PSScriptRoot "Start-UxRefinementStrategicSupervisorLoop.ps1"

function Invoke-TestApiAction {
    param(
        [string]$ActionName,
        [hashtable]$ExtraParameters = @{}
    )

    $args = @(
        '-ExecutionPolicy', 'Bypass',
        '-NoLogo',
        '-NoProfile',
        '-File', $testApiScript,
        '-BindHost', $BindHost,
        '-Port', $Port,
        '-Action', $ActionName
    )

    foreach ($entry in $ExtraParameters.GetEnumerator()) {
        $args += "-$($entry.Key)"
        if ($null -ne $entry.Value -and ($entry.Value -isnot [switch])) {
            $args += [string]$entry.Value
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($ReasoningEffort)) {
        $args += @('-ReasoningEffort', $ReasoningEffort)
    }

    powershell @args
}

powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $prepareScript -InstallTemplates -ActiveUxPhaseId $ActiveUxPhaseId | Out-Null
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $stopScript
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $ensureApiScript -BindHost $BindHost -Port $Port

Invoke-TestApiAction -ActionName 'set-policy' -ExtraParameters @{
    MaxWaves = $MaxWaves
    ConsecutiveLowValueStop = 3
} | Out-Null
Invoke-TestApiAction -ActionName 'set-desired-run' -ExtraParameters @{
    Phase = 'phase_ux_refinement'
    MaxWaves = $MaxWaves
    Model = $Model
    StallTimeoutSeconds = $StallTimeoutSeconds
    BootstrapGraceSeconds = $BootstrapGraceSeconds
} | Out-Null
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File (Join-Path $PSScriptRoot "Invoke-UxRefinementStrategicSupervisor.ps1") -BindHost $BindHost -Port $Port -ActiveUxPhaseId $ActiveUxPhaseId | Out-Null
Invoke-TestApiAction -ActionName 'start' -ExtraParameters @{
    Phase = 'phase_ux_refinement'
    MaxWaves = $MaxWaves
    Model = $Model
} | Out-Null

Start-Process pwsh -ArgumentList '-ExecutionPolicy','Bypass','-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot 'Start-CodexSupervisorWatchdogLoop.ps1'),'-IntervalSeconds','60' -WorkingDirectory $repoRoot | Out-Null
Start-Process pwsh -ArgumentList '-ExecutionPolicy','Bypass','-NoLogo','-NoProfile','-File',$uxStrategicScript,'-BindHost',$BindHost,'-Port',$Port,'-IntervalSeconds',$StrategicIntervalSeconds,'-DurationHours',$StrategicDurationHours,'-ActiveUxPhaseId',$ActiveUxPhaseId -WorkingDirectory $repoRoot | Out-Null

Invoke-TestApiAction -ActionName 'summary'
