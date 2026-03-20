# zajec

CLI tool that acts as a narrow interface between a local code review agent and GitHub. It fetches PR context (metadata, comments, reviews) as normalized JSON and can publish one summary comment to a PR. GitHub authentication is delegated to `gh`.

## Installation

Add as a dev dependency via uv:

```bash
uv add --group dev git+https://github.com/bernatGene/zajec.git
```

Or install editable:

```bash
uv pip install -e .
```

## Commands

- `zajec get-context --repo owner/repo --pr 123` - fetch and print PR context as JSON
- `zajec publish-comment --repo owner/repo --pr 123 --body-file review.md` - publish a comment

Intended for use by local AI coding agents (e.g., opencode) that need to read PR discussions and post review summaries without direct GitHub API access.
