import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _repo_slug(repo: str) -> str:
    return repo.replace("/", "__")


def _repo_dir(base_dir: Path, repo: str) -> Path:
    return base_dir / "repos" / _repo_slug(repo)


def _controller_path(base_dir: Path, repo: str) -> Path:
    return _repo_dir(base_dir, repo) / "controller"


def _worktree_path(base_dir: Path, repo: str, pr_number: int) -> Path:
    return _repo_dir(base_dir, repo) / "worktrees" / str(pr_number)


async def _run_git(*args: str, cwd: Path | None = None) -> str:
    cmd = ["git"] + list(args)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode().strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {err}")
    return stdout.decode().strip()


async def _run_git_in_controller(base_dir: Path, repo: str, *args: str) -> str:
    return await _run_git(*args, cwd=_controller_path(base_dir, repo))


async def ensure_controller_clone(base_dir: Path, repo: str) -> Path:
    controller = _controller_path(base_dir, repo)
    if controller.exists():
        logger.info("Fetching updates for %s controller clone", repo)
        await _run_git("fetch", "--all", cwd=controller)
    else:
        logger.info("Cloning %s into controller", repo)
        controller.parent.mkdir(parents=True, exist_ok=True)
        clone_url = f"https://github.com/{repo}.git"
        await _run_git("clone", clone_url, str(controller))
    return controller


async def fetch_pr_ref(base_dir: Path, repo: str, pr_number: int) -> None:
    logger.info("Fetching PR %d ref for %s", pr_number, repo)
    await _run_git_in_controller(
        base_dir, repo, "fetch", "origin", f"pull/{pr_number}/head:pr/{pr_number}"
    )


def worktree_path(base_dir: Path, repo: str, pr_number: int) -> Path:
    return _worktree_path(base_dir, repo, pr_number)


async def ensure_worktree(base_dir: Path, repo: str, pr_number: int) -> Path:
    worktree = _worktree_path(base_dir, repo, pr_number)
    branch = f"pr/{pr_number}"
    if worktree.exists():
        logger.info("Resetting worktree for %s#%d", repo, pr_number)
        await _run_git("fetch", "origin", f"pull/{pr_number}/head", cwd=worktree)
        await _run_git("reset", "--hard", "FETCH_HEAD", cwd=worktree)
        await _run_git("clean", "-fdx", cwd=worktree)
    else:
        logger.info("Creating worktree for %s#%d", repo, pr_number)
        worktree.parent.mkdir(parents=True, exist_ok=True)
        controller = _controller_path(base_dir, repo)
        await _run_git("worktree", "add", str(worktree), branch, cwd=controller)
    return worktree


async def cleanup_worktree(base_dir: Path, repo: str, pr_number: int) -> None:
    worktree = _worktree_path(base_dir, repo, pr_number)
    branch = f"pr/{pr_number}"
    controller = _controller_path(base_dir, repo)
    if worktree.exists():
        logger.info("Removing worktree for %s#%d", repo, pr_number)
        await _run_git("worktree", "remove", "--force", str(worktree), cwd=controller)
    await _run_git("branch", "-D", branch, cwd=controller)
