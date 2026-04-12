import json
from pathlib import Path
import sys

import pytest

from zajecdaemon.config import Config
from zajecdaemon.opencode_runner import run_opencode

PROJECT_ROOT = Path(__file__).parent.parent
DUMMY_SCRIPT = PROJECT_ROOT / "scripts" / "dummy_opencode.py"


def _make_config(tmp_path: Path, *, max_retries: int = 5) -> Config:
    return Config(
        poll_interval_seconds=60,
        worker_concurrency=1,
        base_dir=tmp_path,
        repos=["owner/repo"],
        opencode_command=f"{sys.executable} {DUMMY_SCRIPT}",
        max_forbidden_retries=max_retries,
    )


@pytest.mark.asyncio
async def test_run_opencode_success(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    monkeypatch.setenv("DUMMY_OUTCOME", "success")
    result = await run_opencode(
        worktree, "https://github.com/owner/repo/pull/42", "owner/repo", 42, config
    )

    assert result.status == "success"
    assert result.session_id.startswith("sess_")
    assert result.log_path is not None
    assert result.log_path.exists()
    assert result.forbidden_retries == 0


@pytest.mark.asyncio
async def test_run_opencode_forbidden_once_then_success(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    monkeypatch.setenv("DUMMY_OUTCOME", "forbidden_once")
    result = await run_opencode(
        worktree, "https://github.com/owner/repo/pull/42", "owner/repo", 42, config
    )

    assert result.status == "success"
    assert result.forbidden_retries == 1
    assert result.session_id.startswith("sess_")
    assert result.log_path is not None
    assert result.log_path.exists()

    lines = result.log_path.read_text().strip().split("\n")
    json_lines = [json.loads(line) for line in lines if line.strip().startswith("{")]
    stop_events = [e for e in json_lines if e.get("type") == "assistant"]
    assert len(stop_events) >= 1


@pytest.mark.asyncio
async def test_run_opencode_forbidden_exhausted(tmp_path, monkeypatch):
    config = _make_config(tmp_path, max_retries=2)
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    monkeypatch.setenv("DUMMY_OUTCOME", "forbidden_always")
    result = await run_opencode(
        worktree, "https://github.com/owner/repo/pull/42", "owner/repo", 42, config
    )

    assert result.status == "forbidden_exhausted"
    assert result.forbidden_retries == 2
    assert result.session_id.startswith("sess_")


@pytest.mark.asyncio
async def test_run_opencode_failure(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    monkeypatch.setenv("DUMMY_OUTCOME", "failure")
    result = await run_opencode(
        worktree, "https://github.com/owner/repo/pull/42", "owner/repo", 42, config
    )

    assert result.status == "failed"
    assert result.session_id.startswith("sess_")


@pytest.mark.asyncio
async def test_run_opencode_log_path(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    monkeypatch.setenv("DUMMY_OUTCOME", "success")
    result = await run_opencode(
        worktree, "https://github.com/owner/repo/pull/42", "owner/repo", 42, config
    )

    assert result.log_path is not None
    log_dir = result.log_path.parent
    assert log_dir == tmp_path / "logs" / "owner__repo" / "42"


@pytest.mark.asyncio
async def test_run_opencode_nonexistent_command(tmp_path):
    config = Config(
        poll_interval_seconds=60,
        worker_concurrency=1,
        base_dir=tmp_path,
        repos=["owner/repo"],
        opencode_command="/nonexistent/command",
    )
    worktree = tmp_path / "worktree"
    worktree.mkdir()

    result = await run_opencode(
        worktree, "https://github.com/owner/repo/pull/42", "owner/repo", 42, config
    )

    assert result.status == "failed"
