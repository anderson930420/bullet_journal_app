#!/usr/bin/env python3
"""
kanban_create_safe.py — Generic Safe Kanban Task Submitter via Project Registry

Reads config/projects.yaml to resolve repo, branch, and artifact paths for any
registered project, then creates verified git worktrees and Hermes Kanban tasks
using workspace type `dir:` (never `worktree:` auto-binding).

Safety constraints:
  - Loads project registry from config/projects.yaml
  - Validates --project exists in the registry before doing anything
  - Validates repo exists and is a git repository
  - Validates current branch matches the project's default_branch
  - Always creates worktree under <repo>/.worktrees/<task-key>
  - Always uses --workspace dir:<path> (never --workspace worktree)
  - Never runs: git push, git merge, git reset --hard, git clean -fd
  - Requires main/default branch unless --allow-non-main is passed
  - Rejects unsafe task keys (only [A-Za-z0-9._-]+ allowed)
  - Never overwrites existing worktrees without --reuse-existing-worktree

Usage:
    python3 scripts/kanban_create_safe.py \
        --project bullet-journal \
        --task-key BJ-0017A \
        --title "Introduce project registry and generic safe submitter skeleton" \
        --body-file /tmp/BJ-0017A.md \
        --assignee bullet-eng \
        --priority 1 \
        --max-runtime 2h \
        --dry-run

Dry run (no worktree, no artifact folder, no hermes call):
    python3 scripts/kanban_create_safe.py ... --dry-run
"""

import argparse
import os
import re
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Optional

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
DEFAULT_CONFIG = "config/projects.yaml"
ALLOWED_KEY_CHARS = re.compile(r"^[A-Za-z0-9._-]+$")
FORBIDDEN_GIT_CMDS = {"push", "merge", "reset", "clean"}

