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
$phase1ManifestPath = Join-Path $runtimeRoot "phase_0_validation_manifest.json"

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

function Write-JsonUtf8NoBom {
    param(
        [string]$PathValue,
        [object]$Payload
    )

    $json = $Payload | ConvertTo-Json -Depth 20
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($PathValue, $json, $utf8NoBom)
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
    $phase1Manifest = Get-JsonFile -PathValue $phase1ManifestPath

    if (
        $phase1Manifest -and
        [string]$phase1Manifest.current_phase_exit -eq "phase_3" -and
        [string]$phase1Manifest.current_phase_status -eq "active"
    ) {
        $phase3Validation = $phase1Manifest.phase_3_current_validation
        $phase1Validation = $phase1Manifest.phase_1_exit_validation

        $phase3Tests = @()
        if ($phase3Validation -and $phase3Validation.supporting_tests) {
            $phase3Tests = @($phase3Validation.supporting_tests)
        }
        if ($phase3Tests.Count -eq 0 -and $phase1Manifest.current_acceptance_target) {
            $phase3Tests = @([string]$phase1Manifest.current_acceptance_target)
        }
        if ($phase3Tests.Count -eq 0) {
            $phase3Tests = @("tests/decision_platform/test_phase3_queue_acceptance.py")
        }

        $phase1Tests = @()
        if ($phase1Validation -and $phase1Validation.supporting_tests) {
            $phase1Tests = @($phase1Validation.supporting_tests)
        }
        if ($phase1Tests.Count -eq 0) {
            $phase1Tests = @(
                "tests/decision_platform/test_scenario_settings_contract.py",
                "tests/decision_platform/test_scenario_persistence.py",
                "tests/decision_platform/test_phase1_exit_acceptance.py",
                "tests/decision_platform/test_phase1_exit_artifacts.py"
            )
        }

        return [ordered]@{
            updated_at = (Get-Date).ToUniversalTime().ToString("o")
            phase_id = "phase_3"
            phase_assessment = "continue_phase"
            recommended_next_phase = "phase_3"
            current_focus = [ordered]@{
                active_wave_index = $State.supervisor_state.active_wave_index
                active_role = $State.supervisor_state.active_role
                waves_completed = [int]($State.supervisor_state.waves_completed)
                last_updated_at = $State.supervisor_state.last_updated_at
                health_state = "phase_3_serial_queue_active"
                latest_commit = Get-LatestCommit
            }
            recent_wave_objectives = @(
                "Open phase_3 with the serial queue MVP.",
                "Add queued-job cancel, explicit rerun, and individual run inspection.",
                "Realign governance so phase_3 is the only active functional phase."
            )
            recent_wave_verdicts = @(
                "significant_progress",
                "significant_progress",
                "operational_alignment"
            )
            recent_commit_subjects = $recentCommitSubjects
            directives = @(
                "Treat phase_1 and phase_2 as closed baselines.",
                "Use tests/decision_platform/test_phase3_queue_acceptance.py as the current functional acceptance gate.",
                "Keep the worker serial and avoid opening parallel orchestration in this wave."
            )
            rationale = @(
                "The codebase already opened the minimum serial queue slice of phase_3.",
                "Governance must reflect the active functional phase to keep gates and continuity auditable."
            )
            current_phase_gate = [ordered]@{
                manifest = "docs/codex_dual_agent_runtime/phase_0_validation_manifest.json"
                manifest_block = "phase_3_current_validation"
                handoff = "docs/2026-04-05_phase3_wave1_queue_open_handoff.md"
                phase_plan = "docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml"
                tests = $phase3Tests
                signals = @(
                    "run_job local persistence",
                    "serial worker only",
                    "queued cancel",
                    "explicit rerun",
                    "individual run inspection"
                )
            }
            phase_1_exit_evidence = [ordered]@{
                manifest = "docs/codex_dual_agent_runtime/phase_0_validation_manifest.json"
                manifest_block = "phase_1_exit_validation"
                handoff = "docs/2026-04-05_phase1_wave5_exit_handoff.md"
                phase_plan = "docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml"
                tests = $phase1Tests
                signals = @(
                    "scenario_bundle.yaml",
                    "component_catalog.csv",
                    "scenario_settings.storage canonical mapping",
                    "save -> reopen -> run provenance"
                )
            }
            phase_1_continuation_policy = [ordered]@{
                additional_functional_waves_allowed = $false
                final_operational_correction_wave = [int]$phase1Manifest.final_operational_correction_wave
                next_functional_phase = "phase_2"
            }
            closed_phases = [ordered]@{
                phase_1 = [ordered]@{
                    status = "closed"
                    handoff = "docs/2026-04-05_phase1_wave5_exit_handoff.md"
                }
                phase_2 = [ordered]@{
                    status = "closed"
                    handoff = "docs/2026-04-05_phase2_exit.md"
                    acceptance_target = "tests/decision_platform/test_phase2_exit_acceptance.py"
                }
            }
            out_of_scope_for_phase_1 = @(
                "tests/decision_platform/test_studio_structure.py",
                "structural node or edge creation, duplication, or deletion",
                "queue and background runs",
                "ranking, scoring, and decision UI expansion"
            )
        }
    }

    if (
        $phase1Manifest -and
        [string]$phase1Manifest.current_phase_exit -eq "phase_1" -and
        [string]$phase1Manifest.current_phase_status -eq "sealed" -and
        -not [bool]$phase1Manifest.phase_1_additional_functional_waves_allowed
    ) {
        $phase1Validation = $phase1Manifest.phase_1_exit_validation
        $supportingTests = @()
        if ($phase1Validation -and $phase1Validation.supporting_tests) {
            $supportingTests = @($phase1Validation.supporting_tests)
        }
        if ($supportingTests.Count -eq 0) {
            $supportingTests = @(
                "tests/decision_platform/test_scenario_settings_contract.py",
                "tests/decision_platform/test_scenario_persistence.py",
                "tests/decision_platform/test_phase1_exit_acceptance.py",
                "tests/decision_platform/test_phase1_exit_artifacts.py"
            )
        }

        $outOfScope = @()
        if ($phase1Validation -and $phase1Validation.out_of_scope) {
            $outOfScope = @($phase1Validation.out_of_scope)
        }
        if ($outOfScope.Count -eq 0) {
            $outOfScope = @(
                "Structural studio creation, duplication, or deletion flows",
                "Queue and background execution",
                "Ranking, scoring, and decision UI expansion",
                "Julia runtime changes beyond the frozen phase_0 gate"
            )
        }

        return [ordered]@{
            updated_at = (Get-Date).ToUniversalTime().ToString("o")
            phase_id = "phase_1"
            phase_assessment = "phase_closed"
            recommended_next_phase = "phase_2"
            current_focus = [ordered]@{
                active_wave_index = [int]$phase1Manifest.final_operational_correction_wave
                active_role = "developer"
                waves_completed = [int]$phase1Manifest.final_operational_correction_wave
                last_updated_at = (Get-Date).ToUniversalTime().ToString("o")
                health_state = "phase_1_closed_no_further_functional_waves"
                latest_commit = Get-LatestCommit
            }
            recent_wave_objectives = @(
                "Seal a reproducible phase_1 exit gate.",
                "Close phase_1 operationally without adding scope.",
                "Apply one final operational correction for reproducible closure artifacts.",
                "Correct the regression in the phase_1 closure artifacts without reopening functional scope."
            )
            recent_wave_verdicts = @(
                "significant_progress",
                "low_significance",
                "regression",
                "corrective_closeout"
            )
            recent_commit_subjects = $recentCommitSubjects
            directives = @(
                "Treat phase_1 as sealed after this regression correction.",
                "Do not schedule new functional waves inside phase_1.",
                "Open phase_2 explicitly for any structural studio continuation."
            )
            rationale = @(
                "The functional exit criteria for phase_1 are already covered by code and tests.",
                "The only remaining work was restoring direct and reproducible reads of the closure artifacts."
            )
            phase_exit_evidence = [ordered]@{
                manifest = "docs/codex_dual_agent_runtime/phase_0_validation_manifest.json"
                manifest_block = "phase_1_exit_validation"
                handoff = "docs/2026-04-05_phase1_wave5_exit_handoff.md"
                phase_plan = "docs/codex_dual_agent_hydraulic_autonomy_bundle/automation/phase_plan.yaml"
                tests = $supportingTests
                signals = @(
                    "scenario_bundle.yaml",
                    "component_catalog.csv",
                    "scenario_settings.storage canonical mapping",
                    "save -> reopen -> run provenance"
                )
            }
            phase_1_continuation_policy = [ordered]@{
                additional_functional_waves_allowed = $false
                final_operational_correction_wave = [int]$phase1Manifest.final_operational_correction_wave
                next_functional_phase = "phase_2"
            }
            out_of_scope_for_phase_1 = $outOfScope
        }
    }

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
    Write-JsonUtf8NoBom -PathValue $guidancePath -Payload $guidance
    Write-StrategicLog "guidance_updated phase=$($guidance.phase_id) assessment=$($guidance.phase_assessment) active_wave=$($guidance.current_focus.active_wave_index) active_role=$($guidance.current_focus.active_role)"
}
catch {
    Write-StrategicLog "guidance_failed error=$($_.Exception.Message)"
    exit 1
}
