param(
    [ValidateSet('architect', 'developer', 'auditor')]
    [string]$Role,
    [string]$Text = "",
    [string]$InputFile = "",
    [switch]$Clear,
    [switch]$Show
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$instructionsRoot = Join-Path $repoRoot "docs\codex_dual_agent_runtime\fresh_instructions"
$instructionPath = Join-Path $instructionsRoot "$Role.md"

New-Item -ItemType Directory -Force -Path $instructionsRoot | Out-Null

if ($Clear) {
    [System.IO.File]::WriteAllText($instructionPath, "", [System.Text.UTF8Encoding]::new($false))
}
elseif ($InputFile) {
    if (-not (Test-Path -LiteralPath $InputFile)) {
        throw "Arquivo de entrada não encontrado: $InputFile"
    }
    $content = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $InputFile), [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::WriteAllText($instructionPath, $content, [System.Text.UTF8Encoding]::new($false))
}
elseif ($Text) {
    [System.IO.File]::WriteAllText($instructionPath, $Text, [System.Text.UTF8Encoding]::new($false))
}

$content = if (Test-Path -LiteralPath $instructionPath) { [System.IO.File]::ReadAllText($instructionPath, [System.Text.UTF8Encoding]::new($false)) } else { "" }

if ($Show -or $true) {
    [pscustomobject]@{
        role = $Role
        path = $instructionPath
        has_content = [bool]($content.Trim())
        content_preview = if ($content.Length -gt 240) { $content.Substring(0, 240) + "..." } else { $content }
    } | ConvertTo-Json -Depth 6
}
