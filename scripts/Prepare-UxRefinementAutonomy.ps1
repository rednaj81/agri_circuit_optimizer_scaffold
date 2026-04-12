param(
    [switch]$InstallTemplates,
    [switch]$RefreshBundle,
    [string]$ActiveUxPhaseId = "ux_phase_2"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$docsRoot = Join-Path $repoRoot "docs"
$zipPath = Join-Path $docsRoot "ux_refinement_autonomy_bundle.zip"
$bundleRoot = Join-Path $docsRoot "ux_refinement_autonomy_bundle"
$extractRoot = Join-Path $docsRoot "_ux_bundle_extract"
$codexRoot = Join-Path $repoRoot ".codex"
$agentsRoot = Join-Path $codexRoot "agents"
$skillsRoot = Join-Path $codexRoot "skills"
$uxSkillRoot = Join-Path $skillsRoot "ux_refinement"
$guidanceScript = Join-Path $PSScriptRoot "Invoke-UxRefinementStrategicSupervisor.ps1"

if (-not (Test-Path -LiteralPath $zipPath)) {
    throw "Bundle ZIP não encontrado em $zipPath"
}

New-Item -ItemType Directory -Force -Path $docsRoot | Out-Null

if ($RefreshBundle -or -not (Test-Path -LiteralPath $bundleRoot)) {
    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $extractRoot | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractRoot -Force
    $extractedBundleRoot = Join-Path $extractRoot "ux_refinement_autonomy_bundle"
    if (-not (Test-Path -LiteralPath $extractedBundleRoot)) {
        throw "Estrutura inesperada no ZIP: pasta ux_refinement_autonomy_bundle não encontrada."
    }
    if (Test-Path -LiteralPath $bundleRoot) {
        Remove-Item -LiteralPath $bundleRoot -Recurse -Force
    }
    Move-Item -LiteralPath $extractedBundleRoot -Destination $bundleRoot
    Remove-Item -LiteralPath $extractRoot -Recurse -Force
}

$templateAgentsRoot = Join-Path $bundleRoot "templates\.codex\agents"
$templateSkillRoot = Join-Path $bundleRoot "templates\.codex\skills\ux_refinement"

if ($InstallTemplates) {
    New-Item -ItemType Directory -Force -Path $agentsRoot | Out-Null
    New-Item -ItemType Directory -Force -Path $uxSkillRoot | Out-Null

    Copy-Item -LiteralPath (Join-Path $templateAgentsRoot "ux_architect.md") -Destination (Join-Path $agentsRoot "ux_architect.md") -Force
    Copy-Item -LiteralPath (Join-Path $templateAgentsRoot "product_flow_engineer.md") -Destination (Join-Path $agentsRoot "product_flow_engineer.md") -Force
    Copy-Item -LiteralPath (Join-Path $templateAgentsRoot "ux_auditor.md") -Destination (Join-Path $agentsRoot "ux_auditor.md") -Force
    Copy-Item -LiteralPath (Join-Path $templateSkillRoot "SKILL.md") -Destination (Join-Path $uxSkillRoot "SKILL.md") -Force
}

powershell -ExecutionPolicy Bypass -NoLogo -NoProfile -File $guidanceScript -ActiveUxPhaseId $ActiveUxPhaseId | Out-Null

[pscustomobject]@{
    bundle_root = $bundleRoot
    bundle_ready = Test-Path -LiteralPath $bundleRoot
    templates_installed = [bool]$InstallTemplates
    active_ux_phase = $ActiveUxPhaseId
    bootstrap_prompt = Join-Path $bundleRoot "prompts\PROMPT_SHORT_BOOTSTRAP_UI_REFINEMENT.md"
    full_prompt = Join-Path $bundleRoot "prompts\PROMPT_FULL_AUTONOMOUS_UI_REFINEMENT.md"
    start_command = ".\scripts\Start-UxRefinementAutonomy.ps1"
} | ConvertTo-Json -Depth 10
