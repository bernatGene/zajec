from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from zajecdaemon.config import Config
from zajecdaemon.models import PRState, Task
from zajecdaemon.state import StateStore
from zajecdaemon.worker import process_task


def _make_config(tmp_path: Path) -> Config:
    return Config(
        poll_interval_seconds=60,
        worker_concurrency=1,
        base_dir=tmp_path,
        repos=["owner/repo"],
    )


def _make_task(repo: str = "owner/repo", pr_number: int = 42) -> Task:
    return Task(
        repo=repo,
        pr_number=pr_number,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha="abc123",
        enqueued_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_process_task_new_worktree(tmp_path):
    config = _make_config(tmp_path)
    state = StateStore(tmp_path / "state" / "state.json")
    pr_state = PRState(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha_seen="abc123",
        last_zajec_comment_id_seen=99,
    )
    state.set(pr_state)

    with (
        patch(
            "zajecdaemon.worker.ensure_controller_clone", new_callable=AsyncMock
        ) as mock_clone,
        patch("zajecdaemon.worker.fetch_pr_ref", new_callable=AsyncMock) as mock_fetch,
        patch(
            "zajecdaemon.worker.worktree_path",
            return_value=Path("/tmp/wt"),
        ),
        patch(
            "zajecdaemon.worker.ensure_worktree",
            new_callable=AsyncMock,
            return_value=Path("/tmp/wt"),
        ) as mock_wt,
    ):
        task = _make_task()
        await process_task(task, config, state)

    mock_clone.assert_awaited_once_with(config.base_dir, "owner/repo")
    mock_fetch.assert_awaited_once_with(config.base_dir, "owner/repo", 42)
    mock_wt.assert_awaited_once_with(config.base_dir, "owner/repo", 42)

    updated = state.get("owner/repo", 42)
    assert updated is not None
    assert updated.head_sha_processed == "abc123"
    assert updated.last_zajec_comment_id_processed == 99
    assert updated.last_run_status == "worktree_ready"


@pytest.mark.asyncio
async def test_process_task_existing_worktree_skips_fetch(tmp_path):
    config = _make_config(tmp_path)
    state = StateStore(tmp_path / "state" / "state.json")
    pr_state = PRState(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha_seen="abc123",
        last_zajec_comment_id_seen=99,
    )
    state.set(pr_state)

    wt_path = tmp_path / "repos" / "owner__repo" / "worktrees" / "42"
    wt_path.mkdir(parents=True)

    with (
        patch(
            "zajecdaemon.worker.ensure_controller_clone", new_callable=AsyncMock
        ) as mock_clone,
        patch("zajecdaemon.worker.fetch_pr_ref", new_callable=AsyncMock) as mock_fetch,
        patch(
            "zajecdaemon.worker.ensure_worktree",
            new_callable=AsyncMock,
            return_value=wt_path,
        ) as mock_wt,
    ):
        task = _make_task()
        await process_task(task, config, state)

    mock_clone.assert_awaited_once_with(config.base_dir, "owner/repo")
    mock_fetch.assert_not_awaited()
    mock_wt.assert_awaited_once_with(config.base_dir, "owner/repo", 42)

    updated = state.get("owner/repo", 42)
    assert updated is not None
    assert updated.last_run_status == "worktree_ready"


@pytest.mark.asyncio
async def test_process_task_updates_state_on_failure(tmp_path):
    config = _make_config(tmp_path)
    state = StateStore(tmp_path / "state" / "state.json")
    pr_state = PRState(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha_seen="abc123",
    )
    state.set(pr_state)

    with patch(
        "zajecdaemon.worker.ensure_controller_clone",
        new_callable=AsyncMock,
        side_effect=RuntimeError("clone failed"),
    ):
        task = _make_task()
        await process_task(task, config, state)

    updated = state.get("owner/repo", 42)
    assert updated is not None
    assert updated.last_run_status == "failed"


@pytest.mark.asyncio
async def test_process_task_fetch_failure(tmp_path):
    config = _make_config(tmp_path)
    state = StateStore(tmp_path / "state" / "state.json")
    pr_state = PRState(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha_seen="abc123",
    )
    state.set(pr_state)

    with (
        patch("zajecdaemon.worker.ensure_controller_clone", new_callable=AsyncMock),
        patch(
            "zajecdaemon.worker.fetch_pr_ref",
            new_callable=AsyncMock,
            side_effect=RuntimeError("fetch failed"),
        ),
    ):
        task = _make_task()
        await process_task(task, config, state)

    updated = state.get("owner/repo", 42)
    assert updated is not None
    assert updated.last_run_status == "failed"
    assert updated.head_sha_processed == ""


@pytest.mark.asyncio
async def test_process_task_no_existing_state(tmp_path):
    config = _make_config(tmp_path)
    state = StateStore(tmp_path / "state" / "state.json")

    with (
        patch("zajecdaemon.worker.ensure_controller_clone", new_callable=AsyncMock),
        patch("zajecdaemon.worker.fetch_pr_ref", new_callable=AsyncMock),
        patch(
            "zajecdaemon.worker.worktree_path",
            return_value=Path("/nonexistent"),
        ),
        patch(
            "zajecdaemon.worker.ensure_worktree",
            new_callable=AsyncMock,
            return_value=Path("/tmp/wt"),
        ),
    ):
        task = _make_task()
        await process_task(task, config, state)

    assert state.get("owner/repo", 42) is None
