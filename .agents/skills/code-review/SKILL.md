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

## Workflow

### 1. Get PR Context

```bash
zajec get-context --repo owner/repo --pr 123
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
# Zajec Review (confidence: 4/5)

| Severity | File | Line | Finding | Status |
|---|---|---:|---|---|
| Medium | `src/foo.ts` | 42 | Possible null access when `bar` is undefined | New |
| Low | `api/items.py` | 118 | Response shape may differ from existing endpoint contract | Possibly already discussed |

Notes:
- Existing PR comments were considered while preparing this summary.
- This is a general summary comment, not inline review feedback.
```

If no issues found:
```md
# Zajec Review (confidence: 5/5)

No additional issues identified based on the current diff and existing PR discussion.
```

### 4. Publish Comment

```bash
zajec publish-comment --repo owner/repo --pr 123 --body-file review.md
```

## Constraints

The agent reviewing code should:
- report findings without attempting to fix them
- avoid making changes to the codebase
- publish only one summary comment per review session

## Constraints

The agent should not:
- call `gh` directly for extra GitHub operations
- browse PRs or search unrelated issues/comments
- post multiple comments unless explicitly asked
