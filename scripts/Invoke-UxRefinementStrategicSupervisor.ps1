param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787,
    [string]$ActiveUxPhaseId = "",
    [switch]$ForcePhaseReset
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeRoot = Join-Path $repoRoot "docs\codex_dual_agent_runtime"
$apiRoot = Join-Path $runtimeRoot "api"
$guidancePath = Join-Path $runtimeRoot "supervisor_guidance.json"
$logPath = Join-Path $apiRoot "ux_strategic_supervisor.log"
$bundleRoot = Join-Path $repoRoot "docs\ux_refinement_autonomy_bundle"
$phasePlanPath = Join-Path $bundleRoot "automation\phase_plan.yaml"
$bootstrapPromptPath = Join-Path $bundleRoot "prompts\PROMPT_SHORT_BOOTSTRAP_UI_REFINEMENT.md"
$fullPromptPath = Join-Path $bundleRoot "prompts\PROMPT_FULL_AUTONOMOUS_UI_REFINEMENT.md"

New-Item -ItemType Directory -Force -Path $apiRoot | Out-Null

function Write-UxStrategicLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format o), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
    Write-Host $line
}

function Get-JsonFile {
    param([string]$PathValue)
    if (-not (Test-Path -LiteralPath $PathValue)) {
        return $null
    }
    return Get-Content -LiteralPath $PathValue -Raw | ConvertFrom-Json
}

function Get-PythonPath {
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }
    throw "Python não encontrado para ler o phase_plan.yaml do bundle de UX."
}

function Get-YamlFileAsObject {
    param([string]$PathValue)

    $pythonPath = Get-PythonPath
    $script = @'
import json
import sys
from pathlib import Path
import yaml

payload = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(json.dumps(payload, ensure_ascii=False))
'@
    $json = $script | & $pythonPath - $PathValue
    if (-not $json) {
        throw "Falha ao carregar YAML em $PathValue"
    }
    return $json | ConvertFrom-Json
}

function Write-JsonUtf8NoBom {
    param(
        [string]$PathValue,
        [object]$Payload
    )

    $json = $Payload | ConvertTo-Json -Depth 30
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($PathValue, $json, $utf8NoBom)
}

function Get-State {
    try {
        $uri = "http://{0}:{1}/state" -f $BindHost, $Port
        return Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 20
    }
    catch {
        return $null
    }
}

if (-not (Test-Path -LiteralPath $bundleRoot)) {
    throw "Bundle de UX não encontrado em $bundleRoot. Execute Prepare-UxRefinementAutonomy.ps1 primeiro."
}

$phasePlan = Get-YamlFileAsObject -PathValue $phasePlanPath
$phases = @($phasePlan.phases)
if ($phases.Count -eq 0) {
    throw "phase_plan.yaml do bundle de UX não possui fases."
}

$existingGuidance = Get-JsonFile -PathValue $guidancePath
$state = Get-State
$activeWaveIndex = 0
$activeRole = ""
$wavesCompleted = 0
$healthState = "not_running"
$runId = ""
$stopReason = ""

if ($state) {
    $activeWaveIndex = [int]$state.supervisor_state.active_wave_index
    $activeRole = [string]$state.supervisor_state.active_role
    $wavesCompleted = [int]$state.supervisor_state.waves_completed
    $healthState = [string]$state.health.state
    $runId = [string]$state.process.run_id
    $stopReason = [string]$state.health.stop_reason
}

$phaseById = @{}
foreach ($phase in $phases) {
    $phaseById[[string]$phase.id] = $phase
}

if ([string]::IsNullOrWhiteSpace($ActiveUxPhaseId)) {
    if (-not $ForcePhaseReset -and $existingGuidance -and $existingGuidance.mode -eq "ux_refinement" -and $existingGuidance.active_ux_phase_id) {
        $ActiveUxPhaseId = [string]$existingGuidance.active_ux_phase_id
    }
    else {
        $ActiveUxPhaseId = [string]$phases[0].id
    }
}

if (-not $phaseById.ContainsKey($ActiveUxPhaseId)) {
    throw "Fase de UX desconhecida: $ActiveUxPhaseId"
}

$activeUxPhase = $phaseById[$ActiveUxPhaseId]
$phaseOrder = @($phases | ForEach-Object { [string]$_.id })
$phasePosition = [Array]::IndexOf($phaseOrder, $ActiveUxPhaseId)
$nextUxPhaseId = if ($phasePosition -ge 0 -and $phasePosition -lt ($phaseOrder.Count - 1)) { $phaseOrder[$phasePosition + 1] } else { "" }

