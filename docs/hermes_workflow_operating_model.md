# Hermes Workflow Operating Model

**Document version:** 1.0
**Last updated:** 2026-05-09
**Task key:** BJ-0027

---

## Purpose and Scope

This document describes the current operating model for the self-hosted Hermes/Kanban workflow used in the `bullet_journal_app` project (and applicable to other projects in the `config/projects.yaml` registry).

This operating model is designed for **human-review-first AI worker automation**:
- AI workers (agents) perform tasks inside verified git worktrees
- All work is staged for human review before reaching the `main` branch
- No direct pushes, merges, or self-approvals are permitted
- Human reviewers hold final authority over all changes

This is **not** a feature change document. It is a consolidation of existing behavior after the workflow hardening tasks (BJ-0021 through BJ-0026) so the workflow can be reused and audited without reconstructing it from chat history.

---

## Core Lifecycle

### 1. Task Creation

A human creates a task using one of:

```bash
# One-command template-based task creation (preferred)
python3 scripts/kanban_new_task_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --type implementation \
  --title "Short descriptive title" \
  --goal "Describe what this task must achieve." \
  --priority 1 \
  --max-runtime 2h

# Hand-written spec task creation
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --title "Short descriptive title" \
  --body-file /tmp/task.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h

# Legacy bullet-journal-specific submitter
python3 scripts/bj_kanban_create.py \
  --task-key BJ-XXXX \
  --title "Short descriptive title" \
  --body-file /tmp/task.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

**What the safe helper does (all three scripts):**

1. Validates main repo is clean (`git status`)
2. Validates current branch is the project's default branch (`main` for bullet-journal)
3. Creates a git worktree at `<repo>/.worktrees/<task-key>` (e.g. `/home/ubuntu/bullet_journal_app/.worktrees/BJ-0027`)
4. Creates a branch named `worktree/<task-key>` (e.g. `worktree/BJ-0027`) branched from `main`
5. Creates the artifact folder at `<artifact_root>/<task-key>/` (e.g. `/home/ubuntu/.hermes/task-artifacts/BJ-0027/`)
6. Prepends mandatory governance text to the task body
7. Creates the Hermes Kanban task with `workspace_kind=dir` pointing to the verified worktree
8. Never runs: `git push`, `git merge`, `git reset --hard`, `git clean -fd`

The worker spawns with `workspace_kind=dir` pointing to the verified worktree. Workers must **never** operate from the main repo at `/home/ubuntu/bullet_journal_app`.

### 2. Verified Worktree

Workers operate **only** inside the verified worktree. The worktree path is:
- Primary: `dir:/home/ubuntu/bullet_journal_app/.worktrees/<task-key>`

Workers **must** verify the workspace at task start:
```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git worktree list
git status --short --untracked-files=all
```

The `scripts/kanban_worker_guard.py` guard automates this verification:
```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/<task-key>

python3 scripts/kanban_worker_guard.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --write-artifacts
```

If the guard fails (wrong directory, wrong branch, dirty main repo), the worker must block immediately.

### 3. Worker Execution

Workers perform the task inside the worktree:
- Edit only files inside the worktree
- Never touch `/home/ubuntu/bullet_journal_app` directly
- Never run forbidden commands
- Write all artifacts to the artifact folder

### 4. Artifact Creation

Before completing, workers write required artifacts to `<artifact_root>/<task-key>/`:

**Required files:**
- `completion_report.md` — human-readable summary of work done, checks run, decisions made
- `git_status.txt` — output of `git status --short --untracked-files=all`
- `worktree_info.txt` — output of `git worktree list` and branch info
- `artifact_manifest.json` — machine-readable contract (see Artifact Contract section)

**Optional files:**
- `pr_info.json` — PR metadata (written by `kanban_pr_handoff.py`)
- `decision.md` — human decision record (written by `kanban_accept_cleanup.py`)
- `guard_report.txt` — output of the worker guard
- `test_output.txt` — raw test runner output
- `diff_stat.txt` — `git diff --stat` output
- `review_notes.md` — human review notes

Initialize the manifest:
```bash
python3 scripts/kanban_artifact_manifest.py init \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --status waiting_for_human_review \
  --recommendation accept \
  --requires-pr true \
  --output /home/ubuntu/.hermes/task-artifacts/BJ-XXXX/artifact_manifest.json \
  --overwrite
