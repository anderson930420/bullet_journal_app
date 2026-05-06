# Bug Fix Task Template

## Purpose

Bug fix tasks address defects or incorrect behavior in the codebase.

## Task type

Bug fix.

## Key characteristics

- **Reproduce or explain the bug** — describe steps to reproduce or the root cause
- **Patch root cause** — fix the underlying issue, not just the symptom
- **Add or update tests where practical** — ensure the bug doesn't regress

## Sections

```markdown
## Goal

<What bug needs to be fixed.>

## Background

<Description of the bug and its impact.>

## Allowed changes

- <files that need to be modified to fix the bug>
- <test files to add or update>

## Bug fix guidance

1. Reproduce or explain the bug
2. Patch root cause
3. Add or update tests where practical
4. Verify the fix
```

## Required artifacts

Follow the Hermes Artifact Contract (`docs/hermes_artifact_contract.md`) for the
standard folder layout. Required files:

- `artifact_manifest.json` — machine-readable completion manifest
- `completion_report.md` — human-readable summary
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
