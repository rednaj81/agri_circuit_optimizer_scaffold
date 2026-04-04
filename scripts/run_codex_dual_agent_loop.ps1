param(
    [string]$Phase = "phase_0",
    [int]$MaxWaves = 10,
    [string]$Backend = "codex-exec-external",
    [string]$Model = "gpt-5.4",
    [string]$ReasoningEffort = "high",
    [switch]$PreflightOnly
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$pythonExe = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
$loopScript = Join-Path $repoRoot "automation\\codex_dual_agent_loop.py"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtualenv not found at $pythonExe"
}

if (-not (Test-Path $loopScript)) {
    throw "Loop script not found at $loopScript"
}

Write-Host "Running Codex dual-agent loop"
Write-Host "repo-root: $repoRoot"
Write-Host "phase: $Phase"
Write-Host "max-waves: $MaxWaves"
Write-Host "backend: $Backend"
Write-Host "model: $Model"
Write-Host "reasoning-effort: $ReasoningEffort"

$argsList = @(
    $loopScript,
    "--repo-root", $repoRoot,
    "--phase", $Phase,
    "--max-waves", $MaxWaves,
    "--backend", $Backend,
    "--model", $Model,
    "--reasoning-effort", $ReasoningEffort
)

if ($PreflightOnly) {
    $argsList += "--preflight-only"
}

& $pythonExe @argsList
