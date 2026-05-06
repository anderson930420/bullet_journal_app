#!/usr/bin/env python3
"""
bj_task_template.py — Reusable Hermes Kanban Task Body Generator

Generates consistent, well-structured task bodies for the bullet-journal-app
Hermes Kanban workflow without requiring manual markdown authoring.

Supported types: analysis, implementation, docs, bugfix, review

Usage:
    python3 scripts/bj_task_template.py \\
      --type implementation \\
      --task-key BJ-0008 \\
      --title "Add reusable task body templates" \\
      --goal "Add reusable Hermes task body templates for future repo tasks." \\
      --output /tmp/BJ-0008.generated.md

    python3 scripts/bj_task_template.py --type docs --task-key BJ-0008 \\
      --title "Update docs" --goal "Update documentation." --dry-run

NOTE: This script only generates a markdown body file. It does NOT create
Hermes tasks, worktrees, or invoke bj_kanban_create.py.
"""

import argparse
import sys
import textwrap
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------
# Template type definitions
# ------------------------------------------------------------------

TEMPLATE_TYPES = {"analysis", "implementation", "docs", "bugfix", "review"}

REPO_ROOT = "/home/ubuntu/bullet_journal_app"

GOVERNANCE_HEADER = """---
## Governance Requirements (MANDATORY)

This task was created via `scripts/bj_task_template.py` and the safe submitter
`scripts/bj_kanban_create.py`.

**You MUST follow these rules:**
- Work ONLY in the verified worktree: `dir:{worktree_path}`
- Do NOT operate from the main repo at `{repo_root}`
- Do NOT run `git push`
- Do NOT run `git merge`
- Do NOT run `git reset --hard`
- Do NOT run `git clean -fd`
- Do NOT self-approve your own changes
- Do NOT mark done unless the task body explicitly allows it
- Final state MUST be `blocked / waiting_for_human_review` unless the task body explicitly allows `done`
- Write all required artifacts to `~/.hermes/task-artifacts/<task-key>/`
- Record `git status --short --untracked-files=all` in artifacts

---
"""


def build_analysis_skeleton(task_key: str, title: str, goal: str) -> str:
    return f"""# {task_key} — {title}

## Project

bullet-journal-app Hermes workflow tooling.

## Repo

```
{REPO_ROOT}
```

## Task type

Analysis / read-only.

## Task key

{task_key}

## Title

{title}

## Goal

{goal}

## Background

<Context and motivation for this analysis.>

## Required workspace behavior

The worker must operate only inside the verified worktree assigned to this task.

Before making changes, verify:

```bash
pwd
git rev-parse --show-toplevel
git status --short --untracked-files=all
git branch --show-current
```

## Allowed changes

This is an analysis task. Source code changes are NOT allowed unless explicitly listed here:
- <list any allowed file changes, or "none">
- <...>

## Forbidden actions

Do not:
- modify app source code
- modify database code
- modify `bullet_journal.db`
- modify `.gitignore`
- modify Hermes global config
- create a real Hermes task from the new template script during tests
- push directly to `main`
- merge any branch
- self-approve the task

## Analysis scope

<Specific questions this analysis must answer.>

## Required artifacts

- `~/.hermes/task-artifacts/{task_key}/` folder
- `analysis_report.md` with findings
- `git_status.txt` with `git status --short --untracked-files=all`
- `worktree_info.txt` with `git worktree list` output

## Required checks

```bash
python3 -m py_compile <target_script.py>
<any applicable linting or type checks>
```

## Final Kanban comment

```
{task_key} completed and waiting for human review.

Analysis summary:
- ...

Artifacts:
- ...

PR required:
- no

Recommendation:
- accept / revise
```

## Final blocked reason

```
waiting_for_human_review
```
"""


def build_implementation_skeleton(task_key: str, title: str, goal: str) -> str:
    return f"""# {task_key} — {title}

## Project

bullet-journal-app Hermes workflow tooling.

## Repo

```
{REPO_ROOT}
```

## Task type

Implementation / tooling.

## Task key

{task_key}

## Title

{title}

## Goal

{goal}

## Background

<Context and motivation for this implementation.>

## Required workspace behavior

The worker must operate only inside the verified worktree assigned to this task.

Before making changes, verify:

```bash
pwd
git rev-parse --show-toplevel
git status --short --untracked-files=all
git branch --show-current
```

## Allowed changes

- <list allowed files/folders>
- <...>

## Forbidden actions

Do not:
- modify app source code unrelated to task goals
- modify database code
- modify `bullet_journal.db`
- modify `.gitignore` unless strictly necessary
- modify Hermes global config
- create a real Hermes task from the new template script during tests
- push directly to `main`
- merge any branch
- self-approve the task

## Implementation guidance

1. **Inspect existing code first** — understand the current patterns before making changes.
2. **Make minimal scoped changes** — avoid scope creep; changes should be directly tied to the goal.
3. **Run relevant tests** — verify behavior before marking complete.
4. **Report changed files** — list all modified and new files in the final artifact.

## Required artifacts

- `~/.hermes/task-artifacts/{task_key}/` folder
- `git_status.txt` with `git status --short --untracked-files=all`
- `worktree_info.txt` with `git worktree list` output
- `completion_report.md` with changed files, checks run, and summary

## Required checks

```bash
python3 -m py_compile <target_script.py>
<any applicable linting, type checks, or tests>
```

## Final Kanban comment

```
{task_key} completed and waiting for human review.

Changed files:
- ...

Checks:
- ...

PR required:
- yes/no

Recommendation:
- accept / revise
```

## Final blocked reason

```
waiting_for_human_review
```
"""


