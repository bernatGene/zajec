from pathlib import Path

from zajecdaemon.git_worktree import (
    _controller_path,
    _repo_dir,
    _repo_slug,
    _worktree_path,
)


def test_repo_slug():
    assert _repo_slug("owner/repo") == "owner__repo"


def test_repo_dir():
    assert _repo_dir(Path("/data"), "owner/repo") == Path("/data/repos/owner__repo")


def test_controller_path():
    assert _controller_path(Path("/data"), "owner/repo") == Path(
        "/data/repos/owner__repo/controller"
    )


def test_worktree_path():
    assert _worktree_path(Path("/data"), "owner/repo", 42) == Path(
        "/data/repos/owner__repo/worktrees/42"
    )
