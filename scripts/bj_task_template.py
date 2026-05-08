#!/usr/bin/env python3
"""
bj_task_template.py — Reusable Hermes Kanban Task Body Generator

Generates consistent, well-structured task bodies for the bullet-journal-app
Hermes Kanban workflow by building a concrete task wrapper that embeds
canonical template guidance from templates/hermes_tasks/<type>.md.

Supported types: analysis, implementation, docs, bugfix, review

Usage:
    python3 scripts/bj_task_template.py \
      --type implementation
      --task-key BJ-0008
      --title "Add reusable task body templates"
      --goal "Add reusable Hermes task body templates for future repo tasks."
      --output /tmp/BJ-0008.generated.md

    python3 scripts/bj_task_template.py --type docs --task-key BJ-0008 \
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


def build_worktree_path(task_key: str) -> str:
    return f"/home/ubuntu/bullet_journal_app/.worktrees/{task_key}"


# ------------------------------------------------------------------
# Task-key-specific section content (replaces template placeholders)
# ------------------------------------------------------------------

# For each task type, define the concrete section content that replaces
# the generic ## Sections code block in the template.
# These are derived from the user-supplied goal; no <...> placeholders remain.


def _section_content_for_review(task_key: str, title: str, goal: str) -> str:
    return textwrap.dedent(f"""\
        ## Goal

        {goal}

        ## Background

        This review task was created to evaluate the changes described in the goal.
        Review the provided diff, tests, and affected files carefully and produce
        a verdict with any blocking issues noted.

        ## Review scope

        Inspect all changed files, related tests, and any documentation updates
        that are part of this task. Verify correctness, consistency with existing
        patterns, and absence of regressions.

        ## Allowed changes

        This is a review task. Source code changes are NOT allowed unless explicitly listed here:
        - none
        """)


def _section_content_for_analysis(task_key: str, title: str, goal: str) -> str:
    return textwrap.dedent(f"""\
        ## Goal

        {goal}

        ## Background

        This analysis task was created to investigate the topic described in the goal.
        Conduct a thorough, read-only investigation and document findings, decisions,
        or recommendations in the completion report.

        ## Analysis scope

        Address the specific questions and objectives raised in the goal above.
        Inspect available data, code, documentation, or other relevant sources.
        Report any evidence found and note any remaining uncertainties.
        """)


def _section_content_for_implementation(task_key: str, title: str, goal: str) -> str:
    return textwrap.dedent(f"""\
        ## Goal

        {goal}

        ## Background

        This implementation task was created to deliver the change described in the goal.
        Inspect existing code patterns first, then make minimal scoped changes directly
        tied to the goal. Verify behavior with relevant tests before completing.

        ## Allowed changes

        Modify only the files necessary to achieve the goal. Report all changed
        and new files in the completion report.
        """)


def _section_content_for_bugfix(task_key: str, title: str, goal: str) -> str:
    return textwrap.dedent(f"""\
        ## Goal

        {goal}

        ## Background

        This bug fix task was created to address the defect described in the goal.
        Reproduce or explain the bug, fix the root cause (not just the symptom),
        and add or update tests to prevent regression.

        ## Allowed changes

        Modify only the files necessary to fix the bug. Add or update test files
        as needed to cover the fix.
        """)


def _section_content_for_docs(task_key: str, title: str, goal: str) -> str:
    return textwrap.dedent(f"""\
        ## Goal

        {goal}

        ## Background

        This documentation task was created to address the docs need described in the goal.
        Make only documentation changes; do not alter application behavior.

        ## Allowed changes

        - docs/*.md
        - README.md (short pointers only)
        - Any other documentation files directly related to the goal
        """)


SECTION_CONTENT = {
    "review": _section_content_for_review,
    "analysis": _section_content_for_analysis,
    "implementation": _section_content_for_implementation,
    "bugfix": _section_content_for_bugfix,
    "docs": _section_content_for_docs,
}


# ------------------------------------------------------------------
# Template loading — loads canonical guidance (no generic sections)
# ------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
TEMPLATES_DIR = SCRIPT_DIR.parent / "templates" / "hermes_tasks"


def load_template_guidance(task_type: str, task_key: str) -> str:
    """Load the canonical template guidance section.

    The template structure after the concrete sections is:
        # <Type> Task Template
        ## Purpose
        ## Task type
        ## Key characteristics
        ## Sections
        ```markdown
        ## Goal
        <...placeholders...>
        ```
        ## Required artifacts     ← we anchor here
        ## Governance notes
        ## Worker preflight guard
        ## Artifact manifest initialization
        ## Final validation

    We return everything from "## Required artifacts" onwards, which is
    the canonical worker guidance (artifact manifest, preflight guard,
    init, validation).  The generic ## Sections block (which contains
    unresolved <...> placeholders) is simply skipped.

    All <task-key> placeholders in the canonical guidance are replaced
    with the actual task_key.  <task-id> is left as-is because the
    Hermes task ID is not available at body-generation time; workers
    must substitute it from their task context.
    """
    template_path = TEMPLATES_DIR / f"{task_type}.md"
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template not found: {template_path}. "
            f"Available types: {', '.join(sorted(TEMPLATE_TYPES))}"
        )

    template_text = template_path.read_text()

    # Anchor on ## Required artifacts — everything after it is canonical guidance
    marker = "## Required artifacts\n"
    if marker not in template_text:
        raise ValueError(
            f"Template {task_type}.md is missing '## Required artifacts' section. "
            "Cannot generate task body."
        )

    start = template_text.index(marker)
    guidance = template_text[start:]

    # Substitute <task-key> with the concrete task key throughout
    guidance = guidance.replace("<task-key>", task_key)

    return guidance


def build_body(
    task_type: str,
    task_key: str,
    title: str,
    goal: str,
    include_governance: bool = True,
) -> str:
    """Build a concrete task body.

    Structure:
        --- governance header (optional) ---
        # <task_key> — <title>

        ## Project
        ## Repo
        ## Task type
        ## Task key
        ## Title
        ## Goal

        <concrete section content derived from goal — no <...> placeholders>
        <canonical template guidance from templates/hermes_tasks/<type>.md>
        (the ## Sections generic code block is omitted)
    """
    worktree = build_worktree_path(task_key)

    # Concrete task header
    task_header = f"# {task_key} — {title}\n"

    # Standard metadata fields
    metadata = textwrap.dedent(f"""\
        ## Project

        bullet-journal-app Hermes workflow tooling.

        ## Repo

        ```text
        {REPO_ROOT}
        ```

        ## Task type

        {task_type}.

        ## Task key

        {task_key}

        ## Title

        {title}
        """)

    # Concrete section content for this task type (no <...> placeholders)
    section_fn = SECTION_CONTENT.get(task_type)
    if section_fn is None:
        raise ValueError(f"Unknown task type: {task_type}")
    concrete_sections = section_fn(task_key, title, goal)

    # Canonical template guidance (stripped of generic ## Sections block)
    template_guidance = load_template_guidance(task_type, task_key)

    # Assemble
    parts = []
    if include_governance:
        parts.append(
            GOVERNANCE_HEADER.format(
                worktree_path=worktree,
                repo_root=REPO_ROOT,
            )
        )
    parts.append(task_header)
    parts.append(metadata)
    parts.append(concrete_sections)
    parts.append(template_guidance)

    return "\n".join(parts)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

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
    parser.add_argument(
        "--no-governance-header", action="store_true",
        help="Omit the governance header from the generated body. "
             "Useful when the caller (e.g. kanban_new_task_safe.py) "
             "or a submitter will add its own governance header.",
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
    body = build_body(
        args.type,
        args.task_key,
        args.title.strip(),
        args.goal.strip(),
        include_governance=not args.no_governance_header,
    )

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
