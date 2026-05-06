#!/usr/bin/env python3
"""
kanban_worker_guard.py — Generic worker preflight guard for Hermes Kanban.

Verifies that a worker is operating inside the expected verified worktree,
on the expected branch, and not modifying the main repo directly.

Usage:
    python3 scripts/kanban_worker_guard.py \
        --project bullet-journal \
        --task-key BJ-0016R

Optional overrides:
    python3 scripts/kanban_worker_guard.py \
        --project bullet-journal \
        --task-key BJ-0016R \
        --expected-worktree /path/to/worktree \
        --expected-branch worktree/BJ-0016R \
        --write-artifacts

Exit codes:
    0  — all checks passed
    1  — check failed (see error message)
    2  — internal error (missing config, bad args, etc.)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a command, return (exit_code, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 2, "", "command timed out"
    except Exception as e:
        return 2, "", str(e)


def load_config(config_path: str) -> dict:
    """Load and parse config/projects.yaml."""
    import yaml

    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("projects", {})


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes Kanban worker preflight guard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", required=True, help="Project name from config/projects.yaml")
    parser.add_argument("--task-key", required=True, help="Task key (e.g. BJ-0016R)")
    parser.add_argument(
        "--config",
        default="config/projects.yaml",
        help="Path to projects.yaml (default: config/projects.yaml relative to script)",
    )
    parser.add_argument(
        "--expected-worktree",
        help="Override expected worktree path (default: <repo>/.worktrees/<task-key>)",
    )
    parser.add_argument(
        "--expected-branch",
        help="Override expected branch (default: <branch_prefix><task-key>)",
    )
    parser.add_argument(
        "--artifact-dir",
        help="Override artifact directory (default: <artifact_root>/<task-key>)",
    )
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="Write guard_report.txt to artifact directory",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress PASS output, only print errors",
    )
    args = parser.parse_args()

    # Resolve config path: if relative, resolve from git root (worktree), not script dir
    if os.path.isabs(args.config):
        config_path = args.config
    else:
        # Try git root first (the worktree), then fall back to script dir
        rc, git_root, _ = run(["git", "rev-parse", "--show-toplevel"])
        if rc == 0 and os.path.exists(os.path.join(git_root, args.config)):
            config_path = os.path.join(git_root, args.config)
        else:
            script_dir = Path(__file__).parent.resolve()
            config_path = str(script_dir / args.config)

    errors: list[str] = []

    # 1. Load config
    try:
        projects = load_config(config_path)
    except FileNotFoundError:
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: failed to parse config: {e}", file=sys.stderr)
        return 2

    # 2. Validate project exists
    if args.project not in projects:
        print(f"ERROR: project '{args.project}' not found in {config_path}", file=sys.stderr)
        available = ", ".join(sorted(projects.keys()))
        print(f"  available projects: {available}", file=sys.stderr)
        return 2

    proj = projects[args.project]

    # 3. Resolve repo path
    repo = proj["repo"]
    if not os.path.isabs(repo):
        repo = str(script_dir / repo)

    # 4. Validate repo exists
    if not os.path.isdir(repo):
        print(f"ERROR: repo directory does not exist: {repo}", file=sys.stderr)
        return 2

    # 5. Validate repo is a git repository
    rc, _, _ = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=repo)
    if rc != 0:
        print(f"ERROR: repo is not a git repository: {repo}", file=sys.stderr)
        return 2

    # 6. Resolve expected worktree
    if args.expected_worktree:
        expected_worktree = args.expected_worktree
    else:
        expected_worktree = os.path.join(repo, ".worktrees", args.task_key)

    # 7. Resolve expected branch
    branch_prefix = proj.get("branch_prefix", "worktree/")
    if args.expected_branch:
        expected_branch = args.expected_branch
    else:
        expected_branch = branch_prefix + args.task_key

    # 8. Determine current working directory
    cwd = os.getcwd()

    # 9. Determine git root via git rev-parse
    rc, actual_git_root, err = run(["git", "rev-parse", "--show-toplevel"])
    if rc != 0:
        print(f"ERROR: not inside a git repository: {err}", file=sys.stderr)
        return 2

    # 10. Determine current branch
    rc, actual_branch, err = run(["git", "branch", "--show-current"])
    if rc != 0:
        print(f"ERROR: failed to get current branch: {err}", file=sys.stderr)
        return 2

    # 11. Check git root equals expected worktree
    if os.path.normpath(actual_git_root) != os.path.normpath(expected_worktree):
        errors.append(
            f"Wrong worktree: expected '{expected_worktree}' but running in '{actual_git_root}'"
        )

    # 12. Check branch matches expected
    if actual_branch != expected_branch:
        errors.append(
            f"Wrong branch: expected '{expected_branch}' but on '{actual_branch}'"
        )

    # 13. Check git root is not the main repo root
    main_repo_root = os.path.normpath(repo)
    if os.path.normpath(actual_git_root) == main_repo_root:
        errors.append(
            f"Worker is running in main repo '{main_repo_root}' — must use a worktree"
        )

    # 14. Resolve artifact dir and validate it exists
    artifact_root = proj.get("artifact_root", "/home/ubuntu/.hermes/task-artifacts")
    if args.artifact_dir:
        artifact_dir = args.artifact_dir
    else:
        artifact_dir = os.path.join(artifact_root, args.task_key)

    if args.write_artifacts:
        os.makedirs(artifact_dir, exist_ok=True)
    elif not os.path.isdir(artifact_dir):
        errors.append(
            f"Artifact directory does not exist: {artifact_dir} "
            f"(use --write-artifacts to create it, or provide --artifact-dir)"
        )

    # 15. Check main repo git status from repo root
    rc, main_status, _ = run(
        ["git", "status", "--porcelain"],
        cwd=repo,
    )
    if rc != 0:
        # Not a fatal error — just record that we couldn't check
        main_status = "(unable to determine)"

    # 16. Fail if main repo has uncommitted or untracked changes
    if main_status and main_status != "":
        errors.append(
            f"Main repo has uncommitted/untracked changes — must be clean:\n  {main_status}"
        )

    # 17/18. Print result
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(file=sys.stderr)
        print("Preflight FAILED", file=sys.stderr)
        result = "FAIL"
        exit_code = 1
    else:
        if not args.quiet:
            print("Preflight guard PASSED")
            print(f"  project:        {args.project}")
            print(f"  task_key:       {args.task_key}")
            print(f"  worktree:       {actual_git_root}")
            print(f"  branch:         {actual_branch}")
        result = "PASS"
        exit_code = 0

    # Write artifact if requested
    if args.write_artifacts:
        report_path = os.path.join(artifact_dir, "guard_report.txt")
        try:
            with open(report_path, "w") as f:
                f.write(f"project={args.project}\n")
                f.write(f"task_key={args.task_key}\n")
                f.write(f"repo={repo}\n")
                f.write(f"expected_worktree={expected_worktree}\n")
                f.write(f"actual_git_root={actual_git_root}\n")
                f.write(f"expected_branch={expected_branch}\n")
                f.write(f"actual_branch={actual_branch}\n")
                f.write(f"artifact_dir={artifact_dir}\n")
                f.write(f"main_repo_status={main_status}\n")
                f.write(f"result={result}\n")
            if exit_code == 0 and not args.quiet:
                print(f"  artifact:       {report_path}")
        except Exception as e:
            print(f"WARNING: failed to write artifact: {e}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
