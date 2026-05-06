# Code Review Task Template

## Purpose

Code review tasks inspect existing code changes and produce a review verdict without modifying the codebase.

## Task type

Code review.

## Key characteristics

- **Inspect diff/status/tests** — review the full changeset carefully
- **Produce review verdict** — note any blocking issues, suggestions, or approval
- **No source changes unless explicitly requested** — review only; implement separately if needed

## Sections

```markdown
## Goal

<What needs to be reviewed.>

## Background

<Context — what PR, commit, or code change is being reviewed?>

## Review scope

<What should the reviewer inspect? Diff, tests, specific files?>

## Allowed changes

This is a review task. Source code changes are NOT allowed unless explicitly listed here:
- <list any allowed file changes, or "none">
```

## Governance notes

- Final state: `blocked / waiting_for_human_review`
- Do not push, merge, or self-approve
- Write all artifacts to `~/.hermes/task-artifacts/<task-key>/`

## Worker preflight guard

Before making any changes, run the guard to verify your workspace:

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/<task-key>

python3 scripts/kanban_worker_guard.py \
  --project bullet-journal \
  --task-key <task-key>
```

The guard fails fast if you are in the wrong directory, on the wrong branch,
or the main repo has uncommitted changes. It does not replace human review.
