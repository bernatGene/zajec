import json
from pathlib import Path

from pydantic import BaseModel


class Config(BaseModel):
    poll_interval_seconds: int = 60
    worker_concurrency: int = 1
    base_dir: Path
    repos: list[str]
    opencode_command: str = "opencode"
    opencode_agent: str = "codereview"
    opencode_timeout_seconds: int = 600
    max_forbidden_retries: int = 5


DEFAULTS = {
    "gh_command": "gh",
    "git_command": "git",
    "opencode_command": "opencode",
    "opencode_agent": "codereview",
    "max_forbidden_retries": 5,
    "comment_trigger_prefix": "#zajec",
}


def load_config(path: Path) -> Config:
    data = json.loads(path.read_text())
    data["base_dir"] = Path(data["base_dir"]).expanduser().resolve()
    return Config(**data)
