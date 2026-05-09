# Hermes Workflow Bootstrap Guide

**Document version:** 1.0
**Task key:** BJ-0030
**Purpose:** Package the Hermes/Kanban self-hosted AI-worker workflow for reuse across other repositories.

---

## Overview

This guide explains how to port the existing Hermes workflow from `bullet_journal_app` into a new repository (e.g. SignalForge, AlphaForge, or a new small project).

The workflow is **human-review-first**: AI workers do isolated work in verified git worktrees, then hand off to a human for review, PR creation, merge, and cleanup. Workers never push, merge, approve, complete, or clean up their own tasks.

---

## What to Copy — Reusable File Inventory

### Workflow Core Scripts

These scripts are project-agnostic and can be copied verbatim:

| File | Purpose | Key properties |
|------|---------|----------------|
| `scripts/kanban_create_safe.py` | Safe task creation via project registry | Creates verified worktrees, rejects forbidden git commands |
| `scripts/kanban_new_task_safe.py` | Template-based task generation | Uses project registry, same safety guarantees |
| `scripts/kanban_pr_handoff.py` | PR creation helper | Stages, commits, pushes, creates GitHub PR, writes `pr_info.json` |
| `scripts/kanban_accept_cleanup.py` | Post-merge and no-PR cleanup | Verifies merge, removes worktree, deletes branch, writes `decision.md` |
| `scripts/kanban_workflow_regression.py` | All-in-one workflow audit | Runs lifecycle + manifest + PR metadata checks for any phase |
| `scripts/kanban_task_audit.py` | Lifecycle audit sub-check | Detects forbidden-command usage, self-completion, artifact false-positives |
| `scripts/kanban_artifact_manifest.py` | Manifest init/validate | Schema enforcement for `artifact_manifest.json` |
| `scripts/kanban_worker_guard.py` | Workspace verification guard | Verifies dir, branch, clean main-repo; writes `guard_report.txt` |

### Audit Scripts

| File | Purpose |
|------|---------|
| `scripts/kanban_task_audit.py` | Lifecycle audit (forbidden commands, self-completion detection) |
| `scripts/kanban_workflow_regression.py` | Consolidated regression audit (review / post-handoff / post-cleanup phases) |

### Documentation

| File | Purpose |
|------|---------|
| `docs/hermes_workflow_operating_model.md` | Detailed lifecycle, commands, artifact contract, failure modes |
| `docs/hermes_workflow_bootstrap.md` | This guide |
| `docs/hermes_artifact_contract.md` | Artifact schema and file conventions |

---

## Governance Model — Must Be Preserved

The following rules are **non-negotiable** in any port:

1. **Workers must use verified isolated worktrees** — `dir:<worktree>` workspace, never `--workspace worktree` auto-binding.
2. **Workers must not run forbidden commands** — `git push`, `git merge`, `git reset --hard`, `git clean -fd`.
3. **Workers must not self-approve** — no `hermes kanban complete` calls unless task body explicitly allows it.
4. **Workers must finish by returning to `blocked / waiting_for_human_review`** — not `done`.
5. **Human reviewer performs PR handoff, merge, accept cleanup, and post-cleanup audit**.
6. **Do not use `hermes kanban create --workspace worktree`** — always use `dir:` workspace.
7. **If a stray root-level file exists, remove only the specific stray file after human review or explicit instruction**.

---

## First-Port Checklist for Another Project

### Prerequisites

- [ ] Target repo is a valid git repository
- [ ] Repo has a default branch (`main` or similar)
- [ ] Repo is clean (no uncommitted changes)
- [ ] Python 3 is available (`python3 --version`)
- [ ] `gh` CLI is installed and authenticated (for GitHub PR creation)
- [ ] Hermes Agent is installed and configured

### Required Project-Specific Values to Change

When copying into a new repo, edit `config/projects.yaml` (create it if missing):

