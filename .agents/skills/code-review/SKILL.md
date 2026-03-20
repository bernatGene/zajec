---
name: code-review
description: Review PR changes using local diff and zajec tool
---

# Code Review Skill

For Python projects, also follow the [python-dev](../python-dev/SKILL.md) skill.

## Purpose

Review a PR by:
1. fetching PR discussion context with `zajec`
2. inspecting the local diff and code using own repo access
3. avoiding repeating issues already raised in the PR discussion
4. writing one summary markdown comment
5. publishing it with `zajec`

## Invocation

All `zajec` commands run via `uv`:

```bash
uv run zajec <command>
```

Examples:
```bash
uv run zajec get-context --repo owner/repo --pr 123
uv run zajec publish-comment --repo owner/repo --pr 123 --body-file review.md
```

## Workflow

### 1. Get PR Context

```bash
uv run zajec get-context --repo owner/repo --pr 123
```

This returns normalized JSON with PR metadata and all comments.

### 2. Review Local Changes

Use git to inspect the diff:
```bash
git diff [base]...[head]
git diff --name-only [base]...[head]
```

Review for:
- Logic correctness and edge cases
- Error handling completeness
- Type safety (strict hints, no `Any`)
- No hardcoded values where they should be configurable
- No commented-out code left behind
- No unnecessary complexity
- Security: no secrets, input validation, auth/authz checks

### 3. Write Summary Comment

Write a short, actionable summary. Avoid repeating existing PR comments.

Format:
```md
**Zajec Review** (confidence: 4/5)

| Severity | File | Line | Finding | Status |
|---|---|---:|---|---|
| Medium | `src/foo.ts` | 42 | Possible null access when `bar` is undefined | New |
| Low | `api/items.py` | 118 | Response shape may differ from existing endpoint contract | Possibly already discussed |
```

If no issues found:
```md
**Zajec Review** (confidence: 5/5)

No additional issues identified based on the current diff and existing PR discussion.
```

### 4. Publish Comment

```bash
uv run zajec publish-comment --repo owner/repo --pr 123 --body-file review.md
```

## Constraints

The agent should not:
- call `gh` directly for extra GitHub operations
- browse PRs or search unrelated issues/comments
- post multiple comments unless explicitly asked
- make changes to the codebase or attempt to fix findings
