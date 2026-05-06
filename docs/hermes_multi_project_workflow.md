# Hermes Multi-Project Workflow

## Overview

This document describes the multi-project Kanban workflow for Hermes agents,
using a shared project registry and a single generic safe submitter script.

## Why a Project Registry?

The original Bullet Journal workflow used a single-repo, single-project approach:

```text
scripts/bj_kanban_create.py  # hardcoded for bullet-journal only
```

This worked for the initial pilot, but does not scale:

- Adding a new project (e.g. alphaforge) would require copying or branching `bj_*` scripts
- Each repo would need its own copy of the submitter logic
- Governance rules would be duplicated across repos

The correct architecture is:

```text
one generic tool layer + project registry config
```

The registry (`config/projects.yaml`) is the single source of truth for:

- Where each project's repo lives
- What its default branch is
- What artifact root to use
- What task prefix to use
- Who the default assignee is
- What branch prefix to use for worktrees

## Project Registry Structure

```yaml
projects:
  bullet-journal:
    repo: /home/ubuntu/bullet_journal_app
    default_branch: main
    task_prefix: BJ
    artifact_root: /home/ubuntu/.hermes/task-artifacts
    default_assignee: bullet-eng
    branch_prefix: worktree/
```

### Fields

| Field | Required | Description |
|---|---|---|
| `repo` | Yes | Absolute path to the project's git repository |
| `default_branch` | Yes | The branch worktrees are created from (e.g. `main`) |
| `task_prefix` | Yes | Prefix for task keys (e.g. `BJ` for bullet-journal) |
| `artifact_root` | Yes | Base path for task artifacts |
| `default_assignee` | Yes | Default Hermes profile for task assignment |
| `branch_prefix` | Yes | Prefix for worktree branches (e.g. `worktree/`) |

## Generic Safe Submitter

`scripts/kanban_create_safe.py` is the generic safe submitter. It:

- Reads `config/projects.yaml` to resolve project configuration
- Validates the project exists in the registry
- Validates the repo exists and is a git repository
- Validates the main repo is clean before creating a worktree
- Validates the current branch matches the project's default branch
- Creates a worktree under `<repo>/.worktrees/<task-key>`
- Creates a branch named `<branch_prefix><task-key>` (e.g. `worktree/BJ-0017A`)
- Creates an artifact folder under `<artifact_root>/<task-key>`
- Prepends mandatory governance text to the task body
- Invokes `hermes kanban create` with `--workspace dir:<verified-worktree>`
- Never runs: `git push`, `git merge`, `git reset --hard`, `git clean -fd`

## How It Differs from `bj_kanban_create.py`

| Aspect | `bj_kanban_create.py` | `kanban_create_safe.py` |
|---|---|---|
| Config | Hardcoded bullet-journal paths | `config/projects.yaml` registry |
| Multi-project | No | Yes |
| Project registration | N/A | Required in YAML |
| Generic | No | Yes |

Both scripts share the same safety guarantees (no dangerous git commands,
verified worktree, governance header).

## Adding a New Project

To add a new project (e.g. alphaforge):

1. Add an entry to `config/projects.yaml`:

```yaml
projects:
  bullet-journal:
    repo: /home/ubuntu/bullet_journal_app
    default_branch: main
    task_prefix: BJ
    artifact_root: /home/ubuntu/.hermes/task-artifacts
    default_assignee: bullet-eng
    branch_prefix: worktree/
  alphaforge:
    repo: /home/ubuntu/alphaforge
    default_branch: main
    task_prefix: AF
    artifact_root: /home/ubuntu/.hermes/task-artifacts
    default_assignee: alpha-eng
    branch_prefix: worktree/
```

2. Ensure the repo exists and is a git repository
3. No script changes needed

## Current Limitation

This task only registers `bullet-journal`. AlphaForge, SignalForge, and bs_pricer
entries are intentionally omitted — they will be added as those projects are onboarded.

## Example Commands

### Dry Run

```bash
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-0017A \
  --title "Introduce project registry and generic safe submitter skeleton" \
  --body-file /tmp/BJ-0017A.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h \
  --dry-run
```

### Real Run

```bash
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-0017A \
  --title "Introduce project registry and generic safe submitter skeleton" \
  --body-file /tmp/BJ-0017A.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

## Governance

All tasks created by the generic submitter include mandatory governance text:

- Work only in the verified worktree
- Do not operate from the main repo
- No git push, merge, reset --hard, clean -fd
- Do not self-approve
- Final state must be `blocked / waiting_for_human_review` unless explicitly allowed
- Write artifacts to the artifact folder
- Record `git status --short --untracked-files=all` in artifacts

## Files

| File | Purpose |
|---|---|
| `config/projects.yaml` | Project registry |
| `scripts/kanban_create_safe.py` | Generic safe submitter |
| `scripts/bj_kanban_create.py` | Bullet Journal-specific submitter (unchanged) |
| `docs/hermes_multi_project_workflow.md` | This document |
