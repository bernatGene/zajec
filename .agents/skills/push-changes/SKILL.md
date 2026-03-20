---
name: push-changes
description: Add, commit, and push repository changes with concise commit messages
---

# Push Changes Skill

## Purpose

Add, commit, and push changes to the repository following the team's workflow conventions.

## Workflow

### 1. Check Status

Always start by checking what has changed:

```bash
git status
```

### 2. Stage Modified Files

Add **only modified files** (already tracked by git):

```bash
git add -u
```

Or add specific files:

```bash
git add path/to/file.md
```

**Do NOT add untracked files** unless the user explicitly asks you to.

### 3. Commit

Write concise, descriptive commit messages. Usually one line:

```bash
git commit -m "Brief description of what changed"
```

Good examples:
- "Add limen360 project timeline and requirements"
- "Update README with Obsidian linking conventions"
- "Fix typo in contributing guidelines"

Bad examples:
- "Update file" (too vague)
- "Made some changes" (no information)
- Multi-paragraph essays (too noisy)

### 4. Push

Push directly to main:

```bash
git push
```

**Do NOT pull before pushing** as a routine step.

If the push fails due to conflicts:
1. Pull the latest changes: `git pull`
2. **STOP and discuss with the user** how to resolve the conflicts
3. Do not auto-resolve or force push without user input

## Important Notes

- All work goes to `main` branch (no feature branches)
- Untracked files should only be added when explicitly requested
- Keep commit messages factual and minimal
- Conflicts require user consultation

