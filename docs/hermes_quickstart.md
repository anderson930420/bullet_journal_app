# Hermes Workflow Quickstart

A concise guide to the Hermes Kanban workflow tooling for `bullet_journal_app`.

---

## What Is This?

Hermes is an AI agent orchestrator with a shared Kanban board (`~/.hermes/kanban.db`). Tasks are created, assigned to specialist profiles (e.g. `bullet-eng`), and workers operate inside **verified git worktrees** to produce artifacts and documentation changes.

---

## Core Principles

1. **Verified worktrees only.** Workers must operate inside `.worktrees/<task-key>/`, never in the main repo at `/home/ubuntu/bullet_journal_app`.
2. **Human review before merge.** All changes stay in the worktree branch until a human approves and merges via GitHub.
3. **Artifacts required.** Every task must produce artifacts in `~/.hermes/task-artifacts/<task-key>/`.
4. **Governance rules are enforced.** Workers must not push or merge; helper scripts may push task branches for PR handoff only.

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/kanban_new_task_safe.py` | Primary: create a task from a template spec with a verified worktree |
| `scripts/kanban_create_safe.py` | Create a task with a hand-written detailed spec |
| `scripts/bj_kanban_create.py` | Bullet Journal-specific legacy/specialized task submitter |
| `scripts/kanban_pr_handoff.py` | Generate a PR from a completed task's worktree |
| `scripts/kanban_accept_cleanup.py` | Post-merge: record decision.md, update artifact_manifest.json, remove worktree/branches, optionally complete the Hermes task |
| `scripts/kanban_artifact_manifest.py` | Validate or generate `artifact_manifest.json` for a task |
| `scripts/kanban_worker_guard.py` | Guard that verifies the worker is running from the correct worktree |

---

## Task Lifecycle

```
human creates task via kanban_new_task_safe.py (or kanban_create_safe.py)
        │
        ▼
worker spawns in verified worktree dir:~/.worktrees/<task-key>
        │
        ▼
worker does work (docs, code, tests)
        │
        ▼
worker writes artifacts → ~/.hermes/task-artifacts/<task-key>/
        │
        ▼
worker marks blocked / waiting_for_human_review
        │
        ▼
human reviews artifacts + git diff
        │
        ├── revise  →  worker addresses feedback, resubmits
        │
        └── accept  →  kanban_pr_handoff.py creates PR
                          human merges PR on GitHub
                              kanban_accept_cleanup.py records decision
                              and cleans up worktree/branches
```

---

## Creating a Task

**Normal template tasks** — use `kanban_new_task_safe.py`:

```bash
python3 scripts/kanban_new_task_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --type docs \
  --title "Short task title" \
  --goal "Describe the documentation change to make." \
  --priority 1 \
  --max-runtime 2h
```

**Hand-written detailed specs** — use `kanban_create_safe.py`:

```bash
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --title "Short task title" \
  --body-file /tmp/task.md \
  --priority 1 \
  --max-runtime 2h
```

Both scripts:
1. Create a git worktree at `.worktrees/<task-key>` branched from `main`
2. Create the artifact folder at `~/.hermes/task-artifacts/<task-key>/`
3. Create the Hermes Kanban task with `workspace_kind=dir` pointing to the verified worktree

**Bullet Journal-specific specialized submitter** — `bj_kanban_create.py` (legacy):

```bash
python3 scripts/bj_kanban_create.py \
  --task-key BJ-XXXX \
  --title "Short task title" \
  --body-file /tmp/task.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

---

## Required Artifacts

Every task must produce:

| File | Content |
|------|---------|
| `git_status.txt` | `git status --short --untracked-files=all` |
| `worktree_info.txt` | `git worktree list` output |
| `completion_report.md` | Changed files, checks run, summary, PR recommendation |

---

## Key Docs

| Doc | What It Covers |
|-----|---------------|
| `docs/hermes_kanban_governance.md` | Full governance rules, forbidden commands, breach response |
| `docs/hermes_multi_project_workflow.md` | Project registry architecture, multi-project scaling |
| `docs/hermes_safe_task_submitter.md` | Why `workspace=worktree` is not trusted; the verified worktree approach |
| `docs/hermes_artifact_contract.md` | Artifact folder schema and validation |
| `docs/incidents/BJ-0004-governance-breach.md` | The incident that drove governance hardening |
| `scripts/kanban_worker_guard.py` | Worktree verification guard for workers |

---

## Forbidden Commands (No Human Approval)

Workers must NOT run:
- `git push` to any remote
- `git merge` into `main`
- `git reset --hard`
- `git clean -fd`
- `git filter-repo` / BFG / `git filter-branch`
- Self-approval of changes

**Note:** Human-confirmed helper scripts may push task branches for PR handoff. No direct push to `main`.

---

## Smoke Test

To verify the workflow tooling works:

```bash
python3 scripts/kanban_worker_guard.py --project bullet-journal --task-key BJ-XXXX --write-artifacts
```

The guard exits 0 when run from the correct worktree, exits 1 with error messages when run from the wrong location or with the wrong task key.
