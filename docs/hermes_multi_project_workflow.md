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

## One-Command Task Submit Flow

For the common case of creating a new task with a generated body, the wrapper
`scripts/kanban_new_task_safe.py` combines both steps into a single command:

```bash
python3 scripts/kanban_new_task_safe.py \
  --project bullet-journal \
  --task-key BJ-0017B \
  --type implementation \
  --title "Add generic one-command task submit flow" \
  --goal "Generate a task body and submit it through the generic safe submitter." \
  --priority 1 \
  --max-runtime 2h \
  --dry-run
```

### When to use `kanban_new_task_safe.py`

Use the wrapper when you want:
- A single command to generate the task body AND submit it
- The template-based body generation (analysis, implementation, docs, bugfix, review)
- Preserved `default_assignee` fallback from the project registry
- A preview of what would be created before committing

Use `kanban_new_task_safe.py --dry-run` to verify the generated body and
planned worktree/artifact paths before creating anything.

### When to use `kanban_create_safe.py` directly

Use the generic submitter directly when:
- You already have a pre-written task body file (e.g. authored manually or by another tool)
- You want full control over every argument passed to `hermes kanban create`
- You need `--reuse-existing-worktree` or `--allow-non-main` flags not exposed by the wrapper

### How the wrapper relates to the submitter

The wrapper (`kanban_new_task_safe.py`) performs two steps:

1. **Generate body** — calls `scripts/bj_task_template.py` to produce a markdown task body
2. **Submit** — calls `scripts/kanban_create_safe.py` with the generated body file

In `--dry-run` mode, both steps run in preview mode; no worktree, artifact folder,
or Hermes task is created, and temporary body files are cleaned up before exit.

In real-run mode, the wrapper writes the body to `--body-output` (default: `/tmp/<task-key>.md`)
or to a path you specify, then calls `kanban_create_safe.py` which creates the worktree,
artifact folder, and Hermes task.

The wrapper stops at human review because the generated task body inherits governance
rules from the template system.

### Example

**Dry run:**

```bash
python3 scripts/kanban_new_task_safe.py \
  --project bullet-journal \
  --task-key BJ-0017B \
  --type implementation \
  --title "Add generic one-command task submit flow" \
  --goal "Generate a task body and submit it through the generic safe submitter." \
  --priority 1 \
  --max-runtime 2h \
  --dry-run
```

**Real run:**

```bash
python3 scripts/kanban_new_task_safe.py \
  --project bullet-journal \
  --task-key BJ-0017B \
  --type implementation \
  --title "Add generic one-command task submit flow" \
  --goal "Generate a task body and submit it through the generic safe submitter." \
  --priority 1 \
  --max-runtime 2h
```

### Optional arguments

| Argument | Description |
|---|---|
| `--assignee` | Assignee profile (falls back to project's `default_assignee`) |
| `--priority` | Task priority (integer) |
| `--max-runtime` | Max runtime (e.g. `2h`, `30m`) |
| `--config` | Path to `projects.yaml` (default: `config/projects.yaml`) |
| `--body-output` | Write generated body to this path (default: `/tmp/<task-key>.md`) |
| `--overwrite` | Allow overwriting an existing body file |
| `--dry-run` | Preview only; no persistent side effects |
| `--json` | Pass `--json` to `hermes kanban create` |

## Worker Preflight Guard

`scripts/kanban_worker_guard.py` is a generic preflight guard that workers run at the
start of every task to verify they are operating inside the expected verified worktree,
on the expected branch, and not modifying the main repo directly.

### What it checks

1. Loads `config/projects.yaml` and validates the project exists
2. Resolves the project repo path and verifies it is a git repository
3. Resolves expected worktree (`<repo>/.worktrees/<task-key>`) and expected branch (`<branch_prefix><task-key>`)
4. Determines the actual git root and current branch via `git rev-parse` and `git branch --show-current`
5. **Fails** if the actual git root does not exactly equal the expected worktree path
6. **Fails** if the actual branch does not exactly equal the expected branch
7. **Fails** if the worker is running in the main repo root instead of a worktree
8. **Fails** if the main repo has uncommitted or untracked changes
9. Optionally writes a `guard_report.txt` artifact

### When to run it

Run the guard **before making any changes** at the start of every task:

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/<task-key>

python3 scripts/kanban_worker_guard.py \
  --project bullet-journal \
  --task-key BJ-0016R
```

### Example command

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/BJ-0016R

python3 scripts/kanban_worker_guard.py \
  --project bullet-journal \
  --task-key BJ-0016R \
  --write-artifacts
```

### What failures mean

| Error | Meaning |
|---|---|
| `Wrong worktree` | Worker is running in the wrong directory — check `pwd` |
| `Wrong branch` | Worker checked out the wrong branch — use `git worktree list` |
| `Worker is running in main repo` | Worker must use the worktree, not the main repo |
| `Main repo has uncommitted/untracked changes` | Clean the main repo before proceeding |

### Why it complements but does not replace human review

The guard enforces mechanical preconditions — correct directory, branch, and clean main repo.
It cannot detect:
- Whether the worker is making the right changes
- Whether the implementation is correct or safe
- Whether the task body was followed correctly

Human review remains mandatory for quality, correctness, and safety.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | All preflight checks passed |
| 1 | One or more checks failed (see error messages) |
| 2 | Internal error (missing config, bad arguments, etc.) |

## Files

| File | Purpose |
|---|---|
| `config/projects.yaml` | Project registry |
| `scripts/kanban_create_safe.py` | Generic safe submitter |
| `scripts/bj_task_template.py` | Template-based body generator |
| `scripts/kanban_new_task_safe.py` | One-command submit wrapper |
| `scripts/kanban_worker_guard.py` | Worker preflight guard |
| `scripts/bj_kanban_create.py` | Bullet Journal-specific submitter (unchanged) |
| `docs/hermes_multi_project_workflow.md` | This document |
