import asyncio
import logging
from pathlib import Path
import shlex
from shutil import which
import signal
import sys

from zajecdaemon.config import load_config
from zajecdaemon.git_worktree import ensure_controller_clone
from zajecdaemon.github_cli import delete_comment, post_comment, update_comment
from zajecdaemon.models import Task
from zajecdaemon.poller import Poller
from zajecdaemon.queueing import QueueManager
from zajecdaemon.state import StateStore
from zajecdaemon.worker import process_task

logger = logging.getLogger(__name__)


class Daemon:
    def __init__(self, config_path: Path) -> None:
        self._config = load_config(config_path)
        state_path = self._config.base_dir / "state" / "state.json"
        self._state = StateStore(state_path)
        self._queue_mgr = QueueManager()
        self._poller = Poller(self._state, self._queue_mgr, self._config)
        self._task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self._running = True
        self._tasks: list[asyncio.Task] = []

    async def run(self) -> None:
        self._validate_startup()
        await self._bootstrap_repos()
        logger.info(
            "Daemon started, polling every %ds", self._config.poll_interval_seconds
        )

        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_signal, sig)

        workers = [
            asyncio.create_task(self._worker(f"worker-{i}"))
            for i in range(self._config.worker_concurrency)
        ]
        poller_task = asyncio.create_task(self._poll_loop())
        self._tasks = [poller_task, *workers]

        try:
            await asyncio.gather(poller_task, *workers)
        except asyncio.CancelledError:
            pass

    def _validate_startup(self) -> None:
        for name in ("gh", "git"):
            if which(name) is None:
                raise RuntimeError(f"Required command not found: {name}")
        try:
            cmd = shlex.split(self._config.opencode_command)[0]
        except ValueError as e:
            raise RuntimeError(f"Invalid opencode_command: {e}") from e
        if which(cmd) is None and not Path(cmd).is_file():
            raise RuntimeError(f"Required command not found: {cmd}")

        self._config.base_dir.mkdir(parents=True, exist_ok=True)

    async def _bootstrap_repos(self) -> None:
        for repo in self._config.repos:
            logger.info("Bootstrapping controller clone for %s", repo)
            await ensure_controller_clone(self._config.base_dir, repo)

    def _handle_signal(self, sig: signal.Signals) -> None:
        logger.info("Received signal %s, shutting down", sig.name)
        self._running = False
        for task in self._tasks:
            task.cancel()

    async def _poll_loop(self) -> None:
        while self._running:
            for repo in self._config.repos:
                try:
                    await self._poller.poll_repo(repo, self._enqueue_task)
                except Exception:
                    logger.exception("Error polling repo %s", repo)
            await asyncio.sleep(self._config.poll_interval_seconds)

    async def _enqueue_task(self, task: Task) -> None:
        if not self._queue_mgr.should_enqueue(task.repo, task.pr_number):
            return
        progress_comment_id: int | None = None
        try:
            progress_comment_id = await post_comment(
                task.repo, task.pr_number, "review in progress"
            )
        except Exception:
            logger.exception(
                "Failed to post comment on %s#%d", task.repo, task.pr_number
            )
        queued_task = task.model_copy(
            update={"progress_comment_id": progress_comment_id}
        )
        await self._task_queue.put(queued_task)
        self._queue_mgr.set_running(task.repo, task.pr_number)
        logger.info("Enqueued task for %s#%d", task.repo, task.pr_number)

    async def _finalize_progress_comment(self, task: Task, status: str) -> None:
        if task.progress_comment_id is None:
            return
        try:
            if status == "success":
                await delete_comment(task.repo, task.progress_comment_id)
            else:
                await update_comment(
                    task.repo,
                    task.progress_comment_id,
                    "review failed",
                )
        except Exception:
            logger.exception(
                "Failed to finalize progress comment on %s#%d",
                task.repo,
                task.pr_number,
            )

    async def _worker(self, name: str) -> None:
        logger.info("Worker %s started", name)
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            logger.info("Worker %s processing %s#%d", name, task.repo, task.pr_number)
            status = "failed"
            try:
                status = await process_task(task, self._config, self._state)
            except Exception:
                logger.exception(
                    "Worker %s failed processing %s#%d", name, task.repo, task.pr_number
                )
            finally:
                await self._finalize_progress_comment(task, status)
                rerun = self._queue_mgr.check_rerun(task.repo, task.pr_number)
                self._queue_mgr.set_idle(task.repo, task.pr_number)
                if rerun:
                    await self._enqueue_task(task)


def main() -> None:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.json")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    daemon = Daemon(config_path)
    asyncio.run(daemon.run())
