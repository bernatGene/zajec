import logging

from zajecdaemon.config import Config
from zajecdaemon.git_worktree import (
    ensure_controller_clone,
    ensure_worktree,
    fetch_pr_ref,
    worktree_path,
)
from zajecdaemon.models import Task
from zajecdaemon.opencode_runner import run_opencode
from zajecdaemon.state import StateStore

logger = logging.getLogger(__name__)


async def process_task(task: Task, config: Config, state_store: StateStore) -> None:
    try:
        await ensure_controller_clone(config.base_dir, task.repo)
        wt_exists = worktree_path(config.base_dir, task.repo, task.pr_number).exists()
        if not wt_exists:
            await fetch_pr_ref(config.base_dir, task.repo, task.pr_number)
        wt = await ensure_worktree(config.base_dir, task.repo, task.pr_number)
    except Exception:
        logger.exception(
            "Worktree preparation failed for %s#%d", task.repo, task.pr_number
        )
        state = state_store.get(task.repo, task.pr_number)
        if state:
            state.last_run_status = "failed"
            state.last_run_at = task.enqueued_at
            state_store.set(state)
            state_store.save()
        return

    result = await run_opencode(wt, task.pr_url, task.repo, task.pr_number, config)

    state = state_store.get(task.repo, task.pr_number)
    if state is None:
        logger.warning(
            "State not found for %s#%d after run, result discarded",
            task.repo,
            task.pr_number,
        )
        return

    if result.status == "success":
        state.head_sha_processed = state.head_sha_seen
        state.last_zajec_comment_id_processed = state.last_zajec_comment_id_seen
        state.last_session_id = result.session_id
    state.last_run_status = result.status
    state.last_run_at = task.enqueued_at
    state_store.set(state)
    state_store.save()

    logger.info(
        "opencode finished for %s#%d: status=%s session=%s retries=%d",
        task.repo,
        task.pr_number,
        result.status,
        result.session_id,
        result.forbidden_retries,
    )
