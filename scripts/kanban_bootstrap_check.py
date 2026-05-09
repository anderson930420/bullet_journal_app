#!/usr/bin/env python3
"""
kanban_bootstrap_check.py — Read-only bootstrap validation for Hermes workflow.

Checks that a repository has the minimum files and structure needed to run
the Hermes Kanban workflow. Completely read-only — makes no mutations.

Usage:
    python3 scripts/kanban_bootstrap_check.py
    python3 scripts/kanban_bootstrap_check.py --project bullet-journal

Exit codes:
    0 — all checks passed
    1 — one or more failures
    2 — internal error (missing deps, bad args)
"""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_CONFIG = "config/projects.yaml"

# Scripts that must exist for the workflow to function
REQUIRED_SCRIPTS = [
    "scripts/kanban_create_safe.py",
    "scripts/kanban_pr_handoff.py",
    "scripts/kanban_accept_cleanup.py",
    "scripts/kanban_workflow_regression.py",
    "scripts/kanban_task_audit.py",
    "scripts/kanban_artifact_manifest.py",
    "scripts/kanban_worker_guard.py",
]

# Docs that should exist for a fully documented workflow
REQUIRED_DOCS = [
    "docs/hermes_workflow_operating_model.md",
    "docs/hermes_workflow_bootstrap.md",
    "docs/hermes_artifact_contract.md",
]

# Scripts that are optional but recommended
OPTIONAL_SCRIPTS = [
    "scripts/kanban_new_task_safe.py",
]

# Config file that must exist
REQUIRED_CONFIG = "config/projects.yaml"


def check(name: str, condition: bool, message: str) -> bool:
    """Print PASS/WARN/FAIL and return whether check passed."""
    if condition:
        print(f"PASS  {name}: {message}")
        return True
    else:
        print(f"FAIL  {name}: {message}")
        return False


def check_warn(name: str, condition: bool, message: str) -> bool:
    """Print PASS/WARN/FAIL (WARN for non-critical checks) and return pass status."""
    if condition:
        print(f"PASS  {name}: {message}")
        return True
    else:
        print(f"WARN  {name}: {message}")
        return True  # WARN does not cause exit code 1


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    """Run a command, return (exit_code, stderr/stdout)."""
    import subprocess
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 2, str(e)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Hermes workflow bootstrap check")
    parser.add_argument("--project", help="Project name to validate in config/projects.yaml")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help=f"Path to projects.yaml (default: {DEFAULT_CONFIG})")
    parser.add_argument("--quiet", action="store_true", help="Suppress PASS output, show FAIL/WARN only")
    args = parser.parse_args()

    failures = 0
    warnings = 0

    # Find repo root
    rc, git_root = run_cmd(["git", "rev-parse", "--show-toplevel"])
    if rc != 0:
        print(f"FAIL  git_repo: Not inside a git repository (git rev-parse --show-toplevel failed)")
        return 1
    git_root = git_root.strip()
    if not args.quiet:
        print(f"INFO  Repo root: {git_root}")

    # Check repo is a valid git repository (worktrees share main .git, so check via git)
    rc_git, git_dir = run_cmd(["git", "rev-parse", "--git-dir"])
    ok = check(".git_dir", rc_git == 0, f"Valid git repository (git-dir: {git_dir.strip()})")
    if not ok:
        failures += 1

    # Check required scripts exist
    for script in REQUIRED_SCRIPTS:
        path = os.path.join(git_root, script)
        ok = check(f"script/{script}", os.path.isfile(path), f"{script} {'exists' if os.path.isfile(path) else 'MISSING'}")
        if not ok:
            failures += 1

    # Check required docs exist
    for doc in REQUIRED_DOCS:
        path = os.path.join(git_root, doc)
        ok = check(f"doc/{doc}", os.path.isfile(path), f"{doc} {'exists' if os.path.isfile(path) else 'MISSING'}")
        if not ok:
            failures += 1

    # Check optional scripts (warnings only)
    for script in OPTIONAL_SCRIPTS:
        path = os.path.join(git_root, script)
        ok = check_warn(f"script (recommended)/{script}", os.path.isfile(path),
                        f"{script} {'exists' if os.path.isfile(path) else 'not found (optional)'}")
        if not ok:
            warnings += 1

    # Check config/projects.yaml exists
    config_path = os.path.join(git_root, args.config)
    ok = check("config/projects.yaml", os.path.isfile(config_path),
               f"projects.yaml {'exists' if os.path.isfile(config_path) else 'MISSING'}")
    if not ok:
        failures += 1

    # If config exists, validate project if given
    if os.path.isfile(config_path) and args.project:
        try:
            import yaml
            with open(config_path) as f:
                data = yaml.safe_load(f)
            projects = data.get("projects", {})
            if args.project in projects:
                proj = projects[args.project]
                repo_val = proj.get("repo", "")
                default_branch = proj.get("default_branch", "")
                artifact_root = proj.get("artifact_root", "")
                ok = check("config/project_valid",
                          all([repo_val, default_branch, artifact_root]),
                          f"project {args.project!r} has repo, default_branch, artifact_root")
                if not ok:
                    failures += 1

                # Check repo path actually exists
                if repo_val:
                    ok = check("config/project_repo_exists", os.path.isdir(repo_val),
                               f"project repo path {'exists' if os.path.isdir(repo_val) else 'NOT FOUND'}: {repo_val}")
                    if not ok:
                        failures += 1
            else:
                print(f"FAIL  config/project_unknown: project {args.project!r} not in projects.yaml")
                failures += 1
        except Exception as e:
            print(f"WARN  config/parse_error: Could not parse {config_path}: {e}")
            warnings += 1

    # Summary
    print()
    if failures > 0:
        print(f"RESULT: {failures} FAIL, {warnings} WARN — bootstrap incomplete")
        return 1
    elif warnings > 0:
        print(f"RESULT: {warnings} WARN — bootstrap OK but some recommended items missing")
        return 0
    else:
        print("RESULT: All checks PASSED — bootstrap ready")
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)