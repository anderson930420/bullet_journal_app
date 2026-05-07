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

## PR Handoff Helper

`scripts/kanban_pr_handoff.py` is a generic PR handoff helper that safely prepares a
completed worktree for human review. It validates the workspace, stages and commits
changes, pushes the task branch, and optionally creates a GitHub PR.

### What it does

1. Validates running from the expected worktree (not main repo)
2. Validates current branch matches expected branch
3. Validates main repo is clean
4. Displays `git status --short --untracked-files=all` and `git diff --stat`
5. Fails if no repo changes to commit
6. Stages all changes (including untracked)
7. Shows staged status before commit
8. Requires `--confirm` for real actions (fails without it)
9. Commits with `--commit-message`
10. Pushes branch with `git push -u origin <branch>`
11. Creates PR with `gh pr create` (if gh CLI is available and `--skip-pr` not given)
12. Writes `<artifact-dir>/pr_info.json` after successful PR creation
13. Updates `artifact_manifest.json` `pr_url` and `status` fields if it exists

### Safety properties

- **Never merges** — only creates and pushes the PR; merge is the human reviewer's action
- **Never marks a task done** — worker autonomy ends at the PR
- **Never self-approves** — human review is the final approval surface
- **Fails from main repo** — must be run from a worktree
- **Dry-run mode** — no persistent changes; safe to preview

### When to use it

Use the PR handoff helper after a task is complete and the worker has written all
required artifacts. It is the bridge between "worker done" and "human review".

### Dry-run example

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/BJ-0010R

python3 scripts/kanban_pr_handoff.py \
  --project bullet-journal \
  --task-key BJ-0010R \
  --commit-message "tooling: add generic kanban PR handoff helper" \
  --title "tooling: add generic kanban PR handoff helper" \
  --body-file /home/ubuntu/.hermes/task-artifacts/BJ-0010R/completion_report.md \
  --dry-run
```

### Real-run example

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/BJ-0010R

python3 scripts/kanban_pr_handoff.py \
  --project bullet-journal \
  --task-key BJ-0010R \
  --commit-message "tooling: add generic kanban PR handoff helper" \
  --title "tooling: add generic kanban PR handoff helper" \
  --body-file /home/ubuntu/.hermes/task-artifacts/BJ-0010R/completion_report.md \
  --confirm
```

### Why it does not merge

Merge is the human reviewer's action. The helper:
- Creates the PR for human review
- Pushes the branch so the PR is accessible
- Writes `pr_info.json` with the PR URL
- Updates `artifact_manifest.json` with `pr_url` and `status: waiting_for_human_review`

The human reviewer then approves and merges via GitHub. This preserves human agency
as the final gate.

### How it writes `pr_info.json`

After successful PR creation, the helper writes:

```json
{
  "project": "bullet-journal",
  "task_key": "BJ-0010R",
  "branch": "worktree/BJ-0010R",
  "base": "main",
  "remote": "origin",
  "commit": "<commit-sha>",
  "pr_url": "https://github.com/...",
  "created_by": "kanban_pr_handoff.py"
}
```

If `artifact_manifest.json` exists, it also updates:
- `pr_url` — the GitHub PR URL
- `status` — set to `waiting_for_human_review` (if not already in a terminal state)

### How it relates to `artifact_manifest.json`

`artifact_manifest.json` is the canonical record of task state. The PR handoff helper
updates it as a courtesy when a PR is created, so downstream tools (dashboards, review
tools) can find the PR URL without parsing git history. The manifest's `status` field
transitions from `running` to `waiting_for_human_review` at this point.

## Accept / Cleanup Helper

`scripts/kanban_accept_cleanup.py` is a generic post-merge accept / cleanup helper that
standardizes the cleanup flow after a human reviewer has already accepted and merged a PR.

### What it does

1. Validates running from a verified worktree (via main repo check)
2. Validates main repo is clean
3. **Dry-run**: prints planned actions without making any changes
4. **Real mode** (requires `--confirm`): fetches, checks out base branch, pulls --ff-only
5. Verifies merged commit is in base branch history (if provided)
6. Verifies PR is merged via gh CLI (if PR URL/number provided)
7. Writes `<artifact-dir>/decision.md` with the human decision
8. Updates `artifact_manifest.json` `status` field (done/rejected)
9. Removes task worktree without force by default (accepted only)
10. Deletes local task branch if it exists
11. Deletes remote task branch only with `--delete-remote-branch`
12. Adds Hermes Kanban comment if `--task-id` provided
13. Completes Hermes Kanban task if `--task-id` provided and decision=accepted

### What it does NOT do

- Never merges a PR
- Never approves work by itself
- Never runs `git merge`
- Never runs `gh pr merge`
- Never pushes directly to main
- Never completes a Hermes task unless `--task-id` is provided and decision=accepted

### Safety properties (5 blocker fixes)

