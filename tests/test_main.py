from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, patch

import pytest

from zajecdaemon.main import STATUS_FAILED, Daemon
from zajecdaemon.models import Task


class TestValidateStartup:
    def test_missing_command_raises(self, tmp_path):
        config = {
            "poll_interval_seconds": 60,
            "worker_concurrency": 1,
            "base_dir": str(tmp_path / "data"),
            "repos": ["owner/repo"],
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        with patch(
            "zajecdaemon.main.which",
            side_effect=lambda name: None if name == "opencode" else name,
        ):
            daemon = Daemon(config_file)
            with pytest.raises(
                RuntimeError, match="Required command not found: opencode"
            ):
                daemon._validate_startup()

    def test_creates_base_dir(self, tmp_path):
        base = tmp_path / "data"
        config = {
            "poll_interval_seconds": 60,
            "worker_concurrency": 1,
            "base_dir": str(base),
            "repos": ["owner/repo"],
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config))

        with patch("zajecdaemon.main.which", return_value="/usr/bin/cmd"):
            daemon = Daemon(config_file)
            daemon._validate_startup()

        assert base.is_dir()


@pytest.mark.asyncio
async def test_enqueue_task_posts_comment(tmp_path):
    config = {
        "poll_interval_seconds": 60,
        "worker_concurrency": 1,
        "base_dir": str(tmp_path / "data"),
        "repos": ["owner/repo"],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    with patch("zajecdaemon.main.which", return_value="/usr/bin/cmd"):
        daemon = Daemon(config_file)

    task = Task(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha="abc",
        enqueued_at=datetime.now(timezone.utc),
    )

    with patch("zajecdaemon.main.post_comment", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = 123
        await daemon._enqueue_task(task)

    mock_post.assert_awaited_once_with("owner/repo", 42, "review in progress")
    queued = await daemon._task_queue.get()
    assert queued.progress_comment_id == 123


@pytest.mark.asyncio
async def test_finalize_progress_comment_deletes_on_success(tmp_path):
    config = {
        "poll_interval_seconds": 60,
        "worker_concurrency": 1,
        "base_dir": str(tmp_path / "data"),
        "repos": ["owner/repo"],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    with patch("zajecdaemon.main.which", return_value="/usr/bin/cmd"):
        daemon = Daemon(config_file)

    task = Task(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha="abc",
        progress_comment_id=123,
        enqueued_at=datetime.now(timezone.utc),
    )

    with (
        patch("zajecdaemon.main.delete_comment", new_callable=AsyncMock) as mock_delete,
        patch("zajecdaemon.main.update_comment", new_callable=AsyncMock) as mock_update,
    ):
        await daemon._finalize_progress_comment(task, "success")

    mock_delete.assert_awaited_once_with("owner/repo", 123)
    mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_finalize_progress_comment_updates_on_failure(tmp_path):
    config = {
        "poll_interval_seconds": 60,
        "worker_concurrency": 1,
        "base_dir": str(tmp_path / "data"),
        "repos": ["owner/repo"],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    with patch("zajecdaemon.main.which", return_value="/usr/bin/cmd"):
        daemon = Daemon(config_file)

    task = Task(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha="abc",
        progress_comment_id=123,
        enqueued_at=datetime.now(timezone.utc),
    )

    with (
        patch("zajecdaemon.main.delete_comment", new_callable=AsyncMock) as mock_delete,
        patch("zajecdaemon.main.update_comment", new_callable=AsyncMock) as mock_update,
    ):
        await daemon._finalize_progress_comment(task, "failed")

    mock_delete.assert_not_called()
    mock_update.assert_awaited_once_with("owner/repo", 123, "review failed")


@pytest.mark.asyncio
async def test_worker_finalizes_comment_when_process_task_raises(tmp_path):
    config = {
        "poll_interval_seconds": 60,
        "worker_concurrency": 1,
        "base_dir": str(tmp_path / "data"),
        "repos": ["owner/repo"],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    with patch("zajecdaemon.main.which", return_value="/usr/bin/cmd"):
        daemon = Daemon(config_file)

    task = Task(
        repo="owner/repo",
        pr_number=42,
        pr_url="https://github.com/owner/repo/pull/42",
        head_sha="abc",
        progress_comment_id=123,
        enqueued_at=datetime.now(timezone.utc),
    )
    await daemon._task_queue.put(task)

    async def finalize_side_effect(*_args, **_kwargs):
        daemon._running = False

    with (
        patch(
            "zajecdaemon.main.process_task",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ),
        patch(
            "zajecdaemon.main.Daemon._finalize_progress_comment",
            new_callable=AsyncMock,
        ) as mock_finalize,
        patch(
            "zajecdaemon.main.QueueManager.check_rerun",
            return_value=False,
        ),
    ):
        mock_finalize.side_effect = finalize_side_effect
        await daemon._worker("worker-0")

    mock_finalize.assert_awaited_once_with(task, STATUS_FAILED)
