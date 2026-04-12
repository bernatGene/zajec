from collections.abc import Callable, Coroutine
from datetime import datetime, timezone
import logging

from zajecdaemon.config import DEFAULTS
from zajecdaemon.github_cli import (
    fetch_comments,
    fetch_pr_commits,
    fetch_pr_meta,
    list_open_prs,
)
from zajecdaemon.models import PRState, Task
from zajecdaemon.queueing import QueueManager
from zajecdaemon.state import StateStore

logger = logging.getLogger(__name__)


def _latest_zajec_comment_id(comments: list[dict]) -> int:
    prefix = DEFAULTS["comment_trigger_prefix"]
    best = 0
    for c in comments:
        body = c.get("body", "")
        if body.strip().startswith(prefix):
            cid = c.get("id", 0)
            if cid > best:
                best = cid
    return best


def _is_merge_commit(commit: dict) -> bool:
    parents = commit.get("parents", [])
    return len(parents) > 1


def _latest_non_merge_sha(commits: list[dict]) -> str | None:
    for commit in reversed(commits):
        if not _is_merge_commit(commit):
            return commit.get("sha", "")
    return None


PollCallback = Callable[[Task], Coroutine[None, None, None]]


class Poller:
    def __init__(self, state_store: StateStore, queue: QueueManager) -> None:
        self._state = state_store
        self._queue = queue

    async def poll_repo(
        self,
        repo: str,
        enqueue: PollCallback,
    ) -> None:
        logger.info("Polling repo %s", repo)
        try:
            open_prs = await list_open_prs(repo)
        except Exception:
            logger.exception("Failed to list open PRs for %s", repo)
            return

        open_numbers = {pr["number"] for pr in open_prs}

        for state_entry in self._state.all_for_repo(repo):
            if state_entry.pr_number not in open_numbers:
                if state_entry.is_open:
                    logger.info("PR %s#%d closed", repo, state_entry.pr_number)
                    state_entry.is_open = False
                continue

        for pr in open_prs:
            pr_number = pr["number"]
            try:
                await self._inspect_pr(repo, pr_number, enqueue)
            except Exception:
                logger.exception("Failed to inspect PR %s#%d", repo, pr_number)

        self._state.save()

    async def _inspect_pr(
        self,
        repo: str,
        pr_number: int,
        enqueue: PollCallback,
    ) -> None:
        existing = self._state.get(repo, pr_number)
        meta = await fetch_pr_meta(repo, pr_number)
        head_sha = meta.get("headRefOid", "")
        pr_url = meta.get("url", "")

        if existing is None:
            state = PRState(
                repo=repo,
                pr_number=pr_number,
                pr_url=pr_url,
                head_sha_seen=head_sha,
            )
            self._state.set(state)
            logger.info("New PR %s#%d detected", repo, pr_number)
            await self._maybe_enqueue(repo, pr_number, pr_url, head_sha, None, enqueue)
            return

        state = existing
        state.is_open = True
        state.pr_url = pr_url

        comments = await fetch_comments(repo, pr_number)
        new_comment_id = _latest_zajec_comment_id(comments)
        if new_comment_id > state.last_zajec_comment_id_seen:
            state.last_zajec_comment_id_seen = new_comment_id
            logger.info("New #zajec comment on %s#%d", repo, pr_number)
            await self._maybe_enqueue(
                repo, pr_number, pr_url, head_sha, new_comment_id, enqueue
            )

        if head_sha != state.head_sha_seen:
            commits = await fetch_pr_commits(repo, pr_number)
            state.head_sha_seen = head_sha

            latest_is_merge = commits and _is_merge_commit(commits[-1])
            if latest_is_merge:
                logger.debug("Merge commit on %s#%d, skipping", repo, pr_number)
            else:
                logger.info("New commit on %s#%d", repo, pr_number)
                await self._maybe_enqueue(
                    repo, pr_number, pr_url, head_sha, None, enqueue
                )

    async def _maybe_enqueue(
        self,
        repo: str,
        pr_number: int,
        pr_url: str,
        head_sha: str,
        trigger_comment_id: int | None,
        enqueue: PollCallback,
    ) -> None:
        if not self._queue.should_enqueue(repo, pr_number):
            return
        task = Task(
            repo=repo,
            pr_number=pr_number,
            pr_url=pr_url,
            head_sha=head_sha,
            trigger_comment_id=trigger_comment_id,
            enqueued_at=datetime.now(timezone.utc),
        )
        await enqueue(task)
