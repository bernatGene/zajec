# AGENTS.md - zajec Development Guidelines

Local CLI tool that interfaces a code review agent with GitHub.

## Technology Stack

- Python >= 3.12
- Standard library only (`argparse`, `subprocess`)
- GitHub CLI (`gh`) for authentication and API

> [!IMPORTANT] Use `uv` to run Python commands. Never `pip install`.

## Skills

> [!IMPORTANT]
> You have skills available. Use them. List them at the beginning of the session and
> remember to activate one if you think it applies.

## Code Style

**General**
- Keep it simple
- Very minimal comments, in general NONE unless it's something that needs an "why?"
explanation
- Always prefer short-circuit logic over nested ifs

**Python**
- Line length 88, 4 spaces, double quotes
- snake_case (functions/vars), PascalCase (classes)
- Strict type hints, never `from __future__ import typing`
- Python >= 3.12: use `list`, `dict` not `typing.List`
- Top-level imports only. Function-local imports are forbidden unless optional
dependency, circular import workaround, or measured startup issue. Add a one-line
comment when making an exception.

## CLI Surface

The tool exposes exactly two commands:

- `zajec get-context --repo owner/repo --pr <n>` - outputs normalized JSON to stdout
- `zajec publish-comment --repo owner/repo --pr <n> --body-file <path>` - outputs compact JSON to stdout

Error messages go to stderr with non-zero exit code.

## Git Workflow

- Always work on the current branch
- Never switch branches unless explicitly requested
- Commit and push to the current branch; do not create or switch to other branches

## Conversation and Writing Style

Address me as if we were coworkers trying to solve a problem via slack, professional
attitude. Don't glaze me with undue praise that would be weird and condescending in a
normal conversation between coworkers. In general, assume a solid level of understanding
of software engineering. Keep answers and explanations concise and to the minimum. Avoid
introductory sentences like the typical at the beginning of each message, or trailing
suggestions and tangents to the current conversation; i.e. focus on the current topic
and be brief unless told otherwise. If lacking context or additional explanations, ask
before answering fully, if unsure (for example exact API of a library), say so.

NEVER use emojis, not in the conversation, not in the plan writing.
