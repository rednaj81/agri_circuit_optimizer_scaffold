"""
Orquestrador local do loop Architect -> Developer -> Auditor.

Backend principal:
- `codex-exec-external`: usa `codex exec` em processo PowerShell externo com CODEX_HOME isolado

Backend auxiliar:
- `scaffold`: valida apenas a política de ondas e a persistência do loop

Este runner evita chamadas aninhadas diretas ao Codex dentro do mesmo processo Python.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


Verdict = Literal[
    "significant_progress",
    "moderate_progress",
    "low_significance",
    "no_progress",
    "regression",
]
Recommendation = Literal["continue", "redirect", "stop"]
Backend = Literal["codex-exec-external", "scaffold"]

ALLOWED_CODEX_HOME_SEED_ITEMS = {
    "auth.json",
    "cap_sid",
    ".sandbox-secrets",
    "sessions",
    "rules",
    "version.json",
    ".codex-global-state.json",
    "models_cache.json",
}


class ArchitectOutput(BaseModel):
    phase_id: str
    objective: str
    wave_scope: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    target_files: list[str] = Field(default_factory=list)
    main_risk: str
    do_not_touch: list[str] = Field(default_factory=list)
    done_definition: str


class DeveloperOutput(BaseModel):
    implementation_summary: list[str] = Field(default_factory=list)
    validations_to_run: list[str] = Field(default_factory=list)
    artifacts_to_generate: list[str] = Field(default_factory=list)
    docs_to_update: list[str] = Field(default_factory=list)
    commit_plan: str
    handoff: str
    limitations: list[str] = Field(default_factory=list)


class AuditorOutput(BaseModel):
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendation: Recommendation
    low_value_streak_relevant: bool = False


@dataclass
class PreflightState:
    backend_requested: str
    codex_cli_found: bool
    pwsh_found: bool
    codex_home_seed_found: bool
    codex_home_seed_path: str = ""
    codex_exec_probe_ok: bool = False
    codex_exec_probe_error: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class WaveState:
    wave_index: int
    phase_id: str
    architect_plan: dict[str, Any] = field(default_factory=dict)
    developer_summary: dict[str, Any] = field(default_factory=dict)
    auditor_verdict: str = ""
    auditor_reasoning: dict[str, Any] = field(default_factory=dict)
    commit_sha: str = ""
    run_root: str = ""


@dataclass
class AgentSessionState:
    role: str
    session_id: str = ""
    codex_home: str = ""
    last_wave_index: int = 0
    last_status: str = "idle"
    last_prompt_path: str = ""
    last_message_path: str = ""
    last_stdout_path: str = ""
    last_stderr_path: str = ""
    last_run_root: str = ""


@dataclass
class LoopState:
    phase_id: str
    backend: str
    run_id: str
    run_started_at: str
    run_root: str
    preflight: dict[str, Any]
    waves: list[WaveState]
    agent_sessions: dict[str, AgentSessionState] = field(default_factory=dict)
    consecutive_low_value: int = 0
    active_wave_index: int = 0
    active_role: str = ""
    last_updated_at: str = ""
    stop_reason: str = ""


def run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def runtime_dir(repo_root: Path) -> Path:
    out = repo_root / "docs" / "codex_dual_agent_runtime"
    out.mkdir(parents=True, exist_ok=True)
    return out


def runtime_policy_override_path(repo_root: Path) -> Path:
    return runtime_dir(repo_root) / "wave_policy.override.json"


def supervisor_guidance_path(repo_root: Path) -> Path:
    return runtime_dir(repo_root) / "supervisor_guidance.json"


def fresh_instructions_dir(repo_root: Path) -> Path:
    out = runtime_dir(repo_root) / "fresh_instructions"
    out.mkdir(parents=True, exist_ok=True)
    return out


def role_fresh_instruction_path(repo_root: Path, role: str) -> Path:
    return fresh_instructions_dir(repo_root) / f"{role}.md"


def runtime_scratch_dir(repo_root: Path, run_id: str) -> Path:
    out = runtime_dir(repo_root) / "runs" / run_id
    out.mkdir(parents=True, exist_ok=True)
    return out


def agent_runtime_dir(repo_root: Path, role: str) -> Path:
    out = runtime_dir(repo_root) / "agents" / role
    out.mkdir(parents=True, exist_ok=True)
    return out


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def persist_state(repo_root: Path, state: LoopState) -> None:
    out = runtime_dir(repo_root)
    state.last_updated_at = now_iso()
    (out / "loop_state.json").write_text(
        json.dumps(asdict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out / "agent_sessions.json").write_text(
        json.dumps({role: asdict(session) for role, session in state.agent_sessions.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out / "supervisor_state.json").write_text(
        json.dumps(
            {
                "phase_id": state.phase_id,
                "backend": state.backend,
                "run_id": state.run_id,
                "run_started_at": state.run_started_at,
                "run_root": state.run_root,
                "active_wave_index": state.active_wave_index,
                "active_role": state.active_role,
                "consecutive_low_value": state.consecutive_low_value,
                "waves_completed": len(state.waves),
                "stop_reason": state.stop_reason,
                "last_updated_at": state.last_updated_at,
                "agent_sessions": {role: asdict(session) for role, session in state.agent_sessions.items()},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def persist_preflight(repo_root: Path, preflight: PreflightState) -> None:
    out = runtime_dir(repo_root)
    (out / "preflight.json").write_text(
        json.dumps(asdict(preflight), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def current_head(repo_root: Path) -> str:
    try:
        return run_git(repo_root, "rev-parse", "HEAD")
    except Exception:
        return ""


def current_branch(repo_root: Path) -> str:
    try:
        return run_git(repo_root, "branch", "--show-current")
    except Exception:
        return ""


def current_status(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or "").strip()


def phase_metadata(repo_root: Path, phase_id: str) -> dict[str, Any]:
    phases = load_yaml(repo_root / "automation" / "phase_plan.yaml")
    phase = phases.get(phase_id)
    if not isinstance(phase, dict):
        raise KeyError(f"Unknown phase: {phase_id}")
    return phase


def wave_policy(repo_root: Path) -> dict[str, Any]:
    policy = load_yaml(repo_root / "automation" / "wave_policy.yaml")
    override_path = runtime_policy_override_path(repo_root)
    if override_path.exists():
        override = load_json(override_path)
        if isinstance(override, dict):
            policy.update(override)
    return policy


def repo_context_text(repo_root: Path, phase_id: str, wave_index: int, state: LoopState | None) -> str:
    phase = phase_metadata(repo_root, phase_id)
    status = current_status(repo_root)
    return "\n".join(
        [
            f"repo_root: {repo_root}",
            f"branch: {current_branch(repo_root)}",
            f"head: {current_head(repo_root)}",
            f"phase_id: {phase_id}",
            f"phase_target: {phase.get('target', '')}",
            f"phase_exit_criteria: {json.dumps(phase.get('exit_criteria', []), ensure_ascii=False)}",
            f"wave_index: {wave_index}",
            f"git_status_short: {status if status else 'clean'}",
            f"existing_waves: {len(state.waves) if state else 0}",
        ]
    )


def previous_wave_summary(state: LoopState | None) -> str:
    if not state or not state.waves:
        return "Nenhuma onda anterior registrada."
    return json.dumps(asdict(state.waves[-1]), indent=2, ensure_ascii=False)


def current_supervisor_guidance(repo_root: Path) -> dict[str, Any]:
    return load_optional_json(supervisor_guidance_path(repo_root))


def consume_role_fresh_instruction(
    repo_root: Path,
    role: str,
    role_run_root: Path,
) -> dict[str, str]:
    instruction_path = role_fresh_instruction_path(repo_root, role)
    if not instruction_path.exists():
        return {}
    content = instruction_path.read_text(encoding="utf-8-sig").strip()
    if not content:
        return {}
    consumed_at = now_iso()
    consumed_path = role_run_root / f"{role}.fresh-instruction.md"
    metadata_path = role_run_root / f"{role}.fresh-instruction.json"
    write_utf8(consumed_path, content.strip() + "\n")
    metadata_path.write_text(
        json.dumps(
            {
                "role": role,
                "source_path": str(instruction_path),
                "consumed_at": consumed_at,
                "consumed_copy_path": str(consumed_path),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    instruction_path.write_text("", encoding="utf-8")
    return {
        "content": content,
        "source_path": str(instruction_path),
        "consumed_at": consumed_at,
        "consumed_copy_path": str(consumed_path),
    }


def compose_initial_prompt(
    *,
    repo_root: Path,
    role_template_path: Path,
    role: str,
    phase_id: str,
    wave_index: int,
    state: LoopState | None,
    handoff_payload: str,
    output_model: type[BaseModel],
    fresh_instruction_payload: dict[str, str] | None = None,
) -> str:
    fresh_instruction_payload = fresh_instruction_payload or {}
    sections = [
        read_text(repo_root / "AGENTS.md"),
        read_text(role_template_path),
        "PROTOCOLO DE SESSAO\n"
        "Voce opera em uma sessao persistente propria por papel. "
        "Observe sempre o mesmo codebase local como fonte de verdade. "
        "Receba apenas o handoff explicito do papel anterior; nao reabra o escopo conceitual.",
        f"CONTEXTO DO REPOSITORIO\n{repo_context_text(repo_root, phase_id, wave_index, state)}",
        f"ONDA ANTERIOR\n{previous_wave_summary(state)}",
        (
            "INSTRUCOES FRESCAS EXTERNAS\n"
            f"source_path: {fresh_instruction_payload.get('source_path', '')}\n"
            f"consumed_at: {fresh_instruction_payload.get('consumed_at', '')}\n"
            "Consuma estas instrucoes nesta onda, trate-as como correcao de curso explicita do supervisor, "
            "e nao reutilize instrucoes antigas fora deste bloco.\n\n"
            f"{fresh_instruction_payload.get('content', '').strip()}"
        )
        if fresh_instruction_payload.get("content")
        else "",
        f"HANDOFF RECEBIDO\n{handoff_payload.strip()}",
        "FORMATO DE RESPOSTA\n"
        f"Responda apenas com um objeto JSON valido compativel com este schema:\n{json.dumps(output_model.model_json_schema(), indent=2, ensure_ascii=False)}",
    ]
    return "\n\n".join(section for section in sections if section)


def compose_resume_prompt(
    *,
    role: str,
    phase_id: str,
    wave_index: int,
    handoff_payload: str,
    output_model: type[BaseModel],
    fresh_instruction_payload: dict[str, str] | None = None,
) -> str:
    fresh_instruction_payload = fresh_instruction_payload or {}
    return "\n\n".join(
        [
            f"CONTINUE SUA SESSAO DO PAPEL {role.upper()}",
            f"phase_id: {phase_id}",
            f"wave_index: {wave_index}",
            "Use o mesmo codebase local como fonte de verdade.",
            "Receba apenas o handoff abaixo e responda sem recap global desnecessario.",
            (
                "INSTRUCOES FRESCAS EXTERNAS\n"
                f"source_path: {fresh_instruction_payload.get('source_path', '')}\n"
                f"consumed_at: {fresh_instruction_payload.get('consumed_at', '')}\n"
                "Consuma estas instrucoes nesta onda e trate-as como correcao de curso explicita do supervisor.\n\n"
                f"{fresh_instruction_payload.get('content', '').strip()}"
            )
            if fresh_instruction_payload.get("content")
            else "",
            f"HANDOFF RECEBIDO\n{handoff_payload.strip()}",
            "FORMATO DE RESPOSTA\n"
            f"Responda apenas com um objeto JSON valido compativel com este schema:\n{json.dumps(output_model.model_json_schema(), indent=2, ensure_ascii=False)}",
        ]
    )


def get_existing_codex_home_path() -> Path | None:
    candidates = []
    for env_var in ("CODEX_HOME", "USERPROFILE", "HOME"):
        value = os.environ.get(env_var)
        if not value:
            continue
        candidate = Path(value) if env_var == "CODEX_HOME" else Path(value) / ".codex"
        if candidate.exists():
            candidates.append(candidate)
    return candidates[0] if candidates else None


def seed_isolated_codex_home(target: Path) -> Path | None:
    source = get_existing_codex_home_path()
    target.mkdir(parents=True, exist_ok=True)
    if source is None:
        return None
    for item in source.iterdir():
        if item.name not in ALLOWED_CODEX_HOME_SEED_ITEMS:
            continue
        destination = target / item.name
        try:
            if item.is_dir():
                shutil.copytree(item, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(item, destination)
        except (PermissionError, FileNotFoundError, OSError):
            continue
    return source


def effective_codex_home() -> Path | None:
    return get_existing_codex_home_path()


def isolated_codex_config_content(*, runner_profile: str, model: str, reasoning_effort: str) -> str:
    profile_name = runner_profile or "agri-hydraulic-isolated"
    lines = [
        f'profile = "{profile_name}"',
        f'model = "{model}"',
        f'model_reasoning_effort = "{reasoning_effort}"',
        'approval_policy = "never"',
        'sandbox_mode = "workspace-write"',
        "",
        "[sandbox_workspace_write]",
        "network_access = true",
        "",
        f"[profiles.{profile_name}]",
        f'model = "{model}"',
        f'model_reasoning_effort = "{reasoning_effort}"',
        'approval_policy = "never"',
    ]
    return "\n".join(lines) + "\n"


def get_execution_profile(repo_root: Path, role: str) -> dict[str, Any]:
    base = load_json(repo_root / "automation" / "execution-profiles.json")
    profile_name = str(base.get("active_profile", "codex-balanced"))
    profiles = dict(base.get("profiles", {}))
    local_override_path = repo_root / "automation" / "execution-profiles.local.json"
    if local_override_path.exists():
        local = load_json(local_override_path)
        profile_name = str(local.get("active_profile", profile_name))
        profiles.update(local.get("profiles", {}))
    selected = profiles[profile_name]
    role_config = selected["roles"][role]
    return {
        "profile_name": profile_name,
        "engine": selected.get("engine", "openai-codex-cli"),
        "command": selected.get("command", "codex"),
        "runner_profile": selected.get("runner_profile", ""),
        "sandbox_strategy": selected.get("sandbox_strategy", "workspace-write"),
        "working_directory": selected.get("working_directory", "."),
        "model": role_config.get("model") or selected.get("defaults", {}).get("model", "gpt-5.4-mini"),
        "reasoning_effort": role_config.get("reasoning_effort")
        or selected.get("defaults", {}).get("reasoning_effort", "medium"),
        "mode": role_config.get("mode", "agent"),
        "entrypoint": role_config.get("entrypoint", ""),
    }


def apply_profile_overrides(
    profile: dict[str, Any],
    model_override: str | None,
    reasoning_effort_override: str | None,
) -> dict[str, Any]:
    updated = dict(profile)
    if model_override:
        updated["model"] = model_override
    if reasoning_effort_override:
        updated["reasoning_effort"] = reasoning_effort_override
    return updated


def codex_output_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    return enforce_closed_object_schema(schema)


def enforce_closed_object_schema(node: Any) -> Any:
    if isinstance(node, dict):
        processed = {key: enforce_closed_object_schema(value) for key, value in node.items()}
        if processed.get("type") == "object":
            processed["additionalProperties"] = False
            properties = processed.get("properties")
            if not isinstance(properties, dict):
                properties = {}
                processed["properties"] = properties
            processed["required"] = list(properties.keys())
        return processed
    if isinstance(node, list):
        return [enforce_closed_object_schema(item) for item in node]
    return node


def write_codex_config(
    codex_home: Path,
    profile: dict[str, Any],
) -> None:
    write_utf8(
        codex_home / "config.toml",
        isolated_codex_config_content(
            runner_profile=str(profile.get("runner_profile") or "agri-hydraulic-isolated"),
            model=str(profile.get("model") or "gpt-5.4-mini"),
            reasoning_effort=str(profile.get("reasoning_effort") or "medium"),
        ),
    )


def write_utf8(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.lstrip("\ufeff").encode("utf-8"))


def powershell_single_quoted(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def resolve_cli_command(command: str) -> str:
    candidates = []
    if os.name == "nt":
        candidates.extend(
            [
                shutil.which(f"{command}.cmd"),
                shutil.which(f"{command}.exe"),
                shutil.which(f"{command}.bat"),
                shutil.which(command),
            ]
        )
    else:
        candidates.append(shutil.which(command))
    for candidate in candidates:
        if candidate:
            return candidate
    raise RuntimeError(f"Comando `{command}` não encontrado no PATH.")


def build_runner_script(
    *,
    repo_root: Path,
    run_root: Path,
    role: str,
    profile: dict[str, Any],
    prompt_path: Path,
    output_schema_path: Path,
    last_message_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    codex_home: Path,
    resume_session_id: str | None,
) -> Path:
    command_path = resolve_cli_command(str(profile["command"]))
    runner_path = run_root / f"{role}_runner.ps1"
    working_directory = str((repo_root / profile.get("working_directory", ".")).resolve())
    if resume_session_id:
        lines = [
            "$ErrorActionPreference = 'Stop'",
            f"$env:CODEX_HOME = {powershell_single_quoted(str(codex_home))}",
            f"$commandPath = {powershell_single_quoted(command_path)}",
            f"$promptPath = {powershell_single_quoted(str(prompt_path))}",
            f"$lastMessagePath = {powershell_single_quoted(str(last_message_path))}",
            "$args = @('exec', 'resume')",
            f"$args += {powershell_single_quoted(resume_session_id)}",
            "$args += '-'",
            "$args += '--json'",
            "$args += '--skip-git-repo-check'",
            "$args += '-o'",
            f"$args += {powershell_single_quoted(str(last_message_path))}",
        ]
        if profile.get("model"):
            lines += [
                "$args += '--model'",
                f"$args += {powershell_single_quoted(str(profile['model']))}",
            ]
        if profile.get("reasoning_effort"):
            lines += [
                "$args += '-c'",
                f"$args += {powershell_single_quoted('model_reasoning_effort=\"' + str(profile['reasoning_effort']) + '\"')}",
            ]
        lines += [
            "$promptContent = [System.IO.File]::ReadAllText($promptPath, [System.Text.UTF8Encoding]::new($false))",
            "$promptContent | & $commandPath @args",
            "exit $LASTEXITCODE",
        ]
        write_utf8(runner_path, "\r\n".join(lines) + "\r\n")
        return runner_path

    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$env:CODEX_HOME = {powershell_single_quoted(str(codex_home))}",
        f"$commandPath = {powershell_single_quoted(command_path)}",
        f"$promptPath = {powershell_single_quoted(str(prompt_path))}",
        f"$outputSchemaPath = {powershell_single_quoted(str(output_schema_path))}",
        f"$lastMessagePath = {powershell_single_quoted(str(last_message_path))}",
        "$args = @('exec', '-', '--json', '--skip-git-repo-check')",
        "$args += '--cd'",
        f"$args += {powershell_single_quoted(working_directory)}",
        "$args += '--sandbox'",
        "$args += 'workspace-write'",
        "$args += '--add-dir'",
        f"$args += {powershell_single_quoted(str(repo_root))}",
    ]
    if profile.get("model"):
        lines += [
            "$args += '--model'",
            f"$args += {powershell_single_quoted(str(profile['model']))}",
        ]
    if profile.get("reasoning_effort"):
        lines += [
            "$args += '-c'",
            f"$args += {powershell_single_quoted('model_reasoning_effort=\"' + str(profile['reasoning_effort']) + '\"')}",
        ]
    lines += [
        "$args += '--output-schema'",
        f"$args += {powershell_single_quoted(str(output_schema_path))}",
        "$args += '-o'",
        f"$args += {powershell_single_quoted(str(last_message_path))}",
        "$promptContent = [System.IO.File]::ReadAllText($promptPath, [System.Text.UTF8Encoding]::new($false))",
        "$promptContent | & $commandPath @args",
        "exit $LASTEXITCODE",
    ]
    write_utf8(runner_path, "\r\n".join(lines) + "\r\n")
    return runner_path


def run_external_codex_agent(
    *,
    repo_root: Path,
    role: str,
    profile: dict[str, Any],
    prompt_text: str,
    output_model: type[BaseModel],
    run_root: Path,
    session_state: AgentSessionState,
) -> tuple[BaseModel, dict[str, str]]:
    prompt_path = run_root / f"{role}.prompt.md"
    output_schema_path = run_root / f"{role}.schema.json"
    runner_stdout_path = run_root / f"{role}.stdout.log"
    runner_stderr_path = run_root / f"{role}.stderr.log"
    last_message_path = run_root / f"{role}.last-message.json"
    shared_codex_home = effective_codex_home()
    if shared_codex_home is None:
        raise RuntimeError("Nenhum CODEX_HOME real foi encontrado para autenticação do Codex.")
    codex_home = shared_codex_home
    session_state.codex_home = str(codex_home)
    if profile.get("mode") == "skill" and profile.get("entrypoint"):
        prompt_text = f"Use the ${profile['entrypoint']} skill.\n\n{prompt_text}"
    write_utf8(prompt_path, prompt_text.strip() + "\n")
    write_utf8(output_schema_path, json.dumps(codex_output_schema(output_model), indent=2, ensure_ascii=False))
    runner_path = build_runner_script(
        repo_root=repo_root,
        run_root=run_root,
        role=role,
        profile=profile,
        prompt_path=prompt_path,
        output_schema_path=output_schema_path,
        last_message_path=last_message_path,
        stdout_path=runner_stdout_path,
        stderr_path=runner_stderr_path,
        codex_home=codex_home,
        resume_session_id=session_state.session_id or None,
    )
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        raise RuntimeError("PowerShell não encontrado no PATH.")
    with runner_stdout_path.open("w", encoding="utf-8") as stdout_handle, runner_stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_handle:
        process = subprocess.run(
            [pwsh, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(runner_path)],
            cwd=repo_root,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            check=False,
        )
    stdout_text = runner_stdout_path.read_text(encoding="utf-8") if runner_stdout_path.exists() else ""
    stderr_text = runner_stderr_path.read_text(encoding="utf-8") if runner_stderr_path.exists() else ""
    if process.returncode != 0:
        raise RuntimeError(
            f"Runner do papel `{role}` falhou (exit={process.returncode}). "
            f"stderr={stderr_text.strip()} stdout={stdout_text.strip()}"
        )
    if not last_message_path.exists():
        raise RuntimeError(f"Runner do papel `{role}` não gerou {last_message_path}")
    payload_text = last_message_path.read_text(encoding="utf-8").strip()
    session_id = extract_session_id(stdout_text) or session_state.session_id
    if session_id:
        session_state.session_id = session_id
    payload = parse_payload_text(payload_text)
    session_state.last_prompt_path = str(prompt_path)
    session_state.last_message_path = str(last_message_path)
    session_state.last_stdout_path = str(runner_stdout_path)
    session_state.last_stderr_path = str(runner_stderr_path)
    session_state.last_run_root = str(run_root)
    session_state.last_status = "completed"
    return output_model.model_validate(payload), {
        "run_root": str(run_root),
        "stdout_path": str(runner_stdout_path),
        "stderr_path": str(runner_stderr_path),
        "last_message_path": str(last_message_path),
        "session_id": session_state.session_id,
        "codex_home": str(codex_home),
        "mode": "resume" if session_state.last_wave_index else "bootstrap",
    }


def extract_session_id(stdout_text: str) -> str:
    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = event.get("type")
        if event_type == "thread.started" and isinstance(event.get("thread_id"), str):
            return event["thread_id"]
    return ""


def parse_payload_text(payload_text: str) -> Any:
    stripped = payload_text.strip()
    if not stripped:
        raise RuntimeError("Resposta final vazia do agente.")
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced_match:
        return json.loads(fenced_match.group(1))
    object_match = re.search(r"(\{.*\})", stripped, flags=re.DOTALL)
    if object_match:
        return json.loads(object_match.group(1))
    raise RuntimeError("Nao foi possivel extrair JSON valido da resposta final do agente.")


def get_or_create_agent_session(state: LoopState, role: str) -> AgentSessionState:
    if role not in state.agent_sessions:
        state.agent_sessions[role] = AgentSessionState(role=role)
    return state.agent_sessions[role]


def persist_handoff(run_root: Path, filename: str, payload: dict[str, Any]) -> Path:
    handoff_dir = run_root / "handoffs"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    path = handoff_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def run_preflight(repo_root: Path, backend: Backend) -> PreflightState:
    preflight = PreflightState(
        backend_requested=backend,
        codex_cli_found=shutil.which("codex") is not None,
        pwsh_found=(shutil.which("pwsh") is not None or shutil.which("powershell") is not None),
        codex_home_seed_found=False,
    )
    source_codex_home = get_existing_codex_home_path()
    if source_codex_home is not None:
        preflight.codex_home_seed_found = True
        preflight.codex_home_seed_path = str(source_codex_home)
    else:
        preflight.notes.append("Nenhum CODEX_HOME existente foi encontrado para seed de auth/config.")
    if not preflight.codex_cli_found:
        preflight.notes.append("Codex CLI não encontrado no PATH.")
    if not preflight.pwsh_found:
        preflight.notes.append("PowerShell (`pwsh` ou `powershell`) não encontrado no PATH.")
    if backend == "codex-exec-external" and preflight.codex_cli_found and preflight.pwsh_found:
        preflight.notes.append(
            "Preflight do backend real depende de execução em shell externo; a prova final deve ser feita fora desta sessão."
        )
    return preflight


def ensure_real_backend_ready(preflight: PreflightState) -> None:
    missing = []
    if not preflight.codex_cli_found:
        missing.append("codex CLI indisponível")
    if not preflight.pwsh_found:
        missing.append("PowerShell indisponível")
    if not preflight.codex_home_seed_found:
        missing.append("CODEX_HOME/auth local não encontrado")
    if missing:
        raise RuntimeError("Backend `codex-exec-external` não está pronto: " + "; ".join(missing))


def should_increment_low_value(verdict: str, policy: dict[str, Any]) -> bool:
    return verdict in set(policy.get("low_value_labels", []))


def architect_step_scaffold(phase_id: str, wave_index: int) -> ArchitectOutput:
    return ArchitectOutput(
        phase_id=phase_id,
        objective=f"Definir a onda {wave_index} dentro de {phase_id}.",
        wave_scope=["Preparar objetivo, critérios e arquivos-alvo."],
        acceptance_criteria=["Wave plan registrado de forma objetiva."],
        target_files=["AGENTS.md", "automation/", "prompts/", ".codex/"],
        main_risk="Confundir scaffold com backend real.",
        do_not_touch=["Arquitetura principal da decision_platform"],
        done_definition="A onda fica pronta quando o plano e os critérios estiverem explícitos.",
    )


def developer_step_scaffold(wave_index: int, plan: ArchitectOutput) -> DeveloperOutput:
    return DeveloperOutput(
        implementation_summary=[
            f"Wave {wave_index}: scaffold placeholder ativo.",
            f"Objetivo recebido: {plan.objective}",
        ],
        validations_to_run=["Validar runner", "Persistir estado do loop"],
        artifacts_to_generate=["docs/codex_dual_agent_runtime/loop_state.json"],
        docs_to_update=["automation/README.md"],
        commit_plan="Não commitar no modo scaffold automático.",
        handoff="Scaffold executado sem backend real.",
        limitations=["Modo scaffold não aciona o backend real `codex exec` externo."],
    )


def auditor_step_scaffold(wave_index: int) -> AuditorOutput:
    return AuditorOutput(
        verdict="moderate_progress",
        reasons=[f"Onda {wave_index}: scaffold persistiu estado e manteve o loop coerente."],
        risks=["Ainda não há execução real de agentes."],
        recommendation="continue",
        low_value_streak_relevant=False,
    )


def run_loop(
    *,
    repo_root: Path,
    phase_id: str,
    backend: Backend,
    run_id: str,
    max_waves: int,
    preflight: PreflightState,
    model_override: str | None,
    reasoning_effort_override: str | None,
) -> LoopState:
    run_root_path = runtime_scratch_dir(repo_root, run_id)
    state = LoopState(
        phase_id=phase_id,
        backend=backend,
        run_id=run_id,
        run_started_at=now_iso(),
        run_root=str(run_root_path),
        preflight=asdict(preflight),
        waves=[],
    )
    for role in ("architect", "developer", "auditor"):
        get_or_create_agent_session(state, role)
    policy = wave_policy(repo_root)
    persist_state(repo_root, state)

    for wave_index in range(1, max_waves + 1):
        state.active_wave_index = wave_index
        if backend == "codex-exec-external":
            ensure_real_backend_ready(preflight)
            wave_run_root = run_root_path / f"wave-{wave_index:02d}"
            architect_session = get_or_create_agent_session(state, "architect")
            developer_session = get_or_create_agent_session(state, "developer")
            auditor_session = get_or_create_agent_session(state, "auditor")

            architect_handoff_payload = json.dumps(
                {
                    "instruction": "Proponha a onda atual de forma incremental, sem reabrir arquitetura.",
                    "phase_target": phase_metadata(repo_root, phase_id).get("target", ""),
                    "wave_index": wave_index,
                    "supervisor_guidance": current_supervisor_guidance(repo_root),
                    "auditor_handoff_from_previous_wave": (
                        state.waves[-1].auditor_reasoning if state.waves else {"note": "Nenhuma onda anterior registrada."}
                    ),
                },
                indent=2,
                ensure_ascii=False,
            )
            architect_run_root = wave_run_root / "architect"
            architect_fresh_instruction = consume_role_fresh_instruction(repo_root, "architect", architect_run_root)
            architect_prompt = (
                compose_resume_prompt(
                    role="architect",
                    phase_id=phase_id,
                    wave_index=wave_index,
                    handoff_payload=architect_handoff_payload,
                    output_model=ArchitectOutput,
                    fresh_instruction_payload=architect_fresh_instruction,
                )
                if architect_session.session_id
                else compose_initial_prompt(
                    repo_root=repo_root,
                    role_template_path=repo_root / "prompts" / "PROMPT_ARCHITECT_WAVE_TEMPLATE.md",
                    role="architect",
                    phase_id=phase_id,
                    wave_index=wave_index,
                    state=state,
                    handoff_payload=architect_handoff_payload,
                    output_model=ArchitectOutput,
                    fresh_instruction_payload=architect_fresh_instruction,
                )
            )
            persist_handoff(
                wave_run_root,
                "architect_inbound.json",
                json.loads(architect_handoff_payload),
            )
            state.active_role = "architect"
            persist_state(repo_root, state)
            plan, architect_files = run_external_codex_agent(
                repo_root=repo_root,
                role="architect",
                profile=apply_profile_overrides(
                    get_execution_profile(repo_root, "architect"),
                    model_override,
                    reasoning_effort_override,
                ),
                prompt_text=architect_prompt,
                output_model=ArchitectOutput,
                run_root=architect_run_root,
                session_state=architect_session,
            )
            architect_session.last_wave_index = wave_index
            persist_handoff(
                wave_run_root,
                "architect_to_developer.json",
                plan.model_dump(),
            )
            developer_handoff_payload = json.dumps(
                {
                    "instruction": "Execute a onda atual no mesmo codebase e entregue um resumo da implementacao.",
                    "wave_index": wave_index,
                    "supervisor_guidance": current_supervisor_guidance(repo_root),
                    "architect_handoff": plan.model_dump(),
                },
                indent=2,
                ensure_ascii=False,
            )
            developer_run_root = wave_run_root / "developer"
            developer_fresh_instruction = consume_role_fresh_instruction(repo_root, "developer", developer_run_root)
            developer_prompt = (
                compose_resume_prompt(
                    role="developer",
                    phase_id=phase_id,
                    wave_index=wave_index,
                    handoff_payload=developer_handoff_payload,
                    output_model=DeveloperOutput,
                    fresh_instruction_payload=developer_fresh_instruction,
                )
                if developer_session.session_id
                else compose_initial_prompt(
                    repo_root=repo_root,
                    role_template_path=repo_root / "prompts" / "PROMPT_DEVELOPER_WAVE_TEMPLATE.md",
                    role="developer",
                    phase_id=phase_id,
                    wave_index=wave_index,
                    state=state,
                    handoff_payload=developer_handoff_payload,
                    output_model=DeveloperOutput,
                    fresh_instruction_payload=developer_fresh_instruction,
                )
            )
            state.active_role = "developer"
            persist_state(repo_root, state)
            dev_summary, developer_files = run_external_codex_agent(
                repo_root=repo_root,
                role="developer",
                profile=apply_profile_overrides(
                    get_execution_profile(repo_root, "developer"),
                    model_override,
                    reasoning_effort_override,
                ),
                prompt_text=developer_prompt,
                output_model=DeveloperOutput,
                run_root=developer_run_root,
                session_state=developer_session,
            )
            developer_session.last_wave_index = wave_index
            persist_handoff(
                wave_run_root,
                "developer_to_auditor.json",
                {
                    "architect_handoff": plan.model_dump(),
                    "developer_handoff": dev_summary.model_dump(),
                },
            )
            auditor_handoff_payload = json.dumps(
                {
                    "instruction": "Atue como gate honesto da onda atual.",
                    "wave_index": wave_index,
                    "supervisor_guidance": current_supervisor_guidance(repo_root),
                    "architect_handoff": plan.model_dump(),
                    "developer_handoff": dev_summary.model_dump(),
                },
                indent=2,
                ensure_ascii=False,
            )
            auditor_run_root = wave_run_root / "auditor"
            auditor_fresh_instruction = consume_role_fresh_instruction(repo_root, "auditor", auditor_run_root)
            auditor_prompt = (
                compose_resume_prompt(
                    role="auditor",
                    phase_id=phase_id,
                    wave_index=wave_index,
                    handoff_payload=auditor_handoff_payload,
                    output_model=AuditorOutput,
                    fresh_instruction_payload=auditor_fresh_instruction,
                )
                if auditor_session.session_id
                else compose_initial_prompt(
                    repo_root=repo_root,
                    role_template_path=repo_root / "prompts" / "PROMPT_AUDITOR_WAVE_TEMPLATE.md",
                    role="auditor",
                    phase_id=phase_id,
                    wave_index=wave_index,
                    state=state,
                    handoff_payload=auditor_handoff_payload,
                    output_model=AuditorOutput,
                    fresh_instruction_payload=auditor_fresh_instruction,
                )
            )
            state.active_role = "auditor"
            persist_state(repo_root, state)
            review, auditor_files = run_external_codex_agent(
                repo_root=repo_root,
                role="auditor",
                profile=apply_profile_overrides(
                    get_execution_profile(repo_root, "auditor"),
                    model_override,
                    reasoning_effort_override,
                ),
                prompt_text=auditor_prompt,
                output_model=AuditorOutput,
                run_root=auditor_run_root,
                session_state=auditor_session,
            )
            auditor_session.last_wave_index = wave_index
            persist_handoff(
                wave_run_root,
                "auditor_to_architect.json",
                review.model_dump(),
            )
            run_root = str(wave_run_root)
            developer_payload = dev_summary.model_dump()
            developer_payload["runner_files"] = developer_files
            architect_payload = plan.model_dump()
            architect_payload["runner_files"] = architect_files
            review_payload = review.model_dump()
            review_payload["runner_files"] = auditor_files
        else:
            plan = architect_step_scaffold(phase_id, wave_index)
            dev_summary = developer_step_scaffold(wave_index, plan)
            review = auditor_step_scaffold(wave_index)
            architect_payload = plan.model_dump()
            developer_payload = dev_summary.model_dump()
            review_payload = review.model_dump()
            run_root = ""

        wave = WaveState(
            wave_index=wave_index,
            phase_id=phase_id,
            architect_plan=architect_payload,
            developer_summary=developer_payload,
            auditor_verdict=review.verdict,
            auditor_reasoning=review_payload,
            commit_sha=current_head(repo_root),
            run_root=run_root,
        )
        state.waves.append(wave)
        state.active_role = ""
        state.consecutive_low_value = (
            state.consecutive_low_value + 1
            if should_increment_low_value(review.verdict, policy)
            else 0
        )
        persist_state(repo_root, state)
        if state.consecutive_low_value >= int(policy.get("consecutive_low_value_stop", 3)):
            state.stop_reason = "three_consecutive_low_value_waves"
            persist_state(repo_root, state)
            break

    if not state.stop_reason:
        state.stop_reason = "max_waves_reached"
        persist_state(repo_root, state)

    if bool(policy.get("final_stabilization_wave", True)):
        state.waves.append(
            WaveState(
                wave_index=len(state.waves) + 1,
                phase_id="final_stabilization",
                architect_plan={"objective": "final stabilization wave"},
                developer_summary={"handoff": "polish, stabilization, errors, release gate"},
                auditor_verdict="moderate_progress",
                auditor_reasoning={
                    "verdict": "moderate_progress",
                    "reasons": ["Final stabilization wave registrada."],
                    "risks": [],
                    "recommendation": "continue",
                    "low_value_streak_relevant": False,
                },
                commit_sha="",
                run_root="",
            )
        )
        persist_state(repo_root, state)

    return state


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-waves", type=int, default=10)
    parser.add_argument(
        "--backend",
        choices=["codex-exec-external", "scaffold"],
        default="codex-exec-external",
    )
    parser.add_argument("--model", default="")
    parser.add_argument("--reasoning-effort", default="")
    parser.add_argument("--preflight-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    run_id = args.run_id or datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
    preflight = run_preflight(repo_root, args.backend)
    persist_preflight(repo_root, preflight)

    if args.preflight_only:
        print(json.dumps(asdict(preflight), indent=2, ensure_ascii=False))
        return

    try:
        state = run_loop(
            repo_root=repo_root,
            phase_id=args.phase,
            backend=args.backend,
            run_id=run_id,
            max_waves=args.max_waves,
            preflight=preflight,
            model_override=args.model or None,
            reasoning_effort_override=args.reasoning_effort or None,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase_id": args.phase,
                    "backend": args.backend,
                    "error": str(exc),
                    "preflight": asdict(preflight),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        raise

    print(json.dumps(asdict(state), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
