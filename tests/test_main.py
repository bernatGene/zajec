import json
from shutil import which
from unittest.mock import patch

import pytest

from zajecdaemon.main import Daemon


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

        with patch("zajecdaemon.main.which", side_effect=which):
            daemon = Daemon(config_file)
            daemon._validate_startup()

        assert base.is_dir()