**Blocker fix #1 — Dry-run is side-effect free:**
In `--dry-run` mode, the helper performs NO mutating operations: no git fetch/checkout/pull,
no file writes, no worktree removal, no branch deletion, no Hermes comment/complete.
It only prints the planned actions.

**Blocker fix #2 — Missing --confirm fails before any mutating action:**
If neither `--dry-run` nor `--confirm` is provided, the helper exits with error code 1
before performing any git operations, file writes, or Hermes calls.

**Blocker fix #3 — No force-removal by default:**
Worktree removal uses `git worktree remove` (non-force) by default. If the worktree is dirty,
removal fails with a clear error message. Optional `--force-remove-worktree` enables
`git worktree remove --force`, but only in `--confirm` mode.

**Blocker fix #4 — Robust local branch detection:**
Uses `git show-ref --verify --quiet refs/heads/<branch>` instead of raw `git branch` output,
avoiding issues with leading spaces or the `*` marker.

**Blocker fix #5 — PR required: yes:**
The completion report explicitly states `PR required: yes` since the helper modifies
repo files and adds a script.

### When to use it

Use the accept/cleanup helper after a human reviewer has:
1. Reviewed the PR on GitHub
2. Approved and merged it to main
3. Recorded the merge commit SHA

### Dry-run example

```bash
MAIN_HEAD=$(cd /home/ubuntu/bullet_journal_app && git rev-parse --short HEAD)

python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-0011R \
  --task-id t_example \
  --decision accepted \
  --merged-commit "$MAIN_HEAD" \
  --dry-run
```

### Real-run example

```bash
MAIN_HEAD=$(cd /home/ubuntu/bullet_journal_app && git rev-parse --short HEAD)

python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-0011R \
  --task-id t_example \
  --decision accepted \
  --merged-commit "$MAIN_HEAD" \
  --confirm
```

### How it updates decision.md

In confirmed real mode, writes `<artifact-dir>/decision.md`:

```markdown
# Task Decision

- project: bullet-journal
- task_key: BJ-0011R
- task_id: t_example
- decision: accepted
- merged_commit: 977abb7
- decided_by: human
- recorded_by: kanban_accept_cleanup.py
- recorded_at: 2026-05-08T03:45:00+00:00

## Notes

Human review accepted. PR has been merged to main.
```

Dry-run does NOT write decision.md.

### How it updates artifact_manifest.json

If `artifact_manifest.json` exists in the artifact directory, it updates the `status` field:

| Decision  | Status    |
|-----------|-----------|
| accepted  | done      |
| rejected  | rejected  |
| abandoned | rejected  |

Existing fields (`checks`, `artifacts`, `changed_files`, `recommendation`) are preserved.

### How it handles worktree cleanup

For `decision=accepted`:
1. Checks if the task worktree exists
2. Verifies it is clean (non-force removal would fail if dirty)
3. Removes it using `git worktree remove` (non-force by default)
4. If dirty and `--force-remove-worktree --confirm`: uses `git worktree remove --force`
5. Deletes the local task branch
6. Optionally deletes the remote task branch with `--delete-remote-branch`

### Why it does not merge PRs

Merge is the human reviewer's action on GitHub. The helper runs after that merge,
receiving the merge commit SHA as input. It never runs `git merge` or `gh pr merge`.
This preserves human agency as the final gate.

### How it relates to human review

The helper is the bridge between "human merged PR on GitHub" and "task artifacts
updated, worktree cleaned up, Hermes task completed". It requires explicit human
confirmation (`--confirm`) and never self-completes without confirmation.

## Artifact Contract

Workers produce artifacts following the **Hermes Artifact Contract** defined in
`docs/hermes_artifact_contract.md`. The contract standardizes the artifact folder
layout and `artifact_manifest.json` schema so downstream tools (dashboards, PR handoff
helpers, accept/cleanup helpers) can read task outputs consistently.

The `scripts/kanban_artifact_manifest.py` helper manages `artifact_manifest.json`:

- `init` — create a manifest from CLI args or project registry
- `validate` — verify a manifest is structurally valid

## Files

| File | Purpose |
|---|---|
| `config/projects.yaml` | Project registry |
| `scripts/kanban_create_safe.py` | Generic safe submitter |
| `scripts/kanban_new_task_safe.py` | One-command submit wrapper |
| `scripts/kanban_worker_guard.py` | Worker preflight guard |
| `scripts/kanban_artifact_manifest.py` | Artifact manifest init/validate helper |
| `scripts/kanban_pr_handoff.py` | PR handoff helper (staging, commit, push, PR creation) |
| `scripts/kanban_accept_cleanup.py` | Post-merge accept/cleanup helper (decision.md, manifest, worktree, Hermes) |
| `scripts/bj_task_template.py` | Template-based body generator |
| `scripts/bj_kanban_create.py` | Bullet Journal-specific submitter (unchanged) |
| `docs/hermes_artifact_contract.md` | Artifact contract schema and folder layout |
| `docs/hermes_multi_project_workflow.md` | This document |
