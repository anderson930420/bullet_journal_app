#!/usr/bin/env python3
"""
kanban_pr_handoff.py — Generic PR handoff helper for Hermes Kanban.

Prepares a completed worktree for human review by validating the workspace,
showing the diff, staging and committing changes, pushing the task branch,
and creating a GitHub PR.

Safety properties:
- Never merges a PR
- Never marks a Hermes task done
- Never self-approves
- Fails if run from the main repo
- Fails without explicit --confirm for real actions
- Dry-run mode never makes persistent changes

Usage:
    python3 scripts/kanban_pr_handoff.py \\
        --project bullet-journal \\
        --task-key BJ-0010R \\
        --commit-message "tooling: add generic kanban PR handoff helper" \\
        --title "tooling: add generic kanban PR handoff helper" \\
        --body-file /home/ubuntu/.hermes/task-artifacts/BJ-0010R/completion_report.md \\
        --dry-run

Exit codes:
    0  — success (dry-run printed plan, or real actions completed)
    1  — check failed (see error message)
    2  — internal error (missing config, bad args, etc.)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULT_CONFIG_PATH = "config/projects.yaml"


def run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    """Run a command, return (exit_code, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 2, "", "command timed out"
    except Exception as e:
        return 2, "", str(e)


def load_config(config_path: str) -> dict:
    """Load and parse config/projects.yaml."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config file not found: {config_path}")
    import yaml
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("projects", {})


def resolve_paths(config_path: str, project: str, task_key: str) -> dict:
    """Resolve repo, worktree, branch, artifact_dir from project registry."""
    projects = load_config(config_path)
    if project not in projects:
        raise ValueError(f"Project {project!r} not found in {config_path}")
    p = projects[project]
    repo = p["repo"]
    default_branch = p.get("default_branch", "main")
    artifact_root = p.get("artifact_root", "/home/ubuntu/.hermes/task-artifacts")
    branch_prefix = p.get("branch_prefix", "worktree/")

    worktree = os.path.join(repo, ".worktrees", task_key)
    branch = branch_prefix + task_key
    artifact_dir = os.path.join(artifact_root, task_key)

    return {
        "repo": repo,
        "worktree": worktree,
        "branch": branch,
        "artifact_dir": artifact_dir,
        "default_branch": default_branch,
        "remote": "origin",
    }


def check_gh_available() -> bool:
    """Check if gh CLI is available."""
    rc, _, _ = run(["gh", "--version"])
    return rc == 0


def gh_pr_create(
    repo: str,
    branch: str,
    base: str,
    title: str,
    body: str,
) -> tuple[int, str, str]:
    """Create a PR via gh CLI. Returns (exit_code, stdout, pr_url_or_error)."""
    # Extract owner/repo from repo path
    owner_repo = os.path.basename(repo)
    rc, remote_url, err = run(["git", "remote", "get-url", "origin"], cwd=repo)
    if rc != 0:
        return rc, "", f"Could not get origin URL: {err}"
    # remote_url might be git@github.com:owner/repo.git or https://github.com/owner/repo.git
    remote_url = remote_url.strip()
    if "github.com" in remote_url:
        # Extract owner/repo from URL
        parts = remote_url.replace(".git", "").replace(":", "/").split("/")
        owner_repo = "/".join(parts[-2:])

    cmd = [
        "gh", "pr", "create",
        "--repo", owner_repo,
        "--base", base,
        "--head", branch,
        "--title", title,
        "--body", body,
    ]
    rc, stdout, stderr = run(cmd)
    if rc == 0:
        # gh pr create outputs the PR URL to stdout
        pr_url = stdout.strip()
        return rc, pr_url, ""
    else:
        return rc, "", stderr.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes Kanban PR handoff helper — safe, human-review-first.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Required
    parser.add_argument("--project", required=True, help="Project name from config/projects.yaml")
    parser.add_argument("--task-key", required=True, help="Task key (e.g. BJ-0010R)")
    parser.add_argument("--commit-message", required=True, help="Git commit message")
    parser.add_argument("--title", required=True, help="PR title")
    # Optional
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to projects.yaml")
    parser.add_argument("--body-file", help="Path to PR body text file")
    parser.add_argument("--body", help="PR body text (overrides --body-file)")
    parser.add_argument("--base", help="Base branch for PR (default: project default_branch)")
    parser.add_argument("--remote", default="origin", help="Git remote name (default: origin)")
    parser.add_argument("--artifact-dir", help="Override artifact directory")
    parser.add_argument("--manifest", help="Override path to artifact_manifest.json")
    parser.add_argument("--branch", help="Override branch name")
    parser.add_argument("--worktree", help="Override worktree path")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without making changes")
    parser.add_argument("--confirm", action="store_true", help="Confirm real action (required for real runs)")
    parser.add_argument("--skip-pr", action="store_true", help="Skip PR creation")
    parser.add_argument("--json", action="store_true", help="Output JSON with pr_url and commit")
    args = parser.parse_args()

    # --- Validate required non-empty args ---
    if not args.commit_message.strip():
        print("ERROR: --commit-message cannot be empty", file=sys.stderr)
        return 2
    if not args.title.strip():
        print("ERROR: --title cannot be empty", file=sys.stderr)
        return 2

    # --- Resolve config path ---
    if os.path.isabs(args.config):
        config_path = args.config
    else:
        rc, git_root, _ = run(["git", "rev-parse", "--show-toplevel"])
        if rc == 0 and os.path.exists(os.path.join(git_root, args.config)):
            config_path = os.path.join(git_root, args.config)
        else:
            script_dir = Path(__file__).parent.resolve()
            config_path = str(script_dir / args.config)

    # --- Load config ---
    try:
        projects = load_config(config_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERROR: failed to parse config: {e}", file=sys.stderr)
        return 2

    # --- Validate project ---
    if args.project not in projects:
        print(f"ERROR: project {args.project!r} not found in {config_path}", file=sys.stderr)
        print(f"  available projects: {', '.join(sorted(projects.keys()))}", file=sys.stderr)
        return 2

    proj = projects[args.project]

    # --- Resolve paths ---
    try:
        paths = resolve_paths(config_path, args.project, args.task_key)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    repo = proj["repo"]
    if not os.path.isabs(repo):
        script_dir = Path(__file__).parent.resolve()
        repo = str(script_dir / repo)

    expected_worktree = args.worktree or paths["worktree"]
    expected_branch = args.branch or paths["branch"]
    expected_remote = args.remote or "origin"
    default_branch = args.base or paths["default_branch"]
    artifact_dir = args.artifact_dir or paths["artifact_dir"]
    manifest_path = args.manifest or os.path.join(artifact_dir, "artifact_manifest.json")

    # --- Check running from expected worktree ---
    rc, actual_git_root, err = run(["git", "rev-parse", "--show-toplevel"])
    if rc != 0:
        print(f"ERROR: not inside a git repository: {err}", file=sys.stderr)
        return 2

    if os.path.normpath(actual_git_root) != os.path.normpath(expected_worktree):
        print(
            f"ERROR: Wrong worktree: expected {expected_worktree!r} but running in {actual_git_root!r}",
            file=sys.stderr,
        )
        return 1

    # --- Check git root is not the main repo root ---
    main_repo_root = os.path.normpath(repo)
    if os.path.normpath(actual_git_root) == main_repo_root:
        print(
            f"ERROR: Worker is running in main repo {main_repo_root!r} — must use a worktree",
            file=sys.stderr,
        )
        return 1

    # --- Check current branch ---
    rc, actual_branch, err = run(["git", "branch", "--show-current"])
    if rc != 0:
        print(f"ERROR: failed to get current branch: {err}", file=sys.stderr)
        return 2

    if actual_branch != expected_branch:
        print(
            f"ERROR: Wrong branch: expected {expected_branch!r} but on {actual_branch!r}",
            file=sys.stderr,
        )
        return 1

    # --- Check main repo is clean ---
    rc, main_status, _ = run(["git", "status", "--porcelain"], cwd=repo)
    if rc == 0 and main_status.strip():
        print(
            f"ERROR: Main repo has uncommitted/untracked changes — must be clean:\n  {main_status}",
            file=sys.stderr,
        )
        return 1

    # --- Check for repo changes in worktree ---
    rc, worktree_status, _ = run(["git", "status", "--porcelain"], cwd=actual_git_root)
    if rc != 0:
        print(f"ERROR: Could not read worktree git status: {worktree_status}", file=sys.stderr)
        return 2

    # --- Git status output ---
    status_short = ""
    rc_s, status_short, _ = run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=actual_git_root,
    )
    if rc_s == 0:
        status_short_output = status_short
    else:
        status_short_output = "(unable to determine)"

    # --- Git diff --stat ---
    rc_d, diff_stat, _ = run(["git", "diff", "--stat"], cwd=actual_git_root)
    diff_stat_output = diff_stat if rc_d == 0 else "(unable to determine)"

    # --- Check if there are changes to commit ---
    has_changes = worktree_status.strip() != ""

    # --- Resolve PR body ---
    pr_body = ""
    if args.body:
        pr_body = args.body
    elif args.body_file:
        if not os.path.exists(args.body_file):
            print(f"ERROR: body file not found: {args.body_file}", file=sys.stderr)
            return 2
        with open(args.body_file, "r") as f:
            pr_body = f.read()
    else:
        pr_body = f"Task {args.task_key} completed. See artifact folder for details."

    # --- DRY RUN MODE ---
    if args.dry_run:
        print("=== DRY RUN — no changes made ===")
        print(f"  project:       {args.project}")
        print(f"  task_key:      {args.task_key}")
        print(f"  repo:         {repo}")
        print(f"  worktree:     {actual_git_root}")
        print(f"  branch:       {actual_branch}")
        print(f"  base:         {default_branch}")
        print(f"  remote:       {expected_remote}")
        print(f"  artifact_dir: {artifact_dir}")
        print(f"  manifest:     {manifest_path}")
        print()
        print("git status --short --untracked-files=all:")
        print(status_short_output or "(no output — clean)")
        print()
        print("git diff --stat:")
        print(diff_stat_output or "(no output — clean)")
        print()
        if not has_changes:
            print("WARNING: no repo changes to commit")
        else:
            print("Would stage and commit:")
            print(f"  git add .")
            print(f"  git commit -m {args.commit_message!r}")
            print(f"  git push -u {expected_remote} {actual_branch}")
            if not args.skip_pr and check_gh_available():
                print(f"  gh pr create --base {default_branch} --head {actual_branch} --title {args.title!r}")
                print(f"  (write <artifact-dir>/pr_info.json)")
            elif not args.skip_pr:
                print(f"  gh not available — would print manual PR instructions")
        print()
        print("Would NOT (dry-run):")
        print("  - stage changes")
        print("  - commit")
        print("  - push")
        print("  - create PR")
        print("  - write pr_info.json")
        print("  - modify artifact_manifest.json")
        return 0

    # --- REAL RUN MODE (dry-run is off) ---
    if not args.confirm:
        print("ERROR: --confirm is required for real actions", file=sys.stderr)
        print("  Use --dry-run to see the plan without making changes.", file=sys.stderr)
        return 1

    if not has_changes:
        print("ERROR: no repo changes to commit", file=sys.stderr)
        return 1

    # --- Stage all changes ---
    print("Staging all changes...")
    rc, stage_out, stage_err = run(["git", "add", "."], cwd=actual_git_root)
    if rc != 0:
        print(f"ERROR: git add failed: {stage_err}", file=sys.stderr)
        return 1

    # --- Show staged status ---
    rc, staged_status, _ = run(
        ["git", "status", "--short"],
        cwd=actual_git_root,
    )
    print("Staged status:")
    print(staged_status or "(nothing staged)")

    # --- Commit ---
    print(f"Committing: {args.commit_message!r}")
    rc, commit_out, commit_err = run(
        ["git", "commit", "-m", args.commit_message],
        cwd=actual_git_root,
    )
    if rc != 0:
        print(f"ERROR: git commit failed: {commit_err}", file=sys.stderr)
        return 1

    commit_sha = ""
    rc_c, commit_sha, _ = run(
        ["git", "rev-parse", "HEAD"],
        cwd=actual_git_root,
    )
    if rc_c != 0:
        commit_sha = "(unknown)"

    # --- Push ---
    print(f"Pushing: git push -u {expected_remote} {actual_branch}")
    rc, push_out, push_err = run(
        ["git", "push", "-u", expected_remote, actual_branch],
        cwd=actual_git_root,
    )
    if rc != 0:
        print(f"ERROR: git push failed: {push_err}", file=sys.stderr)
        return 1

    pr_url = ""
    pr_created = False
    pr_info_path = None

    # --- Create PR or handle --skip-pr ---
    if args.skip_pr:
        print("--skip-pr specified — skipping PR creation.")
        print()
        print("Manual PR creation instructions:")
        print(f"  gh pr create --base {default_branch} --head {actual_branch} \\")
        print(f"    --title {args.title!r}")
        if pr_body:
            print(f"    --body '<filepath>'")
            print(f"    # where body is the contents of the completion report")
        print()
        print("pr_info.json will NOT be written when --skip-pr is used.")
        print("(pr_info.json requires a successful PR creation to record the PR URL)")
    elif check_gh_available():
        print(f"Creating PR: {args.title!r}")
        rc_pr, pr_url, pr_err = gh_pr_create(
            repo=repo,
            branch=actual_branch,
            base=default_branch,
            title=args.title,
            body=pr_body,
        )
        if rc_pr == 0:
            print(f"PR created: {pr_url}")
            pr_created = True
        else:
            print(f"ERROR: gh pr create failed: {pr_err}", file=sys.stderr)
            print()
            print("Manual PR creation:")
            print(f"  gh pr create --base {default_branch} --head {actual_branch} \\")
            print(f"    --title {args.title!r}")
            return 1
    else:
        print("gh CLI not available — cannot create PR.", file=sys.stderr)
        print()
        print("Manual PR creation:")
        print(f"  gh pr create --base {default_branch} --head {actual_branch} \\")
        print(f"    --title {args.title!r}")
        return 1

    # --- Write pr_info.json ONLY after successful PR creation ---
    if pr_created and pr_url:
        os.makedirs(artifact_dir, exist_ok=True)
        pr_info = {
            "project": args.project,
            "task_key": args.task_key,
            "branch": actual_branch,
            "base": default_branch,
            "remote": expected_remote,
            "commit": commit_sha.strip(),
            "pr_url": pr_url,
            "created_by": "kanban_pr_handoff.py",
        }
        pr_info_path = os.path.join(artifact_dir, "pr_info.json")
        with open(pr_info_path, "w") as f:
            json.dump(pr_info, f, indent=2)
        print(f"Written: {pr_info_path}")

        # --- Update artifact_manifest.json if it exists ---
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                if "pr_url" in manifest or "status" in manifest:
                    manifest["pr_url"] = pr_url
                    if "status" in manifest and manifest["status"] not in (
                        "accepted", "rejected", "merged", "done"
                    ):
                        manifest["status"] = "waiting_for_human_review"
                    with open(manifest_path, "w") as f:
                        json.dump(manifest, f, indent=2)
                    print(f"Updated: {manifest_path}")
            except Exception as e:
                print(f"WARNING: could not update manifest: {e}", file=sys.stderr)

    # --- JSON output mode ---
    if args.json:
        output = {
            "project": args.project,
            "task_key": args.task_key,
            "branch": actual_branch,
            "base": default_branch,
            "remote": expected_remote,
            "commit": commit_sha.strip(),
            "pr_url": pr_url,
            "pr_info_path": pr_info_path,
            "manifest_updated": os.path.exists(manifest_path),
        }
        print()
        print(json.dumps(output, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