```

### 5. Blocked / `waiting_for_human_review`

After writing all artifacts, workers set the task status to:
```
blocked / waiting_for_human_review
```

This is the **default terminal state** for all tasks. Workers may only set `done` if the task body explicitly permits it and all of these are true:
1. No human review is required
2. All required artifacts exist and are non-empty
3. No forbidden commands were used
4. No unreviewed repo changes remain

Workers **must not** mark their own tasks done unless explicitly allowed in the task body.

### 6. Human Review

Human reviewers perform these steps:

1. **Check task status** on the Kanban board
2. **Check git status and diff** — inspect `git diff --stat` and changed files
3. **Check artifacts** — confirm all required artifacts exist in `<artifact_root>/<task-key>/`
4. **Validate manifest** — run manifest validation:
   ```bash
   python3 scripts/kanban_artifact_manifest.py validate \
     --path /home/ubuntu/.hermes/task-artifacts/BJ-XXXX/artifact_manifest.json
   ```
5. **Run lifecycle audit**:
   ```bash
   python3 scripts/kanban_task_audit.py \
     --project bullet-journal \
     --task-key BJ-XXXX \
     --task-id <task-id> \
     --artifact-dir /home/ubuntu/.hermes/task-artifacts/BJ-XXXX \
     --phase review
   ```
6. **Decide accept/revise/reject**

### 7. PR Handoff Path (Repo Diff Exists)

If the task produced repo changes (code, docs, config, etc.):

**Step A — Worker runs PR handoff helper:**
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

This:
- Stages and commits all changes
- Pushes the task branch to origin
- Creates a GitHub PR (via `gh pr create`)
- Writes `pr_info.json` to the artifact folder
- Updates `artifact_manifest.json` with `pr_url` and `status: waiting_for_human_review`

**Step B — Human reviews and merges the PR:**
- Human reviews the PR on GitHub
- Human approves and merges via GitHub (not via CLI)
- Human records the merge commit SHA

**Step C — Human runs accept cleanup:**
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

This:
- Verifies the merged commit is in main history
- Writes `decision.md` to the artifact folder
- Updates `artifact_manifest.json` with `status: done`
- Removes the worktree
- Deletes the local task branch
- Optionally completes the Hermes Kanban task

### 8. No-PR Accepted Path (No Repo Diff)

If the task produced **no repo changes** (pure analysis, review, policy decision with no code/docs changes):

**Step A — Worker marks blocked / `waiting_for_human_review` with:**
```json
{
  "requires_pr": false,
  "changed_files": [],
  "status": "waiting_for_human_review"
}
```

**Step B — Human reviews artifacts and manifest**

**Step C — Human runs accept cleanup (no-PR variant):**
```bash
python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision accepted \
  --allow-missing-merged-commit \
  --confirm
```

This path applies **only when** `requires_pr: false` and `changed_files: []` — i.e., the task produced no repository changes at all.

This:
- Writes `decision.md` noting no PR was required
- Updates `artifact_manifest.json` with `status: done`
- Removes the worktree
- Deletes the local task branch
- Does **not** verify a merge commit (since no PR was created)

### 9. Reject Cleanup

If the human reviewer rejects the work:

```bash
python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision rejected \
  --confirm
```

This:
- Writes `decision.md` with decision: rejected
- Updates `artifact_manifest.json` with `status: rejected`
- Removes the worktree
- Deletes the local task branch

---

## Standard Commands

### Create task with `kanban_create_safe.py`
```bash
python3 scripts/kanban_create_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --title "Task title" \
  --body-file /tmp/task-body.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

### Create generated task with `kanban_new_task_safe.py`
```bash
python3 scripts/kanban_new_task_safe.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --type implementation \
  --title "Task title" \
  --goal "What this task achieves." \
  --priority 1 \
  --max-runtime 2h
```

### Validate artifact manifest
```bash
python3 scripts/kanban_artifact_manifest.py validate \
  --path /home/ubuntu/.hermes/task-artifacts/BJ-XXXX/artifact_manifest.json
```

### Run lifecycle audit
```bash
python3 scripts/kanban_task_audit.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --artifact-dir /home/ubuntu/.hermes/task-artifacts/BJ-XXXX \
  --phase review
```

### Run workflow regression audit (all-in-one check)
```bash
python3 scripts/kanban_workflow_regression.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --phase review
```

Phases: `review` | `post-handoff` | `post-cleanup`

