#!/usr/bin/env python3
"""
kanban_new_task_safe.py — Generic One-Command Task Submit Flow

Combines body generation (bj_task_template.py) and safe submission
(kanban_create_safe.py) into a single command while preserving verified
worktrees, project registry lookup, artifact folders, and human review gates.

Usage:
    python3 scripts/kanban_new_task_safe.py \
      --project bullet-journal \
      --task-key BJ-0017B \
      --type implementation \
      --title "Add generic one-command task submit flow" \
      --goal "Generate a task body and submit it through the generic safe submitter." \
      --priority 1 \
      --max-runtime 2h \
      --dry-run

Supported task body types: analysis, implementation, docs, bugfix, review

In dry-run mode:
  - Does NOT create a real Hermes task
  - Does NOT create a real worktree
  - Does NOT create a persistent artifact folder
  - Generates the body (without governance header from template) and
    passes it to kanban_create_safe.py --dry-run
  - Uses a single tracked temp file that is cleaned up before exit

In real-run mode:
  - Generates a markdown task body (without governance header from template)
  - Writes it to --body-output (default: /tmp/<task-key>.md)
  - Refuses to overwrite an existing body file unless --overwrite is given
  - Calls kanban_create_safe.py (without --dry-run) to create worktree and Hermes task
  - kanban_create_safe.py prepends the correct generic governance header
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
SUBMITTER_SCRIPT = SCRIPT_DIR / "kanban_create_safe.py"
TEMPLATE_TYPES = {"analysis", "implementation", "docs", "bugfix", "review"}
ALLOWED_KEY_CHARS = re.compile(r"^[A-Za-z0-9._-]+$")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def run(*cmd: str, capture: bool = True, check: bool = True,
        stdin_input: Optional[str] = None,
        workdir: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command using subprocess with explicit argument list (no shell)."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        input=stdin_input,
        check=check,
        cwd=workdir,
    )


def validate_args(args: argparse.Namespace) -> None:
    """Validate the combined arguments."""
    errors = []

    if not args.project:
        errors.append("--project is required")
    if not args.task_key:
        errors.append("--task-key is required")
    if not args.type:
        errors.append("--type is required")
    if not args.title:
        errors.append("--title is required")
    if not args.goal:
        errors.append("--goal is required")

    if args.type and args.type not in TEMPLATE_TYPES:
        errors.append(f"--type must be one of: {', '.join(sorted(TEMPLATE_TYPES))}")

    if args.task_key and not ALLOWED_KEY_CHARS.match(args.task_key):
        errors.append(
            f"--task-key '{args.task_key}' contains unsafe characters. "
            "Allowed: [A-Za-z0-9._-]+"
        )

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)


def resolve_body_output_path(args: argparse.Namespace) -> Path:
    """Resolve the body output path.

    In real-run mode: defaults to /tmp/<task-key>.md
    In dry-run mode: caller is responsible for temp file management.
    """
    if args.body_output:
        return Path(args.body_output).resolve()

    # Default: /tmp/<task-key>.md
    return Path(f"/tmp/{args.task_key}.md").resolve()


def check_body_file_writeable(path: Path, overwrite: bool) -> None:
    """Check if we can write to the body output path."""
    if path.exists() and not overwrite:
        print(f"ERROR: Body file already exists: {path}", file=sys.stderr)
        print("Pass --overwrite to overwrite it.", file=sys.stderr)
        sys.exit(1)


# ------------------------------------------------------------------
# Step 1: Generate body via bj_task_template.py
# ------------------------------------------------------------------

def generate_body(args: argparse.Namespace) -> tuple[str, Optional[Path]]:
    """Generate task body using bj_task_template.py.

    Uses --no-governance-header so the template skeleton has no duplicate
    governance section; kanban_create_safe.py adds the correct generic
    governance header.

    Returns (body_text, path_written_or_none).
    In dry-run mode: body_text is returned, path is None (no temp file created).
    In real-run mode: body_text is returned, path is the file written.
    """
    body_path = resolve_body_output_path(args)
    is_dry_run = args.dry_run

    if is_dry_run:
        # In dry-run mode, run the template with --dry-run so body comes
        # back on stdout (no file I/O, no "Generated:" message in stderr).
        # Use --no-governance-header so we get the raw skeleton without
        # a duplicate governance section; kanban_create_safe.py adds the
        # correct generic governance header.
        template_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "bj_task_template.py"),
            "--type", args.type,
            "--task-key", args.task_key,
            "--title", args.title,
            "--goal", args.goal,
            "--dry-run",
            "--no-governance-header",
        ]

        print(f"\n=== Step 1: Generate task body ===")
        print(f"Running: {' '.join(template_cmd)}")

        result = run(*template_cmd, check=False)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"ERROR: bj_task_template.py failed with exit code {result.returncode}",
                  file=sys.stderr)
            sys.exit(1)

        # stdout is the generated body (--dry-run prints skeleton to stdout)
        body_text = result.stdout
        return body_text, None

    else:
        # Real-run: write to the target file
        check_body_file_writeable(body_path, args.overwrite)
        template_cmd = [
            sys.executable,
            str(SCRIPT_DIR / "bj_task_template.py"),
            "--type", args.type,
            "--task-key", args.task_key,
            "--title", args.title,
            "--goal", args.goal,
            "--output", str(body_path),
            "--no-governance-header",
        ]

        print(f"\n=== Step 1: Generate task body ===")
        print(f"Running: {' '.join(template_cmd)}")

        result = run(*template_cmd, check=False)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"ERROR: bj_task_template.py failed with exit code {result.returncode}",
                  file=sys.stderr)
            sys.exit(1)

        body_text = body_path.read_text()
        return body_text, body_path


# ------------------------------------------------------------------
# Step 2: Call kanban_create_safe.py (dry-run or real)
# ------------------------------------------------------------------

def call_submitter(args: argparse.Namespace, body_path: Path) -> None:
    """Call kanban_create_safe.py with the generated body file."""

    submitter_cmd = [
        sys.executable,
        str(SUBMITTER_SCRIPT),
        "--project", args.project,
        "--task-key", args.task_key,
        "--title", args.title,
        "--body-file", str(body_path),
    ]

    if args.assignee:
        submitter_cmd.extend(["--assignee", args.assignee])
    if args.priority is not None:
        submitter_cmd.extend(["--priority", str(args.priority)])
    if args.max_runtime:
        submitter_cmd.extend(["--max-runtime", args.max_runtime])
    if args.config:
        submitter_cmd.extend(["--config", args.config])
    if args.json:
        submitter_cmd.append("--json")
    if args.dry_run:
        submitter_cmd.append("--dry-run")

    print(f"\n=== Step 2: Submit via safe submitter ===")
    print(f"Running: {' '.join(submitter_cmd)}")

    result = run(*submitter_cmd, check=False)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"ERROR: kanban_create_safe.py failed with exit code {result.returncode}",
              file=sys.stderr)
        sys.exit(1)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic one-command task submit flow — generate body and submit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Supported --type values: analysis, implementation, docs, bugfix, review

            Required:
              --project   Project name as registered in config/projects.yaml
              --task-key  Task key (e.g. BJ-0017B). Allowed: [A-Za-z0-9._-]+
              --type      Task body type
              --title     Task title
              --goal      One-paragraph description of what this task must achieve

            Optional:
              --assignee     Assignee profile name (falls back to project's default_assignee)
              --priority     Task priority (integer)
              --max-runtime  Max runtime (e.g. 2h, 30m)
              --config       Path to projects.yaml (default: config/projects.yaml)
              --body-output  Output file for generated body (default: /tmp/<task-key>.md)
              --overwrite    Overwrite existing body file
              --dry-run      Preview without creating worktree or Hermes task
              --json         Pass --json to hermes kanban create

            Examples:

            Dry run:
              python3 scripts/kanban_new_task_safe.py \\
                --project bullet-journal \\
                --task-key BJ-0017B \\
                --type implementation \\
                --title "Add generic one-command task submit flow" \\
                --goal "Generate a task body and submit it through the generic safe submitter." \\
                --priority 1 \\
                --max-runtime 2h \\
                --dry-run

            Real run:
              python3 scripts/kanban_new_task_safe.py \\
                --project bullet-journal \\
                --task-key BJ-0017B \\
                --type implementation \\
                --title "Add generic one-command task submit flow" \\
                --goal "Generate a task body and submit it through the generic safe submitter." \\
                --priority 1 \\
                --max-runtime 2h

            The wrapper always stops at human review because the created task body
            inherits governance rules from the template system.
        """),
    )

    parser.add_argument("--project", required=True,
                        help="Project name as registered in config/projects.yaml")
    parser.add_argument("--task-key", required=True,
                        help="Task key (e.g. BJ-0017B). Allowed: [A-Za-z0-9._-]+")
    parser.add_argument("--type", required=True,
                        help=f"Task body type. One of: {', '.join(sorted(TEMPLATE_TYPES))}")
    parser.add_argument("--title", required=True,
                        help="Short descriptive task title")
    parser.add_argument("--goal", required=True,
                        help="One-paragraph description of what this task must achieve")
    parser.add_argument("--assignee", default=None,
                        help="Assignee profile name (falls back to project's default_assignee)")
    parser.add_argument("--priority", type=int, default=None)
    parser.add_argument("--max-runtime", default=None,
                        help="Max runtime (e.g. 2h, 30m)")
    parser.add_argument("--config", default=None,
                        help="Path to projects.yaml (default: config/projects.yaml)")
    parser.add_argument("--body-output", default=None,
                        help="Output file for generated body (default: /tmp/<task-key>.md)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Overwrite existing body file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without creating worktree or Hermes task")
    parser.add_argument("--json", action="store_true",
                        help="Pass --json to hermes kanban create")

    args = parser.parse_args()

    # Validate
    validate_args(args)

    # Set config default if not provided
    if not args.config:
        args.config = "config/projects.yaml"

    # ------------------------------------------------------------------
    # Dry-run mode
    # ------------------------------------------------------------------
    if args.dry_run:
        # Track the ONE temp file we create for this dry-run.
        # generate_body() creates it, we clean it up in finally.
        dryrun_temp_path: Optional[str] = None
        try:
            body_text, _ = generate_body(args)

            # Write body to a single tracked temp file so we can pass it
            # to the submitter's dry-run mode. We use tempfile so the
            # filename is unique and we are guaranteed to be able to write.
            fd, dryrun_temp_path = tempfile.mkstemp(suffix=".md",
                                                     prefix=f"{args.task_key}_dryrun_")
            os.close(fd)
            Path(dryrun_temp_path).write_text(body_text)

            # Build submitter args namespace for dry-run
            args_dry = argparse.Namespace(
                project=args.project,
                task_key=args.task_key,
                title=args.title,
                body_file=dryrun_temp_path,
                assignee=args.assignee,
                priority=args.priority,
                max_runtime=args.max_runtime,
                config=args.config,
                json=args.json,
                dry_run=True,
            )
            call_submitter(args_dry, Path(dryrun_temp_path))

            print("\n=== DRY RUN COMPLETE — no persistent changes made ===")
            print(f"Generated body preview (first 50 lines):")
            lines = body_text.splitlines()
            for line in lines[:50]:
                print(line)
            if len(lines) > 50:
                print(f"... ({len(lines) - 50} more lines)")

        finally:
            # Clean up the ONE temp file we created for this dry-run.
            if dryrun_temp_path and os.path.exists(dryrun_temp_path):
                os.unlink(dryrun_temp_path)
                print(f"\n(Cleaned up temp file: {dryrun_temp_path})")

        return

    # ------------------------------------------------------------------
    # Real-run mode
    # ------------------------------------------------------------------
    body_text, body_path = generate_body(args)

    # body_path is guaranteed to be set in real-run mode
    assert body_path is not None

    print(f"\nGenerated task body: {body_path}")
    print(f"Submitting to kanban_create_safe.py...")

    args_real = argparse.Namespace(
        project=args.project,
        task_key=args.task_key,
        title=args.title,
        body_file=str(body_path),
        assignee=args.assignee,
        priority=args.priority,
        max_runtime=args.max_runtime,
        config=args.config,
        json=args.json,
        dry_run=False,
    )
    call_submitter(args_real, body_path)

    print("\n=== SUBMISSION COMPLETE ===")
    print(f"Project:     {args.project}")
    print(f"Task key:    {args.task_key}")
    print(f"Title:       {args.title}")
    print(f"Body file:   {body_path}")
    print(f"\nNext step: the assigned worker will process the task and ")
    print(f"write artifacts to the artifact folder. Human review required.")


if __name__ == "__main__":
    main()
