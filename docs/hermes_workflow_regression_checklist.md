# Hermes Workflow Regression Checklist

**Question:** How do we know a task really completed safely?

Use this checklist after any Hermes/Symphony-style workflow task to verify lifecycle safety and artifact completeness.

---

## Main Repo State

- [ ] Main repo is clean before task creation
  ```bash
  git -C /home/ubuntu/bullet_journal_app status --short
  ```
- [ ] Main branch is current
  ```bash
  git -C /home/ubuntu/bullet_journal_app fetch origin
  git -C /home/ubuntu/bullet_journal_app status --short --branch
  git -C /home/ubuntu/bullet_journal_app log --oneline HEAD..origin/main
  # empty output = main is current (no unpushed worker commits)
  # non-empty = main has diverged — investigate before proceeding
  ```
- [ ] No direct main push occurred
  ```bash
  git -C /home/ubuntu/bullet_journal_app log --oneline origin/main..HEAD
  # should be empty for no-direct-push verification
  ```

---

## Worktree Lifecycle

- [ ] Verified worktree exists while task is active or in review
  ```bash
  git worktree list | grep BJ-0021
  ```
- [ ] Worker operated only inside the assigned worktree
  ```bash
  pwd
  # must be: /home/ubuntu/bullet_journal_app/.worktrees/BJ-0021
  git rev-parse --show-toplevel
  # must show the worktree path, not the main repo
  ```
- [ ] Worktree is removed after accept cleanup
  ```bash
  git worktree list | grep -v BJ-0021
  # remaining worktrees should be expected ones only
  ```
- [ ] No unexpected leftover worktrees remain
  ```bash
  git worktree list
  # audit each entry — only planned worktrees should be present
  ```

---

## Hermes Task State

- [ ] Task was created by safe submitter (e.g., `scripts/kanban_create_safe.py`)
  ```bash
  hermes kanban show <task_id>
  # check created_by field
  ```
- [ ] Task used `workspace dir:<path>`
  ```bash
  hermes kanban show <task_id>
  # check workspace_kind and workspace_path fields
  ```
- [ ] Worker did not use `hermes kanban create --workspace worktree`
  ```bash
  git log --oneline --all --source --grep="hermes kanban create"
  # no worker-created tasks should appear via forbidden pattern
  ```
- [ ] Task ends in `blocked / waiting_for_human_review` before human review
  ```bash
  hermes kanban show <task_id>
  # status must be blocked with reason: waiting_for_human_review
  ```
- [ ] Task is marked done only after human accept cleanup
  ```bash
  hermes kanban show <task_id>
  # outcome must be set by human action, not worker auto-done
  ```

---

## Artifact Completeness

All artifacts should exist under `/home/ubuntu/.hermes/task-artifacts/<task-key>/`.

- [ ] `completion_report.md` exists
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/completion_report.md
  ```
- [ ] `git_status.txt` exists
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/git_status.txt
  ```
- [ ] `worktree_info.txt` exists
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/worktree_info.txt
  ```
- [ ] `artifact_manifest.json` exists
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/artifact_manifest.json
  ```
- [ ] Artifact manifest validation passes
  ```bash
  python3 /home/ubuntu/bullet_journal_app/scripts/kanban_artifact_manifest.py validate \
    --path /home/ubuntu/.hermes/task-artifacts/<task-key>/artifact_manifest.json
  ```
- [ ] `decision.md` exists after accept cleanup
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/decision.md
  # required only after human accept cleanup
  ```
- [ ] `pr_info.json` exists for PR-backed tasks
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/pr_info.json
  # required only for tasks with a PR handoff
  ```
- [ ] Analysis-only or review-only tasks may omit PR artifacts only when no repo diff exists
  ```bash
  git diff --stat
  # if no source files changed and task is analysis/review, PR artifacts may be skipped
  ```

---

## PR and Merge Handoff

> **Important:** Even docs-only tasks that produce a repo diff require PR handoff and GitHub merge. The only tasks that may skip PR artifacts are analysis-only or review-only tasks with no repo diff.

- [ ] PR-backed tasks have a PR URL
  ```bash
  cat /home/ubuntu/.hermes/task-artifacts/<task-key>/pr_info.json | grep url
  ```
- [ ] PR was created by human handoff helper (not worker)
  ```bash
  gh pr view <pr_number> --json author
  # author must be human, not bot/worker
  ```
- [ ] GitHub merge was done by human
  ```bash
  gh pr view <pr_number> --json mergedAt,mergedBy
  # mergedBy must be human
  ```