GOVERNANCE_HEADER = """
---
## Governance Requirements (MANDATORY)

This task was created by `scripts/kanban_create_safe.py` using a verified worktree
under `dir:` workspace (not `--workspace worktree`).

**You MUST follow these rules:**
- Work ONLY in the verified worktree: `dir:{worktree_path}`
- Do NOT operate from the main repo at `{repo}`
- Do NOT run `git push`
- Do NOT run `git merge`
- Do NOT run `git reset --hard`
- Do NOT run `git clean -fd`
- Do NOT self-approve your own changes
- Do NOT mark done unless the task body explicitly allows it
- Final state MUST be `blocked / waiting_for_human_review` unless the task body explicitly allows `done`
- Write all required artifacts to `{artifact_root}/<task-key>/`
- Record `git status --short --untracked-files=all` in artifacts

---
""".strip()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def run(*cmd: str, capture: bool = True, check: bool = True,
        stdin_input: Optional[str] = None,
        workdir: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command using subprocess with explicit argument list (no shell).

    Rejects commands containing known dangerous git subcommands.
    """
    for word in cmd:
        if word in FORBIDDEN_GIT_CMDS:
            raise ValueError(f"Forbidden command component: {word}")
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        input=stdin_input,
        check=check,
        cwd=workdir,
    )


def load_project_registry(config_path: Path) -> dict:
    """Load and return the projects.yaml registry."""
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        print("Hint: run from the repo root where config/projects.yaml exists.",
              file=sys.stderr)
        sys.exit(1)
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    if not raw or "projects" not in raw:
        print(f"ERROR: {config_path} must contain a 'projects:' key",
              file=sys.stderr)
        sys.exit(1)
    return raw["projects"]


def get_project(projects: dict, name: str) -> dict:
    """Return the project entry, or exit with an error."""
    if name not in projects:
        print(f"ERROR: Unknown project '{name}'. Available: "
              f"{', '.join(sorted(projects.keys()))}", file=sys.stderr)
        sys.exit(1)
    return projects[name]


def validate_repo_exists(repo: Path) -> None:
    """Verify the repo directory exists."""
    if not repo.exists():
        print(f"ERROR: Repo does not exist: {repo}", file=sys.stderr)
        sys.exit(1)


def validate_is_git_repo(repo: Path) -> None:
    """Verify the repo is a valid git repository."""
    result = run("git", "-C", str(repo), "rev-parse", "--git-dir",
                 check=False, capture=True)
    if result.returncode != 0:
        print(f"ERROR: Not a git repository: {repo}", file=sys.stderr)
        sys.exit(1)


def validate_repo_clean(repo: Path) -> None:
    """Verify the main repo has no uncommitted changes."""
    result = run("git", "-C", str(repo), "status", "--porcelain",
                 check=True, capture=True)
    if result.stdout.strip():
        print("ERROR: Main repo has uncommitted changes:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        sys.exit(1)


def validate_current_branch(repo: Path, expected_branch: str,
                            allow_non_main: bool) -> None:
    """Verify the current branch matches the expected default branch."""
    result = run("git", "-C", str(repo), "branch", "--show-current",
                 check=True, capture=True)
    current = result.stdout.strip()
    if current != expected_branch and not allow_non_main:
        print(f"ERROR: Not on branch '{expected_branch}' (current: '{current}'). "
              "Pass --allow-non-main to override.", file=sys.stderr)
        sys.exit(1)


def validate_task_key(key: str) -> None:
    """Validate task key contains only safe characters."""
    if not ALLOWED_KEY_CHARS.match(key):
        print(f"ERROR: Task key '{key}' contains unsafe characters. "
              "Allowed: [A-Za-z0-9._-]+", file=sys.stderr)
        sys.exit(1)


def validate_body_file(path: Path) -> None:
    """Validate the body file exists."""
    if not path.exists():
        print(f"ERROR: Body file does not exist: {path}", file=sys.stderr)
        sys.exit(1)


def resolve_repo_root(project: dict, config_path: Path) -> Path:
    """Resolve the repo root from the project config.

    The repo path in YAML is treated as absolute. If relative (future use),
    it would be resolved relative to the config file's directory.
    """
    repo = Path(project["repo"]).resolve()
    return repo


def worktree_path_for(repo: Path, task_key: str) -> Path:
    return repo / ".worktrees" / task_key


def artifact_path_for(project: dict, task_key: str) -> Path:
    return Path(project["artifact_root"]) / task_key


def verify_worktree(wt_path: Path, expected_branch: str) -> None:
    """Run all required verification checks on the worktree."""
    os.chdir(wt_path)

    checks = {
        "pwd": ["pwd"],
        "git rev-parse --show-toplevel": [
            "git", "rev-parse", "--show-toplevel"],
        "git branch --show-current": ["git", "branch", "--show-current"],
        "git worktree list": ["git", "worktree", "list"],
        "git status --short": [
            "git", "status", "--short", "--untracked-files=all"],
    }

    print("\n=== Worktree Verification ===")
    all_ok = True
    for name, cmd in checks.items():
        result = run(*cmd, workdir=wt_path)
        output = result.stdout.strip()
        print(f"[{name}]")
        print(output)
        if name == "pwd" and output != str(wt_path):
            print(f"  MISMATCH: expected {wt_path}")
            all_ok = False
        elif name == "git rev-parse --show-toplevel" and output != str(wt_path):
            print(f"  MISMATCH: expected {wt_path}")
            all_ok = False
        elif name == "git branch --show-current" and output != expected_branch:
            print(f"  MISMATCH: expected {expected_branch}")
            all_ok = False
    if not all_ok:
        raise RuntimeError("Worktree verification failed")


def create_artifact_folder(artifact_root: Path, task_key: str) -> Path:
    ap = artifact_root / task_key
    ap.mkdir(parents=True, exist_ok=True)
    return ap


def build_hermes_command(args: argparse.Namespace, body_with_header: str,
                         worktree_verified: Path) -> list[str]:
    """Build the hermes kanban create command as a list of args."""
    cmd = [
        "hermes", "kanban", "create",
        args.title,
        "--assignee", args.assignee,
        "--workspace", f"dir:{worktree_verified}",
    ]
    if args.priority is not None:
        cmd.extend(["--priority", str(args.priority)])
    if args.max_runtime:
        cmd.extend(["--max-runtime", args.max_runtime])
    if args.body_file:
        cmd.extend(["--body", body_with_header])
    if args.json:
        cmd.append("--json")
    return cmd


# ------------------------------------------------------------------
# Main logic
# ------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generic Safe Kanban Task Submitter via Project Registry",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--project", required=True,
                        help="Project name as registered in config/projects.yaml")
    parser.add_argument("--task-key", required=True,
                        help="Task key (e.g. BJ-0017A). Allowed: [A-Za-z0-9._-]+")
    parser.add_argument("--title", required=True, help="Task title")
    parser.add_argument("--body-file", required=True,
                        help="Path to file containing task body (markdown)")
    parser.add_argument("--assignee", required=False, help="Assignee profile name (falls back to project's default_assignee)")
    parser.add_argument("--priority", type=int, default=None)
    parser.add_argument("--max-runtime", default=None,
                        help="Max runtime (e.g. 2h, 30m)")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help=f"Path to projects.yaml (default: {DEFAULT_CONFIG})")
    parser.add_argument("--allow-non-main", action="store_true",
                        help="Allow creating from non-default branch")
    parser.add_argument("--reuse-existing-worktree", action="store_true",
                        help="Reuse an existing worktree instead of failing")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without making changes")
    parser.add_argument("--json", action="store_true",
                        help="Pass --json to hermes kanban create")

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Step 1: Load project registry
    # ------------------------------------------------------------------
    config_path = Path(args.config).resolve()
    print(f"Loading project registry: {config_path}")
    projects = load_project_registry(config_path)
    # ------------------------------------------------------------------
    # Step 2: Validate project exists in registry
    # ------------------------------------------------------------------
    project = get_project(projects, args.project)

    # Step 2b: Resolve assignee — explicit override or project's default
    if args.assignee:
        resolved_assignee = args.assignee
    else:
        resolved_assignee = project.get("default_assignee")
        if not resolved_assignee:
            print("ERROR: No --assignee given and project has no default_assignee",
                  file=sys.stderr)
            sys.exit(1)
        print(f"Assignee not provided — using project's default: {resolved_assignee}")
    args.assignee = resolved_assignee

    # ------------------------------------------------------------------
    # Step 3: Resolve repo root
    # ------------------------------------------------------------------
    repo_root = resolve_repo_root(project, config_path)
    print(f"Using repo root: {repo_root}")
    validate_repo_exists(repo_root)
    validate_is_git_repo(repo_root)

    # ------------------------------------------------------------------
    # Step 4: Validate task key
    # ------------------------------------------------------------------
    validate_task_key(args.task_key)

    # ------------------------------------------------------------------
    # Step 5: Verify main repo is clean
    # ------------------------------------------------------------------
    print("\nChecking main repo is clean...")
    validate_repo_clean(repo_root)

    # ------------------------------------------------------------------
    # Step 6: Verify on correct branch
    # ------------------------------------------------------------------
    default_branch = project["default_branch"]
    print(f"Checking current branch (expecting '{default_branch}')...")
    validate_current_branch(repo_root, default_branch, args.allow_non_main)

    # ------------------------------------------------------------------
    # Step 7: Read task body
    # ------------------------------------------------------------------
    body_path = Path(args.body_file).resolve()
    validate_body_file(body_path)
    original_body = body_path.read_text()

    # ------------------------------------------------------------------
    # Step 8: Compute paths
    # ------------------------------------------------------------------
    wt_path = worktree_path_for(repo_root, args.task_key)
    branch = f"{project['branch_prefix']}{args.task_key}"
    artifact_root = Path(project["artifact_root"])
    ap = artifact_path_for(project, args.task_key)
    wt_exists = wt_path.exists()

    print(f"\nPlanned paths:")
    print(f"  Project:       {args.project}")
    print(f"  Repo:          {repo_root}")
    print(f"  Worktree:      {wt_path}")
    print(f"  Branch:        {branch}")
    print(f"  Artifact dir:  {ap}")

    # ------------------------------------------------------------------
    # Step 9: Check worktree collision
    # ------------------------------------------------------------------
    if wt_exists and not args.reuse_existing_worktree:
        print(f"ERROR: Worktree already exists: {wt_path}", file=sys.stderr)
        print("Pass --reuse-existing-worktree to reuse it.", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 10: Build body with governance header
    # ------------------------------------------------------------------
    body_with_header = GOVERNANCE_HEADER.format(
        worktree_path=wt_path,
        repo=str(repo_root),
        artifact_root=str(artifact_root),
    ) + "\n\n" + original_body

    # ------------------------------------------------------------------
    # Step 11: Dry run
    # ------------------------------------------------------------------
    if args.dry_run:
        print("\n=== DRY RUN — no changes made ===")
        print(f"Project:    {args.project}")
        print(f"Task key:   {args.task_key}")
        print(f"Title:      {args.title}")
        print(f"Assignee:   {args.assignee}")
        print(f"Worktree:   {wt_path} ({'exists' if wt_exists else 'new'})")
        print(f"Branch:     {branch}")
        print(f"Artifact:   {ap}")
        print(f"Body file:  {args.body_file}")
        print(f"Config:    {config_path}")
        if not wt_exists:
            print(f"\nWould run:")
            print(f"  git worktree add -b {branch} {wt_path} {default_branch} "
                  f"(from {repo_root})")
        print(f"\nWould call:")
        print(f"  hermes kanban create ... --workspace dir:{wt_path}")
        print(f"\nBody with governance header:\n")
        print(body_with_header)
        return

    # ------------------------------------------------------------------
    # Step 12: Create artifact folder
    # ------------------------------------------------------------------
    ap = create_artifact_folder(artifact_root, args.task_key)
    print(f"\nCreated artifact folder: {ap}")

    # ------------------------------------------------------------------
    # Step 13: Create worktree
    # ------------------------------------------------------------------
    if not wt_exists:
        print(f"\nCreating worktree: {wt_path}")
        run("git", "-C", str(repo_root), "worktree", "add",
            "-b", branch, str(wt_path), default_branch)
    else:
        print(f"\nReusing existing worktree: {wt_path}")

    # ------------------------------------------------------------------
    # Step 14: Verify worktree
    # ------------------------------------------------------------------
    print(f"\nVerifying worktree at {wt_path}...")
    verify_worktree(wt_path, branch)

    # ------------------------------------------------------------------
    # Step 15: Create Hermes Kanban task
    # ------------------------------------------------------------------
    print("\nCreating Hermes Kanban task...")
    cmd = build_hermes_command(args, body_with_header, wt_path)

    print(f"\nRunning: {' '.join(cmd)}")
    try:
        result = run(*cmd, check=False)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        if result.returncode != 0:
            print(f"WARNING: hermes kanban create returned {result.returncode}",
                  file=sys.stderr)
    except FileNotFoundError:
        print("ERROR: 'hermes' command not found in PATH", file=sys.stderr)
        print("Task was NOT created. Worktree and artifact folder exist.",
              file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 16: Print summary
    # ------------------------------------------------------------------
    print("\n=== Summary ===")
    print(f"Project:     {args.project}")
    print(f"Repo:        {repo_root}")
    print(f"Task key:    {args.task_key}")
    print(f"Worktree:    {wt_path}")
    print(f"Branch:      {branch}")
    print(f"Artifact:   {ap}")
    print(f"Config:     {config_path}")
    print("\nNext steps:")
    print(f"  1. cd {wt_path}")
    print(f"  2. Implement your changes")
    print(f"  3. Write artifacts to {ap}")
    print(f"  4. Create PR against {default_branch} when ready")
    print(f"  5. After PR merges, clean up worktree:")
    print(f"       git worktree remove {wt_path}")
    print(f"       git branch -d {branch}")


if __name__ == "__main__":
    main()
