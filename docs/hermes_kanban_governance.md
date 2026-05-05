# Hermes Kanban Governance Policy

## Purpose

This document defines the rules that all Hermes Kanban workers must follow when operating on this repository. These rules exist to prevent unauthorized modifications, protect sensitive data, and ensure human review before any change reaches the `main` branch.

---

## Universal Worker Rules

### Workspace Isolation

- **All tasks** that modify repository files must use `workspace=worktree`.
- Workers must **never** edit `/home/ubuntu/bullet_journal_app` directly (the main workspace).
- Workers must **verify** the workspace is a real git worktree via `git worktree list`.
- If a worktree cannot be created or verified, the task must **block immediately**.

### Forbidden Commands (Always)

Without explicit human approval, workers must **never** run:
- `git push` to any remote
- `git merge` into `main`
- Direct commit to `main` branch
- `git reset --hard` on `main`
- `git clean -fd` on `main`
- History rewrite: `git filter-repo`, BFG, `git filter-branch`
- Force push: `git push --force`
- Self-approval of any kind

### Done-State Rule

A worker may mark a task `done` **only if** all of the following are true:
1. The task body does **not** require human review
2. **All** required artifacts exist and are non-empty
3. Final `git status --short --untracked-files=all` is recorded
4. No forbidden command was used
5. No unreviewed repo changes remain
6. The task body **explicitly** allows `done`

**Otherwise, the correct terminal state is:**
```
blocked / waiting_for_human_review
```

### Artifact Completeness Rule

- No task (done or blocked) may have an empty artifact folder.
- Workers must write required artifacts **before** marking done or blocking.
- The artifact folder path is always `~/.hermes/task-artifacts/<TASK_ID>/`.

---

## Analysis / Read-Only Task Rules

Tasks tagged: analysis-only, read-only, policy decision, audit, investigation, review.

### Forbidden (Analysis Tasks)

- `git rm` (any form)
- `git commit`
- `git push`
- `git reset --hard` or `--soft`
- `git clean`
- `git filter-repo`, BFG, `git filter-branch`
- Modifying source files
- Modifying database files
- History rewrite of any kind

### Allowed (Analysis Tasks)

- Read-only Git inspection (`git log`, `git ls-files`, `git status`)
- Read-only SQLite inspection (schema, row counts, redacted samples)
- Writing artifacts to `~/.hermes/task-artifacts/<TASK_ID>/`
- Adding Kanban comments
- Blocking with `waiting_for_human_review`

### Required Final State

`blocked / waiting_for_human_review`

---

## Implementation Task Rules

Tasks that modify source code, add files, or change behavior.

### Permitted Only If

- Task body **explicitly** allows implementation
- Workspace is a **verified** worktree
- Changes stay in the **worktree branch** until human approval
- All required artifacts are written
- Final state is `blocked / waiting_for_human_review` **unless** task explicitly authorizes `done`

### Forbidden Without Human Approval

- Push to GitHub
- Merge into `main`
- Direct commit to `main`
- Force push
- History rewrite

---

## Database / Sensitive Artifact Rules

- `.db`, `.sqlite`, `.sqlite3` files are **sensitive by default**.
- Do **not** remove tracked database files unless the task explicitly allows implementation.
- Do **not** dump private DB content into artifacts.
- Use **schema + row counts only**; no raw note content, names, emails, or tokens.
- History rewrite for a tracked DB requires **separate explicit human approval**.

---

## Profile Configuration

Worker profiles are defined in:
- `~/.hermes/profiles/<profile_name>/`
- Profile instructions may include custom system prompts and tool restrictions

### bullet-eng Profile

- **Location**: `~/.hermes/profiles/bullet-eng/`
- **Recommendation**: Add explicit governance rules to the profile's system instructions
- **Hardening**: Disable `git push` at profile level for analysis tasks; require human gate for implementation tasks

---

## Governance Breach Response

If a worker violates these rules:
1. Human immediately reverts any unauthorized changes
2. Task is archived as a governance breach
3. A hardening task (like BJ-0004A) is created to prevent recurrence
4. The `backup/` branch pattern (`backup/bj<task>-incident-<description>`) preserves the bad state for audit

---

## Revision History

| Date | Version | Change |
|------|---------|--------|
| 2026-05-06 | 1.0 | Initial governance policy after BJ-0004 breach |
