# zajec

CLI tool and daemon for orchestrating automated code reviews on GitHub PRs. GitHub authentication is delegated to `gh`.

## Components

### 1. CLI Tool (`zajec`)

A narrow interface between a local code review agent and GitHub. Fetches PR context, publishes summary comments, and updates PR titles.

**Commands:**

- `zajec get-context --repo owner/repo --pr 123` - fetch PR metadata, comments, and reviews as JSON
- `zajec publish-comment --repo owner/repo --pr 123 --body-file review.md` - publish a review comment
- `zajec update-title --repo owner/repo --pr 123 --title "[MOT-323] Improve retry handling"` - update the PR title

### 2. Daemon (`zajecdaemon`)

A persistent asyncio process that automatically polls configured repositories, detects PRs needing review, and runs a code review agent.

**Triggers:**

- New open PR
- New comment starting with `@zajec`
- New non-merge commit on PR branch

**Features:**

- Polls every 60 seconds (configurable)
- Manages git worktrees per PR
- Waits for CI completion before reviewing
- Retries on forbidden command rejections
- Persists state to resume after restart

## Installation

Add as a dev dependency via uv:

```bash
uv add --group dev git+https://github.com/bernatGene/zajec.git
```

Or install editable:

```bash
uv pip install -e .
```

## CLI Usage

Fetch PR context for local analysis:

```bash
zajec get-context --repo owner/repo --pr 123
```

Publish a review comment:

```bash
zajec publish-comment --repo owner/repo --pr 123 --body-file review.md
```

Update a PR title:

```bash
zajec update-title --repo owner/repo --pr 123 --title "[MOT-323] Improve retry handling"
```

## Daemon Usage

Create a config file (e.g., `zajec.json`):

```json
{
  "poll_interval_seconds": 60,
  "worker_concurrency": 1,
  "base_dir": "/path/to/data",
  "repos": ["owner/repo1", "owner/repo2"]
}
```

Run the daemon:

```bash
zajecdaemon --config zajec.json
```

The daemon will:

1. Clone controller repos to `base_dir/repos/<owner__repo>/controller`
2. Create worktrees at `base_dir/repos/<owner__repo>/worktrees/<pr_number>`
3. Write logs to `base_dir/logs/<owner__repo>/<pr_number>/<timestamp>.log`
4. Persist state to `base_dir/state/state.json`

To trigger a review manually, comment `@zajec` on any PR in a configured repository.

## Requirements

- Python >= 3.12
- `gh` CLI installed and authenticated
- `git`
- `opencode` (for daemon mode)

## Project Structure

```
zajec/
  __init__.py
  __main__.py
  cli.py          # CLI entry points
  github_cli.py   # gh CLI wrappers

zajecdaemon/
  __init__.py
  __main__.py
  main.py         # Daemon event loop
  config.py       # Configuration models
  models.py       # State and task models
  state.py        # JSON state persistence
  poller.py       # GitHub polling logic
  queueing.py     # Task queue management
  git_worktree.py # Git worktree operations
  opencode_runner.py  # Agent execution
  worker.py       # Task processing
```

## Development

Run tests:

```bash
uv run pytest
```

Lint:

```bash
uv run ruff check
```
