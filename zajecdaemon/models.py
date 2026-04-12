from datetime import datetime

from pydantic import BaseModel


class PRState(BaseModel):
    repo: str
    pr_number: int
    pr_url: str
    is_open: bool = True
    head_sha_seen: str = ""
    head_sha_processed: str = ""
    last_zajec_comment_id_seen: int = 0
    last_zajec_comment_id_processed: int = 0
    last_session_id: str = ""
    last_run_at: datetime | None = None
    last_run_status: str = ""

    @property
    def key(self) -> str:
        return f"{self.repo}#{self.pr_number}"


class Task(BaseModel):
    repo: str
    pr_number: int
    pr_url: str
    head_sha: str
    trigger_comment_id: int | None = None
    enqueued_at: datetime
