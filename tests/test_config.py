import json
from pathlib import Path

import pydantic
import pytest

from zajecdaemon.config import Config, load_config


def test_config_defaults():
    cfg = Config(base_dir=Path("/tmp/zajec"), repos=["owner/repo"])
    assert cfg.poll_interval_seconds == 60
    assert cfg.worker_concurrency == 1


def test_load_config(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "poll_interval_seconds": 30,
                "worker_concurrency": 2,
                "base_dir": str(tmp_path / "data"),
                "repos": ["foo/bar", "baz/qux"],
            }
        )
    )
    cfg = load_config(config_file)
    assert cfg.poll_interval_seconds == 30
    assert cfg.worker_concurrency == 2
    assert len(cfg.repos) == 2
    assert cfg.base_dir.is_absolute()


def test_load_config_missing_field(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"base_dir": "/tmp/zajec"}))
    with pytest.raises(pydantic.ValidationError):
        load_config(config_file)