```yaml
projects:
  my-project:
    repo: /path/to/my/project           # Absolute path to the new repo
    default_branch: main                # Or: "master" or another branch name
    task_prefix: PROJECT-NAME           # Short prefix for task keys (e.g. "SF", "ALPHA")
    artifact_root: /home/ubuntu/.hermes/task-artifacts  # Shared artifact location
    default_assignee: my-profile        # Hermes profile that owns this project
    branch_prefix: worktree/            # Prefix for task branches (keep "worktree/")
```

### Required New Files

1. **`config/projects.yaml`** — Project registry (see above)
2. **`docs/hermes_workflow_bootstrap.md`** — This guide (copy from bullet-journal-app)
3. **`docs/hermes_workflow_operating_model.md`** — Detailed operating model (copy from bullet-journal-app)
4. **`docs/hermes_artifact_contract.md`** — Artifact schema (copy from bullet-journal-app)

### Optional but Recommended

- **`templates/hermes_project_registry_example.yaml`** — Example project registry (see template below)
- **`scripts/kanban_bootstrap_check.py`** — Read-only bootstrap validation (see script below)

### First Task Creation

```bash
# Dry run first
python3 scripts/kanban_create_safe.py \
  --project my-project \
  --task-key PROJECT-001 \
  --title "First bootstrap task" \
  --body-file /tmp/first-task.md \
  --assignee my-profile \
  --priority 1 \
  --max-runtime 2h \
  --dry-run

# If dry-run looks correct, run for real
python3 scripts/kanban_create_safe.py \
  --project my-project \
  --task-key PROJECT-001 \
  --title "First bootstrap task" \
  --body-file /tmp/first-task.md \
  --assignee my-profile \
  --priority 1 \
  --max-runtime 2h
```

---

## Command Examples for Every Phase

### Safe Task Creation — Dry Run

```bash
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --title "Descriptive title" \
  --body-file /tmp/task-body.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h \
  --dry-run
```

### Safe Task Creation — Confirm

```bash
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --title "Descriptive title" \
  --body-file /tmp/task-body.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

### Review-Phase Regression Audit

```bash
python3 scripts/kanban_workflow_regression.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --phase review
```

### PR Handoff — Dry Run

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/BJ-XXXX

python3 scripts/kanban_pr_handoff.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --commit-message "description of change" \
  --title "PR title" \
  --body-file /home/ubuntu/.hermes/task-artifacts/BJ-XXXX/completion_report.md \
  --dry-run
```

### PR Handoff — Confirm

```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/BJ-XXXX

python3 scripts/kanban_pr_handoff.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --commit-message "description of change" \
  --title "PR title" \
  --body-file /home/ubuntu/.hermes/task-artifacts/BJ-XXXX/completion_report.md \
  --confirm
```

### Accept Cleanup — Dry Run (with PR)

```bash
MAIN_HEAD=$(cd /home/ubuntu/bullet_journal_app && git rev-parse --short HEAD)

python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision accepted \
  --merged-commit "$MAIN_HEAD" \
  --dry-run
```

### Accept Cleanup — Confirm (with PR)

```bash
MAIN_HEAD=$(cd /home/ubuntu/bullet_journal_app && git rev-parse --short HEAD)

python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision accepted \
  --merged-commit "$MAIN_HEAD" \
  --confirm
```

### Accept Cleanup — Dry Run (no-PR, no repo changes)

```bash
python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision accepted \
  --allow-missing-merged-commit \
  --dry-run
```

### Accept Cleanup — Confirm (no-PR)

```bash
python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision accepted \
  --allow-missing-merged-commit \
  --confirm
```

### Post-Cleanup Regression Audit

```bash
python3 scripts/kanban_workflow_regression.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --phase post-cleanup
```

---

## Known Unsafe Commands — Do Not Use

