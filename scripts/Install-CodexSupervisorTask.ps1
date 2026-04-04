param(
    [string]$TaskName = "CodexDualAgentSupervisor",
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$watchdogScript = Join-Path $repoRoot "scripts\\Invoke-CodexSupervisorWatchdog.ps1"
$pwshPath = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwshPath) {
    $pwshPath = (Get-Command powershell -ErrorAction Stop).Source
}

$taskCommand = "`"$pwshPath`" -ExecutionPolicy Bypass -NoLogo -NoProfile -File `"$watchdogScript`" -BindHost $BindHost -Port $Port"

& schtasks.exe /Create /F /TN $TaskName /SC MINUTE /MO 1 /TR $taskCommand
if ($LASTEXITCODE -ne 0) {
    throw "schtasks.exe failed with exit code $LASTEXITCODE"
}

Write-Host "Scheduled task registered: $TaskName"
