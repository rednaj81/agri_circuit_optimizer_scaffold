param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$runtimeRoot = Join-Path $repoRoot "docs\codex_dual_agent_runtime"
$apiRoot = Join-Path $runtimeRoot "api"
$guidancePath = Join-Path $runtimeRoot "supervisor_guidance.json"
$logPath = Join-Path $apiRoot "strategic_supervisor.log"

New-Item -ItemType Directory -Force -Path $apiRoot | Out-Null

function Write-StrategicLog {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date -Format o), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
    Write-Host $line
}

function Get-State {
    $uri = "http://{0}:{1}/state" -f $BindHost, $Port
    return Invoke-RestMethod -Method Get -Uri $uri -TimeoutSec 20
}

function Get-JsonFile {
    param([string]$PathValue)
    if (-not (Test-Path -LiteralPath $PathValue)) {
        return $null
    }
    return Get-Content -LiteralPath $PathValue -Raw | ConvertFrom-Json
}

function Get-LatestCommit {
    try {
        return (git -C $repoRoot rev-parse HEAD).Trim()
    }
    catch {
        return ""
    }
}

function Get-RecentCommitSubjects {
    param([int]$Count = 8)
    try {
        $lines = git -C $repoRoot log --pretty=format:%s -n $Count
        return @($lines | Where-Object { $_ -and $_.Trim() })
    }
    catch {
        return @()
    }
}

function New-Guidance {
    param(
        [object]$State,
        [object]$LoopState
    )

    $waves = @()
    if ($LoopState -and $LoopState.waves) {
        $waves = @($LoopState.waves)
    }

    $recentWaves = @($waves | Select-Object -Last 3)
    $recentObjectives = @($recentWaves | ForEach-Object { $_.architect_plan.objective })
    $recentVerdicts = @($recentWaves | ForEach-Object { $_.auditor_verdict })
    $recentCommitSubjects = @(Get-RecentCommitSubjects -Count 8)

    $validationPattern = '(runtime|valida|gate|telemetria|julia-only|fail-closed|profiles|diagnostic|comparison)'
    $productPattern = '(studio|component bank|componentes persistidos|persist|versionamento|cenario|cenário|queue|background runs|decision ui|node-edge|nodes|edges)'

    $validationHeavyCount = @($recentObjectives | Where-Object { $_ -match $validationPattern }).Count
    $productFacingCount = @($recentObjectives | Where-Object { $_ -match $productPattern }).Count
    $validationHeavyCommitCount = @($recentCommitSubjects | Where-Object { $_ -match $validationPattern }).Count
    $productFacingCommitCount = @($recentCommitSubjects | Where-Object { $_ -match $productPattern }).Count
    $latestVerdict = if ($recentVerdicts.Count -gt 0) { [string]$recentVerdicts[-1] } else { "" }
    $wavesCompleted = [int]($State.supervisor_state.waves_completed)
    $phaseId = [string]$State.supervisor_state.phase_id

    $directives = New-Object System.Collections.Generic.List[string]
    $rationale = New-Object System.Collections.Generic.List[string]
    $phaseAssessment = "continue_phase"
    $recommendedNextPhase = $phaseId

    if ($latestVerdict -eq "regression") {
        $phaseAssessment = "correct_regression_first"
        $directives.Add("A próxima onda deve corrigir apenas a regressão apontada pelo auditor e revalidar o contrato quebrado, sem abrir nova frente de infraestrutura.")
        $rationale.Add("A última onda concluída foi classificada como regressão pelo auditor.")
    }

    if (
        $phaseId -eq "phase_0" -and (
            ($wavesCompleted -ge 4 -and $validationHeavyCount -ge 2 -and $productFacingCount -eq 0) -or
            ($validationHeavyCommitCount -ge 4 -and $productFacingCommitCount -eq 0)
        )
    ) {
        $phaseAssessment = "prepare_phase_exit"
        $recommendedNextPhase = "phase_1"
        $directives.Add("Se o gate atual fechar sem regressão, encerre a phase_0 e mova a próxima onda para phase_1. Não gaste outra onda apenas refinando infraestrutura de validação.")
        $directives.Add("Ao abrir phase_1, priorize persistência/versionamento de cenários e catálogo de componentes persistido antes de qualquer novo hardening operacional.")
        $rationale.Add("As últimas ondas e os commits recentes ficaram concentrados em runtime truthfulness, gate e validação; o risco agora é overfitting da phase_0.")
    }

    if ($phaseId -eq "phase_0" -and $productFacingCount -eq 0) {
        $directives.Add("Enquanto a phase_0 não fecha, mantenha qualquer mudança estritamente ligada ao gate oficial Julia-only e à evidência de saída da fase.")
    }

    if ($latestVerdict -ne "regression" -and $phaseAssessment -eq "continue_phase") {
        $directives.Add("Continue a onda atual, mas evite criar novos wrappers, perfis ou camadas de automação sem relação direta com os critérios de saída da fase.")
        $rationale.Add("O progresso recente segue alinhado com a fase, mas a densidade de mudanças operacionais já é alta.")
    }

    return [ordered]@{
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
        phase_id = $phaseId
        phase_assessment = $phaseAssessment
        recommended_next_phase = $recommendedNextPhase
        current_focus = [ordered]@{
            active_wave_index = $State.supervisor_state.active_wave_index
            active_role = $State.supervisor_state.active_role
            waves_completed = $wavesCompleted
            last_updated_at = $State.health.last_updated_at
            health_state = $State.health.state
            latest_commit = Get-LatestCommit
        }
        recent_wave_objectives = $recentObjectives
        recent_wave_verdicts = $recentVerdicts
        recent_commit_subjects = $recentCommitSubjects
        directives = @($directives)
        rationale = @($rationale)
    }
}

try {
    $state = Get-State
    $loopState = Get-JsonFile -PathValue (Join-Path $runtimeRoot "loop_state.json")
    $guidance = New-Guidance -State $state -LoopState $loopState
    $guidance | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $guidancePath -Encoding utf8
    Write-StrategicLog "guidance_updated phase=$($guidance.phase_id) assessment=$($guidance.phase_assessment) active_wave=$($guidance.current_focus.active_wave_index) active_role=$($guidance.current_focus.active_role)"
}
catch {
    Write-StrategicLog "guidance_failed error=$($_.Exception.Message)"
    exit 1
}
