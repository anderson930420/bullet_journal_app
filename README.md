# Bullet Journal App

A PySide6 desktop application for managing bullet journal entries and collections.

## Requirements

- Python 3
- PySide6

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd bullet_journal_app

# Optional: create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install PySide6

# If requirements.txt is populated in your checkout, you can also use:
# pip install -r requirements.txt
```

## Run

```bash
python3 main.py
```

## Local Database

The app stores all data in a local SQLite database: `bullet_journal.db`.

- `bullet_journal.db` is **local runtime state** — it is intentionally ignored by Git.
- It is created automatically on the first run.
- Do not commit local `.db`, `.sqlite`, or `.sqlite3` files.

## Developer Notes

### Hermes Kanban Workflow

All Hermes tasks for this repo should be created through the safe submitter:

```bash
python3 scripts/bj_kanban_create.py \
  --task-key BJ-XXXX \
  --title "Short task title" \
  --body-file /tmp/task.md \
  --assignee bullet-eng \
  --priority 1 \
  --max-runtime 2h
```

Do not use `hermes kanban create --workspace worktree` directly for this repo. Use the script so the task is bound to a verified worktree under `.worktrees/`.

Changes stay in the worktree branch until human review approves merging to `main`.
