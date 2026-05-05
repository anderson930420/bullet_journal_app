# Hermes Kanban Task Template

Use this template when creating new tasks for the `bullet-journal` board.

---

## Task Metadata

```
Title:      <short descriptive title>
Board:      bullet-journal
Assignee:   <profile>
Workspace:  worktree | scratch | dir:<path>
Priority:   <1-5, 1=highest>
Max runtime: <e.g. 2h>
Skills:     kanban-worker
```

---

## Task Body Template

```markdown
# Task: <TASK-ID> <Title>

## Project

bullet-journal-app

## Repo

`/home/ubuntu/bullet_journal_app`

## Goal

<One-paragraph description of what this task must achieve.>

## Workspace Behavior

* Use `workspace=<worktree|scratch|dir:<path>>`.
* Do not edit `/home/ubuntu/bullet_journal_app` directly unless workspace=dir:<path> is explicitly authorized.
* Report actual workspace path.
* Do not push.
* Do not merge.
* Do not self-approve.
* Do not mark done <if human review required>.

## Scope

### Allowed

* <list of permitted actions>

### Forbidden

* <list of prohibited actions: git push, git rm, git commit, etc.>
* Do not modify source files unless explicitly allowed.
* Do not modify `.gitignore` unless task requires it.

## Required Artifacts

* `~/.hermes/task-artifacts/<TASK-ID>/completion_report.md`
* <other required files>

## Required Checks

```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git status --short --untracked-files=all
git worktree list
```

## Analysis Questions (for policy/audit tasks)

1. <question>
2. <question>

## Final State

<Choose one:>

**If human review required:**
```
blocked / waiting_for_human_review: <brief reason>
```

**If implementation is complete and human review NOT required:**
```
done
```

## Failure Behavior

If workspace cannot be verified as isolated worktree (for worktree tasks), block immediately:
```
waiting_for_human_review: Could not create or verify isolated worktree workspace.
```
```

---

## Classification Guide

| Task Type | Workspace | Artifact Required | Final State | git push |
|-----------|-----------|-------------------|-------------|----------|
| Analysis / Read-only | worktree | Yes | blocked | No |
| Policy decision | worktree | Yes | blocked | No |
| Audit / Investigation | worktree | Yes | blocked | No |
| Cleanup / Hygiene | worktree | Yes | blocked | No |
| Feature / Implementation | worktree | Yes | blocked | No |
| Docs only | worktree | Yes | blocked | No |

**Key principle:** Unless the task body explicitly says "mark done when complete", the default final state for ALL tasks is `blocked / waiting_for_human_review`.

---

## Artifact Completeness Checklist

Before marking done or blocked, verify:
- [ ] Artifact folder exists: `~/.hermes/task-artifacts/<TASK-ID>/`
- [ ] All required files are present
- [ ] No file is empty (all must have content)
- [ ] `git status --short --untracked-files=all` is in git_status.txt
- [ ] `git worktree list` is in worktree_info.txt
- [ ] Final state matches task requirements

---

## Common Mistakes to Avoid

1. **Marking done without artifacts** — always verify artifact folder first
2. **Using `dir:` instead of `worktree`** — dir: allows direct main edits; worktree is isolated
3. **Self-approving** — workers never approve their own changes
4. **Forgetting to block** — if the task says human review is required, block instead of done
5. **Pushing without approval** — push only after human explicitly approves the diff