def build_docs_skeleton(task_key: str, title: str, goal: str) -> str:
    return f"""# {task_key} — {title}

## Project

bullet-journal-app Hermes workflow tooling.

## Repo

```
{REPO_ROOT}
```

## Task type

Documentation.

## Task key

{task_key}

## Title

{title}

## Goal

{goal}

## Background

<Context and motivation for this documentation work.>

## Required workspace behavior

The worker must operate only inside the verified worktree assigned to this task.

Before making changes, verify:

```bash
pwd
git rev-parse --show-toplevel
git status --short --untracked-files=all
git branch --show-current
```

## Allowed changes

- docs/*.md
- README.md (short pointers only)
- <any other allowed doc files>

## Forbidden actions

Do not:
- modify app source code
- modify database code
- modify `bullet_journal.db`
- modify `.gitignore`
- modify Hermes global config
- create a real Hermes task from the new template script during tests
- push directly to `main`
- merge any branch
- self-approve the task

## Documentation notes

- **Docs-only changes** — this task should not change application behavior.
- **Run formatting/checks** where applicable (e.g., markdown linting).
- **Be concise** — prefer clear, minimal documentation over verbose explanations.

## Required artifacts

- `~/.hermes/task-artifacts/{task_key}/` folder
- `git_status.txt` with `git status --short --untracked-files=all`
- `worktree_info.txt` with `git worktree list` output
- `completion_report.md` with changed files and summary

## Required checks

```bash
<any applicable markdown linting or formatting checks>
```

## Final Kanban comment

```
{task_key} completed and waiting for human review.

Changed files:
- ...

Checks:
- ...

PR required:
- yes/no

Recommendation:
- accept / revise
```

## Final blocked reason

```
waiting_for_human_review
```
"""


def build_bugfix_skeleton(task_key: str, title: str, goal: str) -> str:
    return f"""# {task_key} — {title}

## Project

bullet-journal-app Hermes workflow tooling.

## Repo

```
{REPO_ROOT}
```

## Task type

Bug fix.

## Task key

{task_key}

## Title

{title}

## Goal

{goal}

## Background

<Description of the bug and its impact.>

## Required workspace behavior

The worker must operate only inside the verified worktree assigned to this task.

Before making changes, verify:

```bash
pwd
git rev-parse --show-toplevel
git status --short --untracked-files=all
git branch --show-current
```

## Allowed changes

- <files that need to be modified to fix the bug>
- <test files to add or update>

## Forbidden actions

Do not:
- modify app source code unrelated to the bug fix
- modify database code
- modify `bullet_journal.db`
- modify `.gitignore` unless strictly necessary
- modify Hermes global config
- create a real Hermes task from the new template script during tests
- push directly to `main`
- merge any branch
- self-approve the task

## Bug fix guidance

1. **Reproduce or explain the bug** — describe steps to reproduce or the root cause.
2. **Patch root cause** — fix the underlying issue, not just the symptom.
3. **Add or update tests where practical** — ensure the bug doesn't regress.
4. **Verify the fix** — run relevant checks/tests to confirm the fix works.

## Required artifacts

- `~/.hermes/task-artifacts/{task_key}/` folder
- `git_status.txt` with `git status --short --untracked-files=all`
- `worktree_info.txt` with `git worktree list` output
- `completion_report.md` with bug description, fix applied, and changed files

## Required checks

```bash
python3 -m py_compile <fixed_script.py>
<any applicable tests>
```

## Final Kanban comment

```
{task_key} completed and waiting for human review.

Bug:
- ...

Fix applied:
- ...

Changed files:
- ...

Checks:
- ...

PR required:
- yes/no

Recommendation:
- accept / revise
```

## Final blocked reason

```
waiting_for_human_review
```
"""