Checks: main repo status, worktree existence vs phase, artifact dir, required artifact files, manifest validation, manifest consistency, PR metadata, dirty/no-PR mismatch, lifecycle audit, post-cleanup status.

Exit: 0 = pass, 1 = fail, 2 = error. `--json` for JSON output.

### PR handoff
```bash
cd /home/ubuntu/bullet_journal_app/.worktrees/BJ-XXXX

python3 scripts/kanban_pr_handoff.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --commit-message "description" \
  --title "PR title" \
  --body-file /home/ubuntu/.hermes/task-artifacts/BJ-XXXX/completion_report.md \
  --confirm
```

### Accept cleanup with PR
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

### Accept cleanup without PR
```bash
python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision accepted \
  --allow-missing-merged-commit \
  --confirm
```

Applies only when `requires_pr: false` and `changed_files: []`.

### Rejected cleanup
```bash
python3 scripts/kanban_accept_cleanup.py \
  --project bullet-journal \
  --task-key BJ-XXXX \
  --task-id <task-id> \
  --decision rejected \
  --confirm
```

---

## Artifact Contract Summary

### Required artifact files

| File | Purpose | Written by |
|------|---------|-------------|
| `artifact_manifest.json` | Machine-readable contract with schema version and status | Worker (via `kanban_artifact_manifest.py init`) |
| `completion_report.md` | Human-readable summary of work done | Worker |
| `git_status.txt` | `git status --short --untracked-files=all` | Worker |
| `worktree_info.txt` | `git worktree list` + branch info | Worker |

### Optional artifact files

| File | Purpose | Written by |
|------|---------|-------------|
| `pr_info.json` | PR metadata (URL, number, commit) | `kanban_pr_handoff.py` |
| `decision.md` | Human decision record | `kanban_accept_cleanup.py` |
| `guard_report.txt` | Worker guard output | `kanban_worker_guard.py` |
| `test_output.txt` | Raw test runner output | Worker |
| `diff_stat.txt` | `git diff --stat` output | Worker |

### artifact_manifest.json key fields

**`requires_pr`** — boolean
- `true`: task produced repo changes; PR handoff required
- `false`: task produced no repo changes; no-PR path applies

**`changed_files`** — array of strings
- List of files changed in the worktree (relative to worktree root)
- Empty `[]` when `requires_pr: false`

**`status`** — string
- `ready`: task is ready to be picked up
- `running`: task is in progress
- `waiting_for_human_review`: worker completed; awaiting human review
- `accepted`: human accepted (post-merge or no-PR)
- `rejected`: human rejected
- `merged`: changes merged to main branch
- `done`: task fully completed
- `unknown`: status could not be determined

**`recommendation`** — string
- `accept`: worker recommends accepting
- `revise`: worker recommends revision before accept
- `reject`: worker recommends rejecting
- `unknown`: no recommendation made

---

## Review Task Rules

Review/analysis/policy/audit tasks are **forbidden from self-completing** regardless of how they end:

1. **Final state must be `blocked / waiting_for_human_review`** — never `done`
2. **`requires_pr: false` is valid only when the final worktree is clean** — if the worker made any changes, PR handoff is required
3. **Artifacts must still be written** — even if no files changed, `completion_report.md`, `git_status.txt`, `worktree_info.txt`, and `artifact_manifest.json` are required
4. **Human review is always required** — no exceptions for analysis tasks

---

## Human Review Checklist

- [ ] Check task status is `blocked / waiting_for_human_review`
- [ ] Check `git status --short --untracked-files=all` in artifact folder
- [ ] Check `git diff --stat` for changed files
- [ ] Confirm all required artifacts exist and are non-empty
- [ ] Validate `artifact_manifest.json` with `kanban_artifact_manifest.py validate`
- [ ] Run `kanban_task_audit.py --phase review` with task-id
- [ ] Review `completion_report.md` for accuracy and completeness
- [ ] Decide: **accept** / **revise** / **reject**
- [ ] If accept + repo diff exists: PR handoff path
- [ ] If accept + no repo diff: no-PR accept cleanup
- [ ] If reject: rejected cleanup

---

## Known Failure Modes and Fixes

### BJ-0024 self-complete failure

**Failure:** A review/analysis task was marked `done` by the worker instead of `blocked / waiting_for_human_review`.

