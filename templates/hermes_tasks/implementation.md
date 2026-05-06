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

## Required artifacts

Follow the Hermes Artifact Contract (`docs/hermes_artifact_contract.md`) for the
standard folder layout. Required files:

- `artifact_manifest.json` — machine-readable completion manifest
- `completion_report.md` — human-readable summary (including changed files)
- `git_status.txt` — `git status --short --untracked-files=all`
- `worktree_info.txt` — `git worktree list` + branch info

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
