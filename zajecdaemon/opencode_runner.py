import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shlex
from typing import Literal

from zajecdaemon.config import Config

logger = logging.getLogger(__name__)

RETRY_MESSAGE = (
    "you used a forbidden command. continue without using forbidden commands."
)

Status = Literal["success", "failed", "forbidden_exhausted"]

LOG_HEAD = 2
LOG_TAIL = 2


@dataclass
class RunnerResult:
    status: Status
    session_id: str = ""
    log_path: Path | None = None
    forbidden_retries: int = 0


@dataclass
class _ParsedOutput:
    session_id: str = ""
    step_finish_reason: str = ""
    last_tool_use: dict | None = None


def _log_path(base_dir: Path, repo: str, pr_number: int) -> Path:
    slug = repo.replace("/", "__")
    dir_path = base_dir / "logs" / slug / str(pr_number)
    dir_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return dir_path / f"{ts}.log"


def _truncate_content(content: str) -> str:
    lines = content.splitlines()
    if len(lines) <= LOG_HEAD + LOG_TAIL:
        return content
    skipped = len(lines) - LOG_HEAD - LOG_TAIL
    return "\n".join(
        lines[:LOG_HEAD] + [f"... ({skipped} more lines) ..."] + lines[-LOG_TAIL:]
    )


async def _run_command(
    cmd: list[str],
    cwd: Path,
    log_file: Path,
    timeout: float,
) -> _ParsedOutput:
    parsed = _ParsedOutput()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(cwd),
        limit=1024 * 1024,
    )
    try:
        async with asyncio.timeout(timeout):
            with log_file.open("a", buffering=1) as f:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode().rstrip("\n")
                    if not decoded:
                        continue
                    try:
                        event = json.loads(decoded)
                    except (json.JSONDecodeError, ValueError):
                        logger.debug("Non-JSON line: %s", decoded)
                        continue
                    if session_id := event.get("sessionID"):
                        if not parsed.session_id:
                            parsed.session_id = session_id
                    if event.get("type") == "step_finish":
                        reason = event.get("reason") or event.get("part", {}).get(
                            "reason", ""
                        )
                        if parsed.step_finish_reason != "stop":
                            parsed.step_finish_reason = reason
                    if event.get("type") == "tool_use":
                        parsed.last_tool_use = event.get("part", {})
                    if event.get("type") == "assistant":
                        if "content" in event:
                            event["content"] = _truncate_content(event["content"])
                        f.write(json.dumps(event) + "\n")
            await proc.wait()
    except asyncio.TimeoutError:
        proc.kill()
        try:
            await proc.wait()
        except Exception:
            pass
        logger.warning("opencode timed out after %ds", int(timeout))
    except asyncio.CancelledError:
        proc.terminate()
        try:
            await proc.wait()
        except Exception:
            pass
        raise
    else:
        if proc.returncode != 0:
            logger.warning("opencode exited with code %d", proc.returncode)
    return parsed


async def run_opencode(
    worktree: Path,
    pr_url: str,
    repo: str,
    pr_number: int,
    config: Config,
) -> RunnerResult:
    try:
        log_file = _log_path(config.base_dir, repo, pr_number)
    except OSError:
        logger.exception("Failed to create log directory for %s#%d", repo, pr_number)
        return RunnerResult(status="failed")

    session_id = ""
    forbidden_count = 0
    prompt = f"review {pr_url}"

    try:
        base_cmd = shlex.split(config.opencode_command)
    except ValueError:
        logger.exception("Invalid opencode_command: %s", config.opencode_command)
        return RunnerResult(status="failed", log_path=log_file)

    while True:
        cmd = base_cmd + ["run"]
        if session_id:
            cmd.extend(["-s", session_id])
            cmd.append(RETRY_MESSAGE)
        else:
            cmd.append(prompt)
        cmd.extend(["--model", config.opencode_model])
        cmd.extend(["--agent", config.opencode_agent, "--format", "json"])

        try:
            parsed = await _run_command(
                cmd, worktree, log_file, config.opencode_timeout_seconds
            )
        except Exception:
            logger.exception("opencode command failed for %s#%d", repo, pr_number)
            return RunnerResult(
                session_id=session_id,
                status="failed",
                log_path=log_file,
                forbidden_retries=forbidden_count,
            )

        session_id = session_id or parsed.session_id

        if parsed.step_finish_reason == "stop":
            return RunnerResult(
                session_id=session_id,
                status="success",
                log_path=log_file,
                forbidden_retries=forbidden_count,
            )

        if (
            parsed.step_finish_reason == "tool-calls"
            and session_id
            and forbidden_count < config.max_forbidden_retries
        ):
            forbidden_count += 1
            tool_info = ""
            if parsed.last_tool_use:
                tool_name = parsed.last_tool_use.get("tool", "")
                tool_input = parsed.last_tool_use.get("input", "")
                if tool_input and len(tool_input) > 50:
                    tool_input = "..." + tool_input[-47:]
                tool_info = f" ({tool_name}: {tool_input})" if tool_name else ""
            logger.info(
                "Forbidden command%s, retry %d/%d for %s#%d",
                tool_info,
                forbidden_count,
                config.max_forbidden_retries,
                repo,
                pr_number,
            )
            continue

        status: Status = "failed"
        if parsed.step_finish_reason == "tool-calls":
            status = "forbidden_exhausted"

        return RunnerResult(
            session_id=session_id,
            status=status,
            log_path=log_file,
            forbidden_retries=forbidden_count,
        )