- [ ] Merged commit is present on `main`
  ```bash
  git -C /home/ubuntu/bullet_journal_app fetch origin main
  git -C /home/ubuntu/bullet_journal_app log --oneline origin/main | head -5
  # verify merged commit SHA appears in main history
  ```
- [ ] Worker did not push, merge, or self-approve
  ```bash
  git -C /home/ubuntu/bullet_journal_app log --oneline -10 --author="worker"
  # worker author entries in main history indicate violation
  ```

---

## Forbidden-File Checks

- [ ] No `bullet_journal.db` changes
  ```bash
  git diff --stat | grep bullet_journal.db
  # must be empty
  ```
- [ ] No app source changes unless explicitly allowed
  ```bash
  git diff --stat -- \
    '*.py' '*.qml' '*.ui' ':!tests/**' ':!scripts/**'
  # only allowed if task body explicitly permits source changes
  ```
- [ ] No database code changes unless explicitly allowed
  ```bash
  git diff --stat | grep -E 'schema|migration|db'
  # must be empty unless task body explicitly allows
  ```
- [ ] No Hermes global config changes
  ```bash
  git diff --stat | grep -E '\.hermes|config\.yaml|settings\.json'
  # global Hermes config must not be modified
  ```
- [ ] No unrelated files changed
  ```bash
  git diff --name-only
  # every file should match task scope
  ```

---

## Unsafe Command Checks

- [ ] No `git push` by worker
  ```bash
  git reflog | grep push
  # no worker-initiated push to origin should appear
  ```
- [ ] No `git merge` by worker
  ```bash
  git reflog | grep merge
  # no worker-initiated merge should appear
  ```
- [ ] No `git reset --hard` by worker
  ```bash
  git reflog | grep 'reset --hard'
  # no worker reset should appear
  ```
- [ ] No `git clean -fd` by worker
  ```bash
  git reflog | grep 'clean'
  # no worker clean should appear
  ```
- [ ] No direct main branch edits
  ```bash
  git diff origin/main --stat
  # main branch should only change via PR merge
  ```
- [ ] No task self-completion unless explicitly allowed
  ```bash
  hermes kanban show <task_id> | grep outcome
  # outcome must be set by human or explicit automation, not worker self-done
  ```

---

## Final Acceptance Checklist

- [ ] Human reviewed diff
  ```bash
  git diff --stat
  # human must visually confirm every changed file
  ```
- [ ] Human reviewed artifacts
  ```bash
  ls -la /home/ubuntu/.hermes/task-artifacts/<task-key>/
  # human must confirm all required artifacts are present and valid
  ```
- [ ] Human merged PR if applicable
  ```bash
  gh pr view <pr_number> --json merged
  # must be true, set by human
  ```
- [ ] Human ran accept cleanup
  ```bash
  python3 /home/ubuntu/bullet_journal_app/scripts/kanban_accept_cleanup.py --task-id <task-key> --confirm
  # must be human-initiated with --confirm
  ```
- [ ] Task artifacts contain final decision
  ```bash
  cat /home/ubuntu/.hermes/task-artifacts/<task-key>/decision.md
  # must have human decision: accept / revise / reject
  ```
- [ ] Hermes task is done after cleanup
  ```bash
  hermes kanban show <task_id>
  # status must be done, outcome set
  ```
- [ ] Main repo is clean after cleanup
  ```bash
  git -C /home/ubuntu/bullet_journal_app status --short
  # must be clean — no uncommitted changes, no untracked files
  ```

---

## Quick Verification Commands

Run these for a fast sanity check:

```bash
# 1. Worktree present
git worktree list | grep BJ-0021

# 2. Main repo clean
git -C /home/ubuntu/bullet_journal_app status --short

# 3. Artifacts exist
ls /home/ubuntu/.hermes/task-artifacts/<task-key>/

# 4. Manifest valid
python3 /home/ubuntu/bullet_journal_app/scripts/kanban_artifact_manifest.py validate \
  --path /home/ubuntu/.hermes/task-artifacts/<task-key>/artifact_manifest.json

# 5. No forbidden pushes
git -C /home/ubuntu/bullet_journal_app log --oneline -5 origin/main
```

---

## Using This Checklist

1. **Before task starts:** Record main repo baseline (`git status`, `git log --oneline -3`)
2. **During task:** Keep worktree path as only write context
3. **After task completion:** Fill all checkboxes before requesting human review
4. **After human accept:** Verify cleanup removed worktree, main repo is clean
5. **Final state:** Task is `done` only after all final-acceptance items pass

---

*Last updated: 2026-05-08*
*BJ-0021 regression checklist — documentation-only hardening*