$recentCommitSubjects = @()
try {
    $recentCommitSubjects = @(git -C $repoRoot log --pretty=format:%s -n 8 | Where-Object { $_ -and $_.Trim() })
}
catch {
    $recentCommitSubjects = @()
}

$guidance = [ordered]@{
    updated_at = (Get-Date).ToUniversalTime().ToString("o")
    mode = "ux_refinement"
    source_bundle = "docs/ux_refinement_autonomy_bundle"
    source_zip = "docs/ux_refinement_autonomy_bundle.zip"
    phase_plan = "docs/ux_refinement_autonomy_bundle/automation/phase_plan.yaml"
    bootstrap_prompt = "docs/ux_refinement_autonomy_bundle/prompts/PROMPT_SHORT_BOOTSTRAP_UI_REFINEMENT.md"
    full_prompt = "docs/ux_refinement_autonomy_bundle/prompts/PROMPT_FULL_AUTONOMOUS_UI_REFINEMENT.md"
    current_repo_head = (git -C $repoRoot rev-parse HEAD).Trim()
    current_branch = (git -C $repoRoot branch --show-current).Trim()
    active_ux_phase_id = $ActiveUxPhaseId
    active_ux_phase = [ordered]@{
        id = [string]$activeUxPhase.id
        name = [string]$activeUxPhase.name
        focus = @($activeUxPhase.focus)
        expected_outcomes = @($activeUxPhase.expected_outcomes)
    }
    next_ux_phase_id = $nextUxPhaseId
    phase_sequence = @($phases | ForEach-Object {
        [ordered]@{
            id = [string]$_.id
            name = [string]$_.name
        }
    })
    current_focus = [ordered]@{
        active_wave_index = $activeWaveIndex
        active_role = $activeRole
        waves_completed = $wavesCompleted
        health_state = $healthState
        run_id = $runId
        stop_reason = $stopReason
    }
    directives = @(
        "Do not reopen architecture or replace the current Dash/Cytoscape stack.",
        "Use decision_platform as the product surface and preserve Julia-only official execution.",
        "Treat Studio, Runs, Decision and Audit as the main product spaces.",
        "Keep the Studio focused on the business graph only; technical internal hubs and derived nodes must stay hidden from the primary surface.",
        "Prefer direct manipulation on the canvas over fragmented raw forms whenever the Studio changes.",
        "Reduce html.Pre and raw JSON as primary UI surfaces; use progressive disclosure instead.",
        "Do not allow orphan nodes or technical clutter in the main final visualization.",
        "Prioritize user-facing flow clarity over backend-only refinements.",
        "Require meaningful UX progress in every wave and stop after three low-value waves.",
        "Push the product toward market-grade UX instead of a cleaned-up engineering console."
    )
    product_baseline = @(
        "selected_candidate",
        "selected_candidate_explanation",
        "engine_comparison",
        "technical_tie",
        "studio nodes/edges",
        "queue/run model"
    )
    acceptance_targets = @(
        "navigation clarity",
        "scenario readiness feedback",
        "queue/runs readability",
        "winner vs runner-up visibility",
        "technical tie explicitness",
        "clear infeasibility reasons"
    )
    evidence_requirements = @(
        "commit per meaningful phase",
        "docs updated with honest handoff",
        "tests updated where UI behavior changes",
        "visual evidence via screenshot or structured UI snapshot when possible"
    )
    recent_commit_subjects = $recentCommitSubjects
    repo_overlay = [ordered]@{
        root_agents = "AGENTS.md"
        ux_bundle_root = "docs/ux_refinement_autonomy_bundle"
        installed_agents = @(
            ".codex/agents/ux_architect.md",
            ".codex/agents/product_flow_engineer.md",
            ".codex/agents/ux_auditor.md"
        )
        installed_skill = ".codex/skills/ux_refinement/SKILL.md"
    }
}

Write-JsonUtf8NoBom -PathValue $guidancePath -Payload $guidance
Write-UxStrategicLog ("guidance_updated mode=ux_refinement active_ux_phase={0} active_wave={1} active_role={2} health={3}" -f $ActiveUxPhaseId, $activeWaveIndex, $activeRole, $healthState)
$guidance | ConvertTo-Json -Depth 30
