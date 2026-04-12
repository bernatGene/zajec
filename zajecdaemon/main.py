import asyncio
import logging
from pathlib import Path
from shutil import which
import signal
import sys

from zajecdaemon.config import load_config
from zajecdaemon.models import Task
from zajecdaemon.poller import Poller
from zajecdaemon.queueing import QueueManager
from zajecdaemon.state import StateStore

logger = logging.getLogger(__name__)


class Daemon:
    def __init__(self, config_path: Path) -> None:
        self._config = load_config(config_path)
        state_path = self._config.base_dir / "state" / "state.json"
        self._state = StateStore(state_path)
        self._queue_mgr = QueueManager()
        self._poller = Poller(self._state, self._queue_mgr)
        self._task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self._running = True

    async def run(self) -> None:
        self._validate_startup()
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

        try:
            await asyncio.gather(poller_task, *workers)
        except asyncio.CancelledError:
            pass

    def _validate_startup(self) -> None:
        for name in ("gh", "git", "opencode"):
            if which(name) is None:
                raise RuntimeError(f"Required command not found: {name}")

        self._config.base_dir.mkdir(parents=True, exist_ok=True)

    def _handle_signal(self, sig: signal.Signals) -> None:
        logger.info("Received signal %s, shutting down", sig.name)
        self._running = False

    async def _poll_loop(self) -> None:
        while self._running:
            for repo in self._config.repos:
                try:
                    await self._poller.poll_repo(repo, self._enqueue_task)
                except Exception:
                    logger.exception("Error polling repo %s", repo)
            await asyncio.sleep(self._config.poll_interval_seconds)

    async def _enqueue_task(self, task: Task) -> None:
        self._queue_mgr.should_enqueue(task.repo, task.pr_number)
        await self._task_queue.put(task)
        self._queue_mgr.set_running(task.repo, task.pr_number)
        logger.info("Enqueued task for %s#%d", task.repo, task.pr_number)

    async def _worker(self, name: str) -> None:
        logger.info("Worker %s started", name)
        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            logger.info("Worker %s processing %s#%d", name, task.repo, task.pr_number)
            try:
                await self._process_task(task)
            except Exception:
                logger.exception(
                    "Worker %s failed processing %s#%d", name, task.repo, task.pr_number
                )
            finally:
                rerun = self._queue_mgr.check_rerun(task.repo, task.pr_number)
                self._queue_mgr.set_idle(task.repo, task.pr_number)
                if rerun:
                    await self._enqueue_task(task)

    async def _process_task(self, task: Task) -> None:
        # Phase 2 will implement worktree prep and opencode runner
        state = self._state.get(task.repo, task.pr_number)
        if state:
            state.last_run_at = task.enqueued_at
            state.last_run_status = "pending"
            state.last_session_id = ""
            self._state.set(state)
            self._state.save()


def main() -> None:
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config.json")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    daemon = Daemon(config_path)
    asyncio.run(daemon.run())
