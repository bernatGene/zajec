import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import shlex

from zajecdaemon.config import Config

logger = logging.getLogger(__name__)

RETRY_MESSAGE = (
    "you used a forbidden command. continue without using forbidden commands."
)


@dataclass
class RunnerResult:
    session_id: str = ""
    status: str = ""
    log_path: Path | None = None
    forbidden_retries: int = 0


@dataclass
class _ParsedOutput:
    session_id: str = ""
    step_finish_reason: str = ""


def _log_path(base_dir: Path, repo: str, pr_number: int) -> Path:
    slug = repo.replace("/", "__")
    dir_path = base_dir / "logs" / slug / str(pr_number)
    dir_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return dir_path / f"{ts}.log"


async def _run_command(
    cmd: list[str],
    cwd: Path,
    log_file: Path,
) -> _ParsedOutput:
    parsed = _ParsedOutput()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(cwd),
    )

    with log_file.open("a") as f:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            decoded = line.decode().rstrip("\n")
            if not decoded:
                continue
            f.write(decoded + "\n")
            try:
                event = json.loads(decoded)
            except (json.JSONDecodeError, ValueError):
                logger.debug("Non-JSON line: %s", decoded)
                continue
            if session_id := event.get("sessionID"):
                if not parsed.session_id:
                    parsed.session_id = session_id
            if event.get("type") == "step_finish":
                reason = event.get("reason") or event.get("part", {}).get("reason", "")
                parsed.step_finish_reason = reason

    await proc.wait()
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
    log_file = _log_path(config.base_dir, repo, pr_number)
    session_id = ""
    forbidden_count = 0
    prompt = f"review {pr_url}"

    while True:
        cmd = shlex.split(config.opencode_command) + ["run"]
        if session_id:
            cmd.extend(["-s", session_id])
            cmd.append(RETRY_MESSAGE)
        else:
            cmd.append(prompt)
        cmd.extend(["--agent", config.opencode_agent, "--format", "json"])

        try:
            parsed = await _run_command(cmd, worktree, log_file)
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
            logger.info(
                "Forbidden command, retry %d/%d for %s#%d",
                forbidden_count,
                config.max_forbidden_retries,
                repo,
                pr_number,
            )
            continue

        status = "failed"
        if parsed.step_finish_reason == "tool-calls":
            status = "forbidden_exhausted"

        return RunnerResult(
            session_id=session_id,
            status=status,
            log_path=log_file,
            forbidden_retries=forbidden_count,
        )
