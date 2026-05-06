# Implementation Task Template

## Purpose

Implementation tasks add new code, scripts, tooling, or infrastructure to the repository.

## Task type

Implementation / tooling.

## Key characteristics

- **Inspect existing code first** — understand current patterns before making changes
- **Make minimal scoped changes** — changes should be directly tied to the goal
- **Run relevant tests** — verify behavior before marking complete
- **Report changed files** — list all modified and new files in the final artifact

## Sections

```markdown
## Goal

<One-paragraph description of what must be built.>

## Background

<Context and motivation.>

## Allowed changes

- <list allowed files/folders>

## Implementation guidance

1. Inspect existing code first
2. Make minimal scoped changes
3. Run relevant tests
4. Report changed files
```

## Governance notes

- Final state: `blocked / waiting_for_human_review`
- Do not push, merge, or self-approve
- Write all artifacts to `~/.hermes/task-artifacts/<task-key>/`
