# Safe Hermes Kanban Task Submitter for bullet_journal_app

## Why `--workspace worktree` Is Not Trusted

The `--workspace worktree` auto-binding in Hermes Kanban is not deterministic for `bullet_journal_app` because:

1. **Worktree auto-creation is unreliable.** When `--workspace worktree` is used, Hermes may create a worktree at a path it chooses, not at a predictable location under `.worktrees/<task-key>`. This breaks downstream tasks that depend on knowing the exact worktree path.

2. **Branch naming is inconsistent.** The auto-created worktree branch name may not follow the `worktree/<task-key>` convention, making it harder to audit which worktrees belong to which tasks.

3. **Race conditions in multi-agent runs.** When multiple workers run concurrently with `--workspace worktree`, they may inadvertently share or clobber each other's worktrees because the workspace binding is resolved at dispatch time, not at task creation time.

4. **No pre-creation verification.** The auto-binding does not verify that `git status` is clean, that the worktree was created on `main`, or that the artifact folder exists before the task begins.

5. **BJ-0004 lessons learned.** The BJ-0004 incident involved a read-only policy task that inadvertently modified local main, removed `bullet_journal.db`, created a seed script, and committed locally — all because the workspace binding did not prevent operations on the main repo. A verified worktree approach with explicit `dir:<path>` prevents this class of failure.

## The Approved Workaround: Manual Verified Worktree + `dir:<path>`

The safe approach for `bullet_journal_app` is:

1. **Create a real git worktree manually** at a predictable path: `.worktrees/<task-key>`
2. **Branch from `main`** with branch name `worktree/<task-key>`
3. **Verify the worktree** with `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git worktree list`, and `git status --short --untracked-files=all` before any task begins
4. **Create the artifact folder** at `~/.hermes/task-artifacts/<task-key>/`
5. **Pass `--workspace dir:<verified-worktree-path>`** when creating the Hermes Kanban task
6. **Never operate from the main repo** — all work happens inside the verified worktree

## Using `scripts/bj_kanban_create.py`

The `scripts/bj_kanban_create.py` script automates all of the above.

### Prerequisites

- Python 3 standard library only (no pip install needed)
- Must be run from or against `/home/ubuntu/bullet_journal_app`
- Must be on `main` branch (unless `--allow-non-main` is passed)
- Repo must be clean (no uncommitted changes)

### CLI Reference

```bash
python3 scripts/bj_kanban_create.py \
  --task-key BJ-0004R \
  --title "Redo bullet_journal.db repository policy analysis" \
  --body-file /tmp/bj-0004r.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

**Required arguments:**

| Argument | Description |
|---|---|
| `--task-key` | Task key (e.g. `BJ-0004R`). Pattern: `[A-Za-z0-9._-]+` |
| `--title` | Task title (quoted string) |
| `--body-file` | Path to markdown file with task body |
| `--assignee` | Hermes profile name to assign the task to |

**Optional arguments:**

| Argument | Description |
|---|---|
| `--priority N` | Priority integer (higher = picked sooner) |
| `--max-runtime` | Max runtime (e.g. `2h`, `30m`) |
| `--allow-non-main` | Allow creating from a non-main branch |
| `--reuse-existing-worktree` | Reuse an existing worktree instead of failing |
| `--dry-run` | Print commands and body but do not execute |
| `--json` | Pass `--json` to `hermes kanban create` |

### Example for BJ-0004R

```bash
# Create the task body
cat > /tmp/bj-0004r.md <<'EOF'
# Task: BJ-0004R Redo bullet_journal.db repository policy analysis

## Context
BJ-0004D implemented a safe task submitter that should be used going forward.
This task is to redo the bullet_journal.db policy analysis with proper tooling.

## Goal
Redo the analysis using the new safe submitter workflow.
EOF

# Create the task
python3 scripts/bj_kanban_create.py \
  --task-key BJ-0004R \
  --title "Redo bullet_journal.db repository policy analysis" \
  --body-file /tmp/bj-0004r.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

**Output:**
```
Using repo root: /home/ubuntu/bullet_journal_app

Checking main repo is clean...

Checking current branch...

Artifact folder: /home/ubuntu/.hermes/task-artifacts/BJ-0004R/

=== DRY RUN — no changes made ===
Task key:   BJ-0004R
Title:      Redo bullet_journal.db repository policy analysis
Assignee:   bullet-eng
Worktree:   /home/ubuntu/bullet_journal_app/.worktrees/BJ-0004R (new)
Branch:     worktree/BJ-0004R
Artifact:   /home/ubuntu/.hermes/task-artifacts/BJ-0004R/

Would run:
  git worktree add -b worktree/BJ-0004R /home/ubuntu/bullet_journal_app/.worktrees/BJ-0004R main (from /home/ubuntu/bullet_journal_app)

hermes kanban create command:
  hermes kanban create ... --workspace dir:/home/ubuntu/bullet_journal_app/.worktrees/BJ-0004R
```

### Dry Run

Always dry-run first to verify the script behavior before creating real worktrees:

```bash
python3 scripts/bj_kanban_create.py \
  --task-key BJ-DRYRUN \
  --title "Dry run test" \
  --body-file /tmp/bj-dryrun.md \
  --assignee bullet-eng \
  --dry-run
```

## Cleanup Procedure

After a PR merges or a task is discarded:

### 1. Remove the worktree

```bash
cd /home/ubuntu/bullet_journal_app
git worktree remove .worktrees/<task-key>
git branch -d worktree/<task-key>
```

### 2. Archive or clean the artifact folder

```bash
# Archive (recommended if task had valuable artifacts)
mv ~/.hermes/task-artifacts/<task-key> ~/.hermes/task-artifacts/<task-key>-archived-$(date +%Y%m%d)

# Or delete if truly discarded
rm -rf ~/.hermes/task-artifacts/<task-key>
```

### 3. Verify cleanup

```bash
git worktree list
git branch -a | grep worktree/<task-key>
ls ~/.hermes/task-artifacts/<task-key> 2>/dev/null && echo "artifact folder still exists"
```

## Safety Limitations

`bj_kanban_create.py` provides strong guarantees but is not a complete security solution:

| Guarantee | Limitation |
|---|---|
| Worktree created on `main` branch | The worker must still respect the governance header |
| `dir:<path>` workspace prevents main-repo edits | A malicious worker could `git -C /home/ubuntu/bullet_journal_app push --force` directly |
| Artifact folder created automatically | The worker must actually write artifacts |
| Dry-run mode to preview changes | Real runs still execute git worktree add |
| Forbidden commands list | Only covers direct subprocess calls; a sophisticated bypass could use git's `-C` option or environment manipulation |
| Clean repo check at start | A worker that checks clean, then pulls bad commits before working, could still cause harm |

**Human review is required** for all changes that modify the repository, including worktree creation scripts. No task created via this workflow should be marked `done` without human inspection of the artifacts and git status.

## Related Documents

- `docs/hermes_kanban_governance.md` — General Kanban governance for bullet_journal_app
- `docs/incidents/BJ-0004-governance-breach.md` — The BJ-0004 incident record
- `scripts/bj_kanban_create.py` — The script itself (run with `--help` for usage)
