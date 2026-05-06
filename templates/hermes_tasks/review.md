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
