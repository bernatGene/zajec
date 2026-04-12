from enum import Enum


class PRStatus(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"


class QueueManager:
    def __init__(self) -> None:
        self._status: dict[str, PRStatus] = {}
        self._needs_rerun: set[str] = set()

    def _key(self, repo: str, pr_number: int) -> str:
        return f"{repo}#{pr_number}"

    def get_status(self, repo: str, pr_number: int) -> PRStatus:
        return self._status.get(self._key(repo, pr_number), PRStatus.IDLE)

    def set_running(self, repo: str, pr_number: int) -> None:
        self._status[self._key(repo, pr_number)] = PRStatus.RUNNING

    def set_idle(self, repo: str, pr_number: int) -> None:
        self._status[self._key(repo, pr_number)] = PRStatus.IDLE
        self._needs_rerun.discard(self._key(repo, pr_number))

    def should_enqueue(self, repo: str, pr_number: int) -> bool:
        key = self._key(repo, pr_number)
        status = self._status.get(key, PRStatus.IDLE)
        if status == PRStatus.IDLE:
            return True
        if status == PRStatus.RUNNING:
            self._needs_rerun.add(key)
        return False

    def check_rerun(self, repo: str, pr_number: int) -> bool:
        key = self._key(repo, pr_number)
        if key in self._needs_rerun:
            self._needs_rerun.discard(key)
            return True
        return False