def build_review_skeleton(task_key: str, title: str, goal: str) -> str:
    return f"""# {task_key} — {title}

## Project

bullet-journal-app Hermes workflow tooling.

## Repo

```
{REPO_ROOT}
```

## Task type

Code review.

## Task key

{task_key}

## Title

{title}

## Goal

{goal}

## Background

<Context for this review — what PR, commit, or code change is being reviewed?>

## Required workspace behavior

The worker must operate only inside the verified worktree assigned to this task.

Before making changes, verify:

```bash
pwd
git rev-parse --show-toplevel
git status --short --untracked-files=all
git branch --show-current
```

## Review scope

<What should the reviewer inspect? Diff, tests, specific files?>

## Allowed changes

This is a review task. Source code changes are NOT allowed unless explicitly listed here:
- <list any allowed file changes, or "none">
- <...>

## Forbidden actions

Do not:
- modify app source code unless explicitly requested in the review goal
- modify database code
- modify `bullet_journal.db`
- modify `.gitignore`
- modify Hermes global config
- create a real Hermes task from the new template script during tests
- push directly to `main`
- merge any branch
- self-approve the task

## Review guidance

1. **Inspect diff/status/tests** — review the full changeset carefully.
2. **Produce review verdict** — note any blocking issues, suggestions, or approval.
3. **No source changes unless explicitly requested** — review only; implement separately if needed.

## Required artifacts

- `~/.hermes/task-artifacts/{task_key}/` folder
- `review_report.md` with findings, verdict, and any blocking issues
- `git_status.txt` with `git status --short --untracked-files=all`
- `worktree_info.txt` with `git worktree list` output

## Required checks

```bash
git diff <ref> --stat
git diff <ref>
<any applicable test runs>
```

## Final Kanban comment

```
{task_key} completed and waiting for human review.

Verdict:
- ...

Blocking issues:
- ...

Findings:
- ...

PR required:
- no

Recommendation:
- accept / revise
```

## Final blocked reason

```
waiting_for_human_review
```
"""


# Map template type to builder function
TEMPLATE_BUILDERS = {
    "analysis": build_analysis_skeleton,
    "implementation": build_implementation_skeleton,
    "docs": build_docs_skeleton,
    "bugfix": build_bugfix_skeleton,
    "review": build_review_skeleton,
}


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def build_worktree_path(task_key: str) -> str:
    return f"/home/ubuntu/bullet_journal_app/.worktrees/{task_key}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate reusable Hermes Kanban task body templates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Supported --type values: analysis, implementation, docs, bugfix, review

            NOTE: This script only generates a markdown body file.
            It does NOT create Hermes tasks, worktrees, or invoke bj_kanban_create.py.
        """),
    )
    parser.add_argument(
        "--type", required=True,
        help=f"Task type. One of: {', '.join(sorted(TEMPLATE_TYPES))}",
    )
    parser.add_argument(
        "--task-key", required=True,
        help="Task key (e.g. BJ-0004). Allowed: [A-Za-z0-9._-]+",
    )
    parser.add_argument(
        "--title", required=True,
        help="Short descriptive task title",
    )
    parser.add_argument(
        "--goal", required=True,
        help="One-paragraph description of what this task must achieve",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output file path. If omitted, must use --dry-run.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print generated body to stdout without writing a file",
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Validate
    # ------------------------------------------------------------------
    if args.type not in TEMPLATE_TYPES:
        print(f"ERROR: Invalid --type '{args.type}'. Must be one of:", file=sys.stderr)
        for t in sorted(TEMPLATE_TYPES):
            print(f"  - {t}", file=sys.stderr)
        sys.exit(1)

    import re
    if not re.match(r"^[A-Za-z0-9._-]+$", args.task_key):
        print(f"ERROR: Task key '{args.task_key}' contains unsafe characters.", file=sys.stderr)
        print("Allowed: [A-Za-z0-9._-]+", file=sys.stderr)
        sys.exit(1)

    if not args.title.strip():
        print("ERROR: --title is required and cannot be empty.", file=sys.stderr)
        sys.exit(1)

    if not args.goal.strip():
        print("ERROR: --goal is required and cannot be empty.", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run and not args.output:
        print("ERROR: --output is required when not using --dry-run.", file=sys.stderr)
        print("Use --dry-run to print to stdout instead.", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    builder = TEMPLATE_BUILDERS[args.type]
    worktree_path = build_worktree_path(args.task_key)

    # Generate the skeleton (without header — header is governance-level)
    skeleton = builder(args.task_key, args.title.strip(), args.goal.strip())

    # Add governance header (same one used by bj_kanban_create.py)
    body = GOVERNANCE_HEADER.format(
        worktree_path=worktree_path,
        repo_root=REPO_ROOT,
    ) + "\n" + skeleton

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    if args.dry_run:
        print(body)
    else:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(body)
        print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
