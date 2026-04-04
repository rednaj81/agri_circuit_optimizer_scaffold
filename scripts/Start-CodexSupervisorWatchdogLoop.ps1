param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787,
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"

$watchdogScript = Join-Path $PSScriptRoot "Invoke-CodexSupervisorWatchdog.ps1"

while ($true) {
    powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $watchdogScript -BindHost $BindHost -Port $Port
    Start-Sleep -Seconds $IntervalSeconds
}
