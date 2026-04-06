param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787,
    [int]$MaxWaves = 10,
    [string]$Model = "gpt-5.4",
    [string]$ReasoningEffort = "",
    [int]$StallTimeoutSeconds = 1800,
    [int]$BootstrapGraceSeconds = 180,
    [int]$StrategicIntervalSeconds = 1200,
    [int]$StrategicDurationHours = 18,
    [string]$ActiveUxPhaseId = "ux_phase_1"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$prepareScript = Join-Path $PSScriptRoot "Prepare-UxRefinementAutonomy.ps1"
$ensureApiScript = Join-Path $PSScriptRoot "Ensure-CodexSupervisorApi.ps1"
$testApiScript = Join-Path $PSScriptRoot "Test-CodexSupervisorApi.ps1"
$stopScript = Join-Path $PSScriptRoot "Stop-CodexAutomation.ps1"
$uxStrategicScript = Join-Path $PSScriptRoot "Start-UxRefinementStrategicSupervisorLoop.ps1"

powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $prepareScript -InstallTemplates -ActiveUxPhaseId $ActiveUxPhaseId | Out-Null
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $stopScript
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $ensureApiScript -BindHost $BindHost -Port $Port

powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $testApiScript -BindHost $BindHost -Port $Port -Action set-policy -MaxWaves $MaxWaves -ConsecutiveLowValueStop 3 | Out-Null
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $testApiScript -BindHost $BindHost -Port $Port -Action set-desired-run -Phase phase_ux_refinement -MaxWaves $MaxWaves -Model $Model -ReasoningEffort $ReasoningEffort -StallTimeoutSeconds $StallTimeoutSeconds -BootstrapGraceSeconds $BootstrapGraceSeconds | Out-Null
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File (Join-Path $PSScriptRoot "Invoke-UxRefinementStrategicSupervisor.ps1") -BindHost $BindHost -Port $Port -ActiveUxPhaseId $ActiveUxPhaseId | Out-Null
powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $testApiScript -BindHost $BindHost -Port $Port -Action start -Phase phase_ux_refinement -MaxWaves $MaxWaves -Model $Model -ReasoningEffort $ReasoningEffort | Out-Null

Start-Process pwsh -ArgumentList '-ExecutionPolicy','Bypass','-NoLogo','-NoProfile','-File',(Join-Path $PSScriptRoot 'Start-CodexSupervisorWatchdogLoop.ps1'),'-IntervalSeconds','60' -WorkingDirectory $repoRoot | Out-Null
Start-Process pwsh -ArgumentList '-ExecutionPolicy','Bypass','-NoLogo','-NoProfile','-File',$uxStrategicScript,'-BindHost',$BindHost,'-Port',$Port,'-IntervalSeconds',$StrategicIntervalSeconds,'-DurationHours',$StrategicDurationHours,'-ActiveUxPhaseId',$ActiveUxPhaseId -WorkingDirectory $repoRoot | Out-Null

powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $testApiScript -BindHost $BindHost -Port $Port -Action summary
