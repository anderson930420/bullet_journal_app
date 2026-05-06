# Hermes Task Templates

## Purpose

`scripts/bj_task_template.py` generates consistent, well-structured task body markdown for the bullet-journal-app Hermes Kanban workflow. It eliminates manual authoring of repetitive governance sections and lets task submitters focus on goal, background, and scope.

This is used together with `scripts/bj_kanban_create.py` — the template generates the body file, and the submitter creates the Hermes task with a verified worktree.

**Note:** `bj_task_template.py` does NOT create Hermes tasks, worktrees, or invoke `bj_kanban_create.py`. It only generates a markdown body file.

## Supported task types

| Type | Purpose |
|------|---------|
| `analysis` | Read-only investigation producing an artifact/report |
| `implementation` | New code, scripts, tooling, or infrastructure |
| `docs` | Documentation-only changes |
| `bugfix` | Defect/bug corrections |
| `review` | Code review without modifying source |

## Quick start

### 1. Generate a task body (dry-run)

```bash
python3 scripts/bj_task_template.py \
  --type docs \
  --task-key BJ-0008 \
  --title "Add reusable task body templates" \
  --goal "Add reusable Hermes task body templates for future repo tasks." \
  --dry-run
```

### 2. Write the generated body to a file

```bash
python3 scripts/bj_task_template.py \
  --type implementation \
  --task-key BJ-0008 \
  --title "Add reusable task body templates" \
  --goal "Add reusable Hermes task body templates for future repo tasks." \
  --output /tmp/BJ-0008.generated.md
```

### 3. Pass the file to the safe submitter

```bash
python3 scripts/bj_kanban_create.py \
  --task-key BJ-0008 \
  --title "Add reusable task body templates" \
  --body-file /tmp/BJ-0008.generated.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

## Validation

The script validates:
- `--type` is one of the supported types
- `--task-key` is provided and contains only safe characters `[A-Za-z0-9._-]+`
- `--title` is provided and non-empty
- `--goal` is provided and non-empty
- `--output` is required when not using `--dry-run`

## Output

On success (non-dry-run), the script prints the output path:

```
Generated: /tmp/BJ-0008.generated.md
```

On validation failure, it exits with a non-zero status and a descriptive error message.

## Generated body structure

Every generated body includes:

- Governance header (from `bj_kanban_create.py`)
- Project / Repo / Task key / Task type / Title / Goal
- Required workspace behavior
- Allowed changes
- Forbidden actions
- Required artifacts
- Required checks
- Final Kanban comment template
- Final blocked reason

Type-specific skeletons add guidance tailored to each category (e.g., implementation templates include "inspect existing code first", bugfix templates include "reproduce or explain the bug").

## Template files

Individual template skeletons are also available at:

```
templates/hermes_tasks/analysis.md
templates/hermes_tasks/implementation.md
templates/hermes_tasks/docs.md
templates/hermes_tasks/bugfix.md
templates/hermes_tasks/review.md
```

These can be used as quick reference when authoring a task body manually.

## Relationship to bj_kanban_create.py

```
bj_task_template.py          → generates /tmp/<key>.generated.md
         ↓
bj_kanban_create.py          → reads the file, creates Hermes task + worktree
         ↓
Hermes dispatcher            → spawns worker in the worktree
```

`bj_task_template.py` is a pure generator — it has no side effects on Hermes, git, or the filesystem beyond optionally writing its output file.
