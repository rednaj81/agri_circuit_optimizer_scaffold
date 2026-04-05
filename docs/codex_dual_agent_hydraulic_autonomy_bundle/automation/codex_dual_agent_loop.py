"""
Esqueleto de orquestração local para um loop Architect -> Developer -> Auditor
usando Codex via MCP server e Agents SDK.

Requer:
- Codex CLI disponível
- `codex mcp-server`
- pacote `openai-agents` instalado
- Python 3.11+

Uso esperado:
    python automation/codex_dual_agent_loop.py --repo-root .. --phase phase_0

Observação:
Este arquivo é um scaffold para o Codex completar e adaptar no branch.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal

# Dependência esperada na implementação real:
# from agents import Agent, Runner
# from agents.mcp import MCPServerStdio

Verdict = Literal[
    "significant_progress",
    "moderate_progress",
    "low_significance",
    "no_progress",
    "regression",
]

@dataclass
class WaveState:
    wave_index: int
    phase_id: str
    architect_plan: str = ""
    developer_summary: str = ""
    auditor_verdict: str = ""
    auditor_reasoning: str = ""
    commit_sha: str = ""

@dataclass
class LoopState:
    phase_id: str
    waves: list[WaveState]
    consecutive_low_value: int = 0
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

def persist_state(repo_root: Path, state: LoopState) -> None:
    out = repo_root / "docs" / "codex_dual_agent_runtime"
    out.mkdir(parents=True, exist_ok=True)
    (out / "loop_state.json").write_text(
        json.dumps(asdict(state), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

async def architect_step(repo_root: Path, phase_id: str, wave_index: int) -> str:
    # Placeholder: o Codex deve substituir por chamada real ao MCP server com Agent Architect
    return f"[Architect] phase={phase_id} wave={wave_index}: definir objetivo, critérios e arquivos-alvo."

async def developer_step(repo_root: Path, plan: str, wave_index: int) -> str:
    # Placeholder: o Codex deve substituir por chamada real ao MCP server com Agent Developer
    return f"[Developer] wave={wave_index}: implementar plano, rodar testes, preparar commit."

async def auditor_step(repo_root: Path, plan: str, developer_summary: str, wave_index: int) -> tuple[Verdict, str]:
    # Placeholder: o Codex deve substituir por chamada real ao MCP server com Agent Auditor
    verdict: Verdict = "moderate_progress"
    reason = f"[Auditor] wave={wave_index}: progresso moderado; continuar."
    return verdict, reason

def should_increment_low_value(verdict: str) -> bool:
    return verdict in {"low_significance", "no_progress", "regression"}

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--max-waves", type=int, default=10)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    state = LoopState(phase_id=args.phase, waves=[])

    for wave_index in range(1, args.max_waves + 1):
        plan = await architect_step(repo_root, args.phase, wave_index)
        dev_summary = await developer_step(repo_root, plan, wave_index)
        verdict, reasoning = await auditor_step(repo_root, plan, dev_summary, wave_index)

        try:
            commit_sha = run_git(repo_root, "rev-parse", "HEAD")
        except Exception:
            commit_sha = ""

        wave = WaveState(
            wave_index=wave_index,
            phase_id=args.phase,
            architect_plan=plan,
            developer_summary=dev_summary,
            auditor_verdict=verdict,
            auditor_reasoning=reasoning,
            commit_sha=commit_sha,
        )
        state.waves.append(wave)

        if should_increment_low_value(verdict):
            state.consecutive_low_value += 1
        else:
            state.consecutive_low_value = 0

        persist_state(repo_root, state)

        if state.consecutive_low_value >= 3:
            state.stop_reason = "three_consecutive_low_value_waves"
            persist_state(repo_root, state)
            break

    if not state.stop_reason:
        state.stop_reason = "max_waves_reached"
        persist_state(repo_root, state)

    # Onda final de estabilização
    final_plan = "[Architect] final stabilization wave"
    final_dev = "[Developer] polish, stabilization, errors, release gate"
    final_verdict = "moderate_progress"
    final_reason = "[Auditor] final stabilization reviewed"
    state.waves.append(
        WaveState(
            wave_index=len(state.waves) + 1,
            phase_id="final_stabilization",
            architect_plan=final_plan,
            developer_summary=final_dev,
            auditor_verdict=final_verdict,
            auditor_reasoning=final_reason,
            commit_sha="",
        )
    )
    persist_state(repo_root, state)

if __name__ == "__main__":
    asyncio.run(main())
