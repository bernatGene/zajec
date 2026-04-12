import json
from pathlib import Path
import tempfile

from zajecdaemon.models import PRState


class StateStore:
    def __init__(self, path: Path):
        self._path = path
        self._states: dict[str, PRState] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            self._states = {}
            return
        data = json.loads(self._path.read_text())
        self._states = {k: PRState(**v) for k, v in data.items()}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.model_dump(mode="json") for k, v in self._states.items()}
        fd, tmp_path = tempfile.mkstemp(dir=str(self._path.parent))
        try:
            with open(fd, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        Path(tmp_path).rename(self._path)

    def get(self, repo: str, pr_number: int) -> PRState | None:
        return self._states.get(f"{repo}#{pr_number}")

    def set(self, state: PRState) -> None:
        self._states[state.key] = state

    def remove(self, repo: str, pr_number: int) -> None:
        self._states.pop(f"{repo}#{pr_number}", None)

    def all_open(self, repo: str) -> list[PRState]:
        return [s for s in self._states.values() if s.repo == repo and s.is_open]

    def all_for_repo(self, repo: str) -> list[PRState]:
        return [s for s in self._states.values() if s.repo == repo]