**Fix (BJ-0024R):** Template guardrails were added to prevent review tasks from including self-approval instructions. Additionally, `kanban_task_audit.py` was enhanced to detect actual Hermes task `status: done` for review-phase tasks, preventing workers from bypassing the blocked-state requirement through artifact manipulation.

**Prevention:** Workers must follow the default-state rule. Analysis/review/policy tasks never self-complete.

### Dirty worktree with no-PR manifest

**Failure:** Worker produced changes (dirty worktree) but set `requires_pr: false` in manifest.

**Fix:** Human reviewer checks `git diff --stat` before accepting. If repo diff exists, PR handoff is mandatory regardless of what the manifest says.

**Prevention:** Human review checklist step "check git diff --stat" is required before accepting.

### Manifest not finalized

**Failure:** Worker blocked with artifacts but `artifact_manifest.json` was never initialized or was left in `running` status.

**Fix:** Worker must run `kanban_artifact_manifest.py init` before blocking. Manifest must show `status: waiting_for_human_review`.

**Prevention:** Manifest validation step in human review checklist.

### Audit false positive on clean human-readable `git_status.txt`

**Failure (BJ-0025R):** `kanban_task_audit.py` falsely flagged a task as having untracked files when the `git_status.txt` artifact was written in human-readable prose style (e.g., "(empty — worktree clean)" or "(empty — no repo diff)"), and those prose strings happened to match the audit's pattern for untracked file markers. The real worktree was clean, but the human-readable artifact text triggered a false positive.

**Fix:** Audit now reads `git_status.txt` as raw text and searches for actual untracked filename patterns (lines starting with `?? `), not human-readable annotations. Clean artifacts with no untracked files pass correctly.

**Prevention:** Use `kanban_artifact_manifest.py validate` as the primary check; use audit as secondary verification.

### No-PR accepted cleanup wording bug

**Failure (BJ-0026):** When a task required no PR (`requires_pr: false`), the accept cleanup helper would output messages saying "PR has been merged to main" or "PR merged to main at unknown commit", which were misleading for a task that never had a PR.

**Fix:** Cleanup helper now detects no-PR accept path explicitly and uses wording that correctly reflects no PR was required, rather than implying a PR was merged.

**Prevention:** Test both cleanup variants in smoke tests.

---

## Current Limits / Non-Goals

- **CLI-first, not dashboard-first.** The primary interface is the terminal and `hermes kanban` CLI. Dashboard tooling is minimal.
- **Worker is constrained by prompts + audit, not guaranteed behavior.** Workers follow governance rules because the prompts encode them and the audit verifies them. This is not a hard security guarantee — a sophisticated bypass could still occur. Human review is the real safeguard.
- **Multi-project use is possible but must be validated per project.** The project registry (`config/projects.yaml`) supports multiple projects. Each project must verify its workflow tooling works correctly before full adoption.
- **This document does not describe Bullet Journal app features.** The app's functionality (journal entries, time tracking, etc.) is documented elsewhere. This document covers only the Hermes/Kanban workflow tooling.

---

## Related Documents

| Document | Purpose |
|----------|---------|
| `docs/hermes_kanban_governance.md` | Universal worker rules, forbidden commands, breach response |
| `docs/hermes_workflow_regression_checklist.md` | Post-task safety verification checklist |
| `docs/hermes_artifact_contract.md` | Artifact folder schema and manifest validation |
| `docs/hermes_multi_project_workflow.md` | Project registry, generic submitter, accept/pr handoff helpers |
| `docs/hermes_safe_task_submitter.md` | Why verified worktree is used instead of `--workspace worktree` |
| `docs/hermes_quickstart.md` | Concise quickstart guide |
| `docs/incidents/BJ-0004-governance-breach.md` | The BJ-0004 incident that drove governance hardening |
| `scripts/kanban_create_safe.py` | Generic safe task creation |
| `scripts/kanban_new_task_safe.py` | One-command template-based task creation |
| `scripts/kanban_pr_handoff.py` | PR creation from completed worktree |
| `scripts/kanban_accept_cleanup.py` | Post-merge accept / reject cleanup |
| `scripts/kanban_artifact_manifest.py` | Manifest init and validation |
| `scripts/kanban_task_audit.py` | Lifecycle audit for human review |
| `scripts/kanban_worker_guard.py` | Worktree preflight verification for workers |
| `config/projects.yaml` | Project registry (repo paths, artifact roots, task prefixes) |
