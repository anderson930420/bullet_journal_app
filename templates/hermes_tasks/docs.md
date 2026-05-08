# Documentation Task Template

## Purpose

Documentation tasks improve or add to project documentation without changing application behavior.

## Task type

Documentation.

## Key characteristics

- **Docs-only changes** — this task should not change application behavior
- **No app behavior changes** — only markdown, README, and doc files
- **Run formatting/checks** where applicable (e.g., markdown linting)

## Sections

```markdown
## Goal

<What documentation needs to be written or updated.>

## Background

<Context and motivation.>

## Allowed changes

- docs/*.md
- README.md (short pointers only)
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

## Artifact manifest initialization

After preflight guard passes, initialize the artifact manifest:

```bash
python3 scripts/kanban_artifact_manifest.py init \
  --project bullet-journal \
  --task-key <task-key> \
  --task-id <task-id> \
  --status running \
  --recommendation unknown \
  --requires-pr true \
  --output /home/ubuntu/.hermes/task-artifacts/<task-key>/artifact_manifest.json
```

Record the initialization in `completion_report.md`:

```
Artifact manifest initialized at:
/home/ubuntu/.hermes/task-artifacts/<task-key>/artifact_manifest.json
```

## Final validation

Before recording your final `blocked / waiting_for_human_review` state, run:

```bash
python3 scripts/kanban_artifact_manifest.py validate \
  --path /home/ubuntu/.hermes/task-artifacts/<task-key>/artifact_manifest.json
```

Record the validation result in `completion_report.md`:

```
Artifact manifest validation: PASS | FAIL
```

If the manifest is invalid, fix it before completing. Do not mark the task done
with an invalid manifest.