| Command | Why it's unsafe |
|---------|-----------------|
| `hermes kanban create --workspace worktree` | Uses worktree auto-binding instead of verified `dir:` worktree. Workers may operate from the wrong directory. |
| `git reset --hard` | Destroys uncommitted work. Used in the BJ-0004 breach. Never use in a workflow task. |
| `git clean -fd` | Removes untracked files and directories. Can delete artifact folders or worktree contents. Never use in a workflow task. |
| Worker self-completing tasks | Workers marking their own tasks `done` bypasses human review. Only `blocked / waiting_for_human_review` is permitted unless task body explicitly allows `done`. |

## Known Failure Modes

| Failure | Symptom | Fix |
|---------|---------|-----|
| **Dirty worktree, no-PR manifest** | Worktree has changes but `requires_pr: false` in manifest | Human reviewer checks `git diff --stat` before accepting. If diff exists, PR handoff is mandatory. |
| **Self-completion of review task** | Worker called `hermes kanban complete` on a review/analysis task | Task must end in `blocked / waiting_for_human_review`. `kanban_task_audit.py` detects this. |
| **Manifest not initialized** | `artifact_manifest.json` missing or in `running` status | Worker must run `kanban_artifact_manifest.py init` before blocking |
| **Treating no-PR accept as PR merged** | `decision.md` says "PR merged" when no PR existed | Only use `--allow-missing-merged-commit` when `requires_pr: false` AND `changed_files: []` |
| **changed_files mismatch** | Manifest has `changed_files: []` but worktree has changes | Human reviewer must check `git diff --stat` before accepting |

---

## Project-Specific Values Reference

When configuring a new project, these values must be changed:

| Value |bullet-journal example | What to change it to |
|-------|----------------------|----------------------|
| `repo` | `/home/ubuntu/bullet_journal_app` | Absolute path to the new repo |
| `default_branch` | `main` | Default branch name of new repo |
| `task_prefix` | `BJ` | Short prefix for task keys (e.g. `SF`, `ALPHA`) |
| `artifact_root` | `/home/ubuntu/.hermes/task-artifacts` | Can stay shared or be repo-specific |
| `default_assignee` | `bullet-eng` | Hermes profile name for the new project |
| `branch_prefix` | `worktree/` | Keep `worktree/` — workers use `worktree/<task-key>` branches |
| Worktree path | `.worktrees/<task-key>` | Workers operate inside `<repo>/.worktrees/<task-key>` |
| Artifact path | `~/.hermes/task-artifacts/<task-key>/` | Where artifacts are stored |

---

## Responsibilities Matrix

| Actor | Responsibilities |
|-------|-----------------|
| **AI Worker** | Work inside verified `dir:<worktree>`. Write all required artifacts. Return task to `blocked / waiting_for_human_review`. Never push, merge, self-approve, or complete. |
| **Human Reviewer** | Review artifacts and git diff. Decide accept/revise/reject. Run PR handoff if repo diff exists. Merge PR on GitHub. Run accept cleanup. Run post-cleanup regression audit. |
| **PR Handoff** (human-initiated via script) | Stage, commit, push branch. Create GitHub PR. Write `pr_info.json`. |
| **Cleanup** (human-initiated via script) | Verify merged commit. Remove worktree. Delete task branch. Write `decision.md`. Update manifest. |
| **Audit** (human-initiated via script) | Run `kanban_workflow_regression.py --phase post-cleanup`. Confirm worktree removed, branch deleted, artifacts correct. |

---

## Optional: Bootstrap Validation Script

See `scripts/kanban_bootstrap_check.py` for a read-only script that checks:

- Expected workflow scripts exist
- Expected docs exist
- Repo has a `.git` directory
- Current directory appears to be the repo root
- No obvious missing bootstrap files

Run with:
```bash
python3 scripts/kanban_bootstrap_check.py
```

Output is PASS/WARN/FAIL per check. The script is completely read-only and makes no mutations.

---

## Optional: Project Registry Template

See `templates/hermes_project_registry_example.yaml` for an annotated example showing all configurable fields and their purposes.