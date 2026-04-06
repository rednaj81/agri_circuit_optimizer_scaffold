from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_STALL_TIMEOUT_SECONDS = 1800
DEFAULT_BOOTSTRAP_GRACE_SECONDS = 180


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def runtime_dir(repo_root: Path) -> Path:
    out = repo_root / "docs" / "codex_dual_agent_runtime"
    out.mkdir(parents=True, exist_ok=True)
    return out


def api_runtime_dir(repo_root: Path) -> Path:
    out = runtime_dir(repo_root) / "api"
    out.mkdir(parents=True, exist_ok=True)
    return out


def runtime_policy_override_path(repo_root: Path) -> Path:
    return runtime_dir(repo_root) / "wave_policy.override.json"


def desired_run_path(repo_root: Path) -> Path:
    return api_runtime_dir(repo_root) / "desired_run.json"


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False)
    path.write_bytes(serialized.lstrip("\ufeff").encode("utf-8"))


def tail_text(path: Path, max_chars: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def process_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return str(pid) in (result.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class SupervisorService:
    def __init__(self, repo_root: Path, host: str, port: int) -> None:
        self.repo_root = repo_root
        self.host = host
        self.port = port
        self.runtime_root = runtime_dir(repo_root)
        self.api_root = api_runtime_dir(repo_root)
        self.process_state_path = self.api_root / "process_state.json"
        self.server_state_path = self.api_root / "server_state.json"
        self.write_server_state()

    def write_server_state(self) -> None:
        write_json(
            self.server_state_path,
            {
                "host": self.host,
                "port": self.port,
                "repo_root": str(self.repo_root),
                "started_at": now_iso(),
                "pid": os.getpid(),
            },
        )

    def load_process_state(self) -> dict[str, Any]:
        payload = read_json(self.process_state_path)
        return payload if isinstance(payload, dict) else {}

    def save_process_state(self, payload: dict[str, Any]) -> None:
        write_json(self.process_state_path, payload)

    def load_desired_run(self) -> dict[str, Any]:
        payload = read_json(desired_run_path(self.repo_root))
        return payload if isinstance(payload, dict) else {}

    def save_desired_run(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = now_iso()
        write_json(desired_run_path(self.repo_root), payload)

    def current_process_snapshot(self) -> dict[str, Any]:
        state = self.load_process_state()
        pid = int(state.get("pid") or 0)
        running = process_is_running(pid) if pid else False
        if state:
            state["running"] = running
        return state

    def build_health_payload(self) -> dict[str, Any]:
        process = self.current_process_snapshot()
        desired = self.load_desired_run()
        supervisor_state = read_json(self.runtime_root / "supervisor_state.json") or {}
        loop_state = read_json(self.runtime_root / "loop_state.json") or {}

        process_running = bool(process.get("running"))
        stop_reason = str(loop_state.get("stop_reason") or supervisor_state.get("stop_reason") or "")
        active_role = str(supervisor_state.get("active_role") or loop_state.get("active_role") or "")
        active_wave_index = int(supervisor_state.get("active_wave_index") or loop_state.get("active_wave_index") or 0)

        last_updated_at = supervisor_state.get("last_updated_at") or loop_state.get("last_updated_at")
        started_at = process.get("started_at")
        last_updated_dt = parse_iso_datetime(last_updated_at)
        started_dt = parse_iso_datetime(started_at)
        now = datetime.now(timezone.utc)

        seconds_since_update = None
        if last_updated_dt is not None:
            seconds_since_update = max(0, int((now - last_updated_dt).total_seconds()))

        seconds_since_start = None
        if started_dt is not None:
            seconds_since_start = max(0, int((now - started_dt).total_seconds()))

        stall_timeout_seconds = int(desired.get("stall_timeout_seconds") or DEFAULT_STALL_TIMEOUT_SECONDS)
        bootstrap_grace_seconds = int(desired.get("bootstrap_grace_seconds") or DEFAULT_BOOTSTRAP_GRACE_SECONDS)

        state = "idle"
        stalled = False
        reason = ""

        if stop_reason:
            state = "terminal"
            reason = stop_reason
        elif not process_running:
            state = "idle"
            reason = "process_not_running"
        elif not active_role:
            state = "bootstrapping"
            if seconds_since_start is not None and seconds_since_start > bootstrap_grace_seconds:
                stalled = True
                state = "stalled"
                reason = "bootstrap_timeout"
            else:
                reason = "waiting_first_role"
        else:
            state = "running"
            if seconds_since_update is not None and seconds_since_update > stall_timeout_seconds:
                stalled = True
                state = "stalled"
                reason = "stale_supervisor_state"
            else:
                reason = "active_progress"

        return {
            "state": state,
            "stalled": stalled,
            "reason": reason,
            "process_running": process_running,
            "active_role": active_role,
            "active_wave_index": active_wave_index,
            "last_updated_at": last_updated_at or "",
            "seconds_since_update": seconds_since_update,
            "seconds_since_start": seconds_since_start,
            "stall_timeout_seconds": stall_timeout_seconds,
            "bootstrap_grace_seconds": bootstrap_grace_seconds,
            "stop_reason": stop_reason,
        }

    def build_status_payload(self) -> dict[str, Any]:
        return {
            "server": read_json(self.server_state_path),
            "process": self.current_process_snapshot(),
            "desired_run": self.load_desired_run(),
            "health": self.build_health_payload(),
            "preflight": read_json(self.runtime_root / "preflight.json"),
            "policy_override": read_json(runtime_policy_override_path(self.repo_root)),
            "supervisor_state": read_json(self.runtime_root / "supervisor_state.json"),
            "agent_sessions": read_json(self.runtime_root / "agent_sessions.json"),
            "loop_state": read_json(self.runtime_root / "loop_state.json"),
        }

    def get_policy_payload(self) -> dict[str, Any]:
        base_path = self.repo_root / "automation" / "wave_policy.yaml"
        base_text = base_path.read_text(encoding="utf-8")
        override_path = runtime_policy_override_path(self.repo_root)
        return {
            "base_path": str(base_path),
            "base_yaml": base_text,
            "override_path": str(override_path),
            "override": read_json(override_path),
        }

    def update_policy_override(self, payload: dict[str, Any]) -> dict[str, Any]:
        allowed_keys = {
            "max_waves",
            "consecutive_low_value_stop",
            "low_value_labels",
            "final_stabilization_wave",
            "commit_every_wave",
        }
        filtered = {key: value for key, value in payload.items() if key in allowed_keys}
        override_path = runtime_policy_override_path(self.repo_root)
        write_json(override_path, filtered)
        return {
            "updated": True,
            "override_path": str(override_path),
            "override": filtered,
        }

    def clear_policy_override(self) -> dict[str, Any]:
        override_path = runtime_policy_override_path(self.repo_root)
        if override_path.exists():
            override_path.unlink()
        return {"cleared": True, "override_path": str(override_path)}

    def run_preflight(
        self,
        *,
        phase: str,
        backend: str,
        model: str,
        reasoning_effort: str,
    ) -> dict[str, Any]:
        script = self.repo_root / "scripts" / "run_codex_dual_agent_loop.ps1"
        pwsh = shutil_which_pwsh()
        result = subprocess.run(
            [
                pwsh,
                "-ExecutionPolicy",
                "Bypass",
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(script),
                "-Phase",
                phase,
                "-Backend",
                backend,
                "-Model",
                model,
                "-ReasoningEffort",
                reasoning_effort,
                "-PreflightOnly",
            ],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "preflight": read_json(self.runtime_root / "preflight.json"),
        }

    def start_loop(
        self,
        *,
        phase: str,
        backend: str,
        max_waves: int,
        model: str,
        reasoning_effort: str,
    ) -> dict[str, Any]:
        current = self.current_process_snapshot()
        current_desired = self.load_desired_run()
        desired = {
            "active": True,
            "phase": phase,
            "backend": backend,
            "max_waves": max_waves,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "restart_on_terminal_stop": bool(current_desired.get("restart_on_terminal_stop", False)),
            "stall_timeout_seconds": int(
                current_desired.get("stall_timeout_seconds") or DEFAULT_STALL_TIMEOUT_SECONDS
            ),
            "bootstrap_grace_seconds": int(
                current_desired.get("bootstrap_grace_seconds") or DEFAULT_BOOTSTRAP_GRACE_SECONDS
            ),
        }
        self.save_desired_run(desired)
        if current.get("running"):
            return {"started": False, "reason": "already_running", "process": current}

        script = self.repo_root / "scripts" / "run_codex_dual_agent_loop.ps1"
        pwsh = shutil_which_pwsh()
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_id = f"run-{timestamp}"
        run_root = str(runtime_dir(self.repo_root) / "runs" / run_id)
        stdout_path = self.api_root / f"loop-{timestamp}.stdout.log"
        stderr_path = self.api_root / f"loop-{timestamp}.stderr.log"
        stdout_handle = stdout_path.open("w", encoding="utf-8")
        stderr_handle = stderr_path.open("w", encoding="utf-8")
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        process = subprocess.Popen(
            [
                pwsh,
                "-ExecutionPolicy",
                "Bypass",
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(script),
                "-Phase",
                phase,
                "-RunId",
                run_id,
                "-Backend",
                backend,
                "-MaxWaves",
                str(max_waves),
                "-Model",
                model,
                "-ReasoningEffort",
                reasoning_effort,
            ],
            cwd=self.repo_root,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            creationflags=creationflags,
        )
        stdout_handle.close()
        stderr_handle.close()
        state = {
            "pid": process.pid,
            "started_at": now_iso(),
            "phase": phase,
            "backend": backend,
            "run_id": run_id,
            "run_root": run_root,
            "max_waves": max_waves,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "running": True,
        }
        self.save_process_state(state)
        return {"started": True, "process": state, "desired_run": desired}

    def stop_loop(self, *, clear_desired_run: bool = True) -> dict[str, Any]:
        state = self.current_process_snapshot()
        pid = int(state.get("pid") or 0)
        if clear_desired_run:
            desired = self.load_desired_run()
            desired["active"] = False
            self.save_desired_run(desired)
        if not pid or not state.get("running"):
            return {"stopped": False, "reason": "not_running", "process": state}
        if os.name == "nt":
            result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, check=False)
            state["stop_stdout"] = result.stdout
            state["stop_stderr"] = result.stderr
        else:
            os.kill(pid, signal.SIGTERM)
        state["running"] = False
        state["stopped_at"] = now_iso()
        self.save_process_state(state)
        return {"stopped": True, "process": state}

    def restart_loop(
        self,
        *,
        phase: str,
        backend: str,
        max_waves: int,
        model: str,
        reasoning_effort: str,
    ) -> dict[str, Any]:
        stop_result = self.stop_loop(clear_desired_run=False)
        start_result = self.start_loop(
            phase=phase,
            backend=backend,
            max_waves=max_waves,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        return {"stop": stop_result, "start": start_result}

    def log_payload(self) -> dict[str, Any]:
        process = self.current_process_snapshot()
        stdout_path = Path(process.get("stdout_path", "")) if process.get("stdout_path") else None
        stderr_path = Path(process.get("stderr_path", "")) if process.get("stderr_path") else None
        return {
            "process": process,
            "stdout": tail_text(stdout_path) if stdout_path else "",
            "stderr": tail_text(stderr_path) if stderr_path else "",
        }

    def get_desired_run_payload(self) -> dict[str, Any]:
        return {
            "path": str(desired_run_path(self.repo_root)),
            "desired_run": self.load_desired_run(),
        }

    def update_desired_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.load_desired_run()
        allowed_keys = {
            "active",
            "phase",
            "backend",
            "max_waves",
            "model",
            "reasoning_effort",
            "restart_on_terminal_stop",
            "stall_timeout_seconds",
            "bootstrap_grace_seconds",
        }
        for key, value in payload.items():
            if key in allowed_keys:
                current[key] = value
        self.save_desired_run(current)
        return {"updated": True, "desired_run": current}


def shutil_which_pwsh() -> str:
    for candidate in ("pwsh", "powershell"):
        result = subprocess.run(["where", candidate], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            first = (result.stdout or "").splitlines()[0].strip()
            if first:
                return first
    raise RuntimeError("PowerShell não encontrado no PATH.")


class SupervisorHandler(BaseHTTPRequestHandler):
    service: SupervisorService

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw.strip():
            return {}
        return json.loads(raw)

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(HTTPStatus.OK, {"ok": True, "timestamp": now_iso()})
            return
        if parsed.path == "/state":
            self._send(HTTPStatus.OK, self.service.build_status_payload())
            return
        if parsed.path == "/logs":
            self._send(HTTPStatus.OK, self.service.log_payload())
            return
        if parsed.path == "/policy":
            self._send(HTTPStatus.OK, self.service.get_policy_payload())
            return
        if parsed.path == "/desired-run":
            self._send(HTTPStatus.OK, self.service.get_desired_run_payload())
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body = self._read_json_body()
        phase = str(body.get("phase") or "phase_0")
        backend = str(body.get("backend") or "codex-exec-external")
        max_waves = int(body.get("max_waves") or 10)
        model = str(body.get("model") or "gpt-5.4")
        reasoning_effort = str(body["reasoning_effort"]) if "reasoning_effort" in body else ""

        if parsed.path == "/preflight":
            payload = self.service.run_preflight(
                phase=phase,
                backend=backend,
                model=model,
                reasoning_effort=reasoning_effort,
            )
            self._send(HTTPStatus.OK, payload)
            return
        if parsed.path == "/start":
            payload = self.service.start_loop(
                phase=phase,
                backend=backend,
                max_waves=max_waves,
                model=model,
                reasoning_effort=reasoning_effort,
            )
            self._send(HTTPStatus.OK, payload)
            return
        if parsed.path == "/stop":
            self._send(HTTPStatus.OK, self.service.stop_loop())
            return
        if parsed.path == "/restart":
            payload = self.service.restart_loop(
                phase=phase,
                backend=backend,
                max_waves=max_waves,
                model=model,
                reasoning_effort=reasoning_effort,
            )
            self._send(HTTPStatus.OK, payload)
            return
        if parsed.path == "/policy":
            self._send(HTTPStatus.OK, self.service.update_policy_override(body))
            return
        if parsed.path == "/desired-run":
            self._send(HTTPStatus.OK, self.service.update_desired_run(body))
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_DELETE(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/policy":
            self._send(HTTPStatus.OK, self.service.clear_policy_override())
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def make_handler(service: SupervisorService) -> type[SupervisorHandler]:
    class BoundHandler(SupervisorHandler):
        pass

    BoundHandler.service = service
    return BoundHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    service = SupervisorService(repo_root=repo_root, host=args.host, port=args.port)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(service))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
