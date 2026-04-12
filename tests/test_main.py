from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, patch

import pytest

from zajecdaemon.main import Daemon
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
        await daemon._enqueue_task(task)

    mock_post.assert_awaited_once_with("owner/repo", 42, "review in progress")
