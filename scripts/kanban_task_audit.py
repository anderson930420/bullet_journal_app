#!/usr/bin/env python3
"""
kanban_task_audit.py — Read-only lifecycle audit command for Hermes/Symphony-style workflow tasks.

Audits a task for internal consistency across:
  - artifact directory completeness
  - artifact_manifest.json validation
  - git worktree / branch state
  - Hermes Kanban task state
  - PR metadata and merge status
  - merged commit verification
  - forbidden / destructive command absence

Usage:
    python3 scripts/kanban_task_audit.py --project bullet-journal --task-key BJ-0022 --task-id t_5cfe5f09
    python3 scripts/kanban_task_audit.py --project bullet-journal --task-key BJ-0022 --task-id t_5cfe5f09 --phase post-cleanup --merged-commit c3d6476 --pr-number 15
    python3 scripts/kanban_task_audit.py --project bullet-journal --task-key BJ-0022 --task-id t_5cfe5f09 --phase post-cleanup --merged-commit c3d6476 --pr-number 15 --json

Exit codes:
    0 — no FAIL checks
    1 — at least one FAIL check
    2 — usage / configuration error
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = "config/projects.yaml"
ARTIFACT_ROOT_DEFAULT = "/home/ubuntu/.hermes/task-artifacts"
SCHEMA_VERSION = "hermes-task-artifacts/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str], cwd: Optional[str] = None, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command, return (exit_code, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 2, "", "command timed out"
    except Exception as e:
        return 2, "", str(e)


def load_yaml_simple(stream) -> dict:
    """Minimal YAML parser for projects.yaml (stdib-only fallback)."""
    data = {}
    current_project = None
    for line in stream.readlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("projects:"):
            continue
        # Depth-1 project name line: "  project-name:" with nothing after the colon
        # (or only whitespace after colon). This is a project block header.
        stripped = line.strip()
        if stripped.endswith(":") and not any(stripped.startswith(pre) for pre in (" ", "\t")):
            # top-level project name like "bullet-journal:"
            project_name = stripped.rstrip(":")
            if project_name:
                current_project = project_name
        elif line.startswith("  ") and ":" in line:
            # key: value under current project
            key = line.strip().split(":")[0]
            rest = line.strip().split(":", 1)[1].strip()
            if rest and current_project:
                data.setdefault("projects", {}).setdefault(current_project, {})[key] = rest
        else:
            # Bare project name (no leading spaces), e.g. "bullet-journal:"
            project_name = line.strip().rstrip(":")
            if project_name and not any(c in project_name for c in (" ", "\t")):
                current_project = project_name
    return data


def load_project_config(config_path: str, project: str) -> Optional[dict]:
    """Load project registry and return project config or None."""
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r") as f:
        data = load_yaml_simple(f)
    projects = data.get("projects", {})
    return projects.get(project)


def resolve_artifact_dir(config_path: str, project: str, task_key: str) -> Optional[str]:
    """Resolve artifact_dir from project config."""
    proj = load_project_config(config_path, project)
    if not proj:
        return None
    artifact_root = proj.get("artifact_root", ARTIFACT_ROOT_DEFAULT)
    return os.path.join(artifact_root, task_key)


def resolve_worktree_branch(config_path: str, project: str, task_key: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve worktree path and branch name from project config."""
    proj = load_project_config(config_path, project)
    if not proj:
        return None, None
    repo = proj.get("repo", "")
    branch_prefix = proj.get("branch_prefix", "worktree/")
    worktree = os.path.join(repo, ".worktrees", task_key)
    branch = branch_prefix + task_key
    return worktree, branch


# ---------------------------------------------------------------------------
# Artifact directory checks
# ---------------------------------------------------------------------------

def check_artifact_dir(artifact_dir: str, phase: str) -> list[dict]:
    """Check artifact directory structure."""
    checks = []
    if not artifact_dir:
        checks.append({
            "name": "artifact_dir_provided",
            "status": "FAIL",
            "message": "No artifact directory provided",
        })
        return checks

    exists = os.path.isdir(artifact_dir)
    checks.append({
        "name": "artifact_dir_exists",
        "status": "PASS" if exists else "FAIL",
        "message": f"Artifact dir {'exists' if exists else 'not found'}: {artifact_dir}",
    })

    if not exists:
        return checks

    # Required files for all phases
    required_all = ["completion_report.md", "git_status.txt", "worktree_info.txt", "artifact_manifest.json"]
    for fname in required_all:
        fpath = os.path.join(artifact_dir, fname)
        present = os.path.isfile(fpath)
        checks.append({
            "name": f"artifact_file_{fname}",
            "status": "PASS" if present else "FAIL",
            "message": f"{fname} {'present' if present else 'missing'} in {artifact_dir}",
        })

    # decision.md only for post-cleanup/accepted
    if phase in ("post-cleanup",):
        dpath = os.path.join(artifact_dir, "decision.md")
        present = os.path.isfile(dpath)
        checks.append({
            "name": "decision_md_post_cleanup",
            "status": "PASS" if present else "FAIL",
            "message": f"decision.md {'present' if present else 'missing'} (post-cleanup phase)",
        })

    # pr_info.json when we have a PR
    pr_info_path = os.path.join(artifact_dir, "pr_info.json")
    has_pr_info = os.path.isfile(pr_info_path)
    checks.append({
        "name": "pr_info_json_present",
        "status": "WARN" if not has_pr_info else "PASS",
        "message": f"pr_info.json {'present' if has_pr_info else 'not found'} in {artifact_dir}",
    })

    return checks


# ---------------------------------------------------------------------------
# Artifact manifest validation
# ---------------------------------------------------------------------------

def validate_manifest_file(manifest_path: str) -> tuple[bool, list[str]]:
    """Validate artifact_manifest.json. Returns (valid, errors)."""
    errors = []
    if not os.path.exists(manifest_path):
        return False, [f"Manifest file not found: {manifest_path}"]

    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    # Required fields
    required_fields = [
        "schema_version", "project", "task_key", "task_id", "status",
        "recommendation", "repo", "worktree", "branch", "artifact_dir",
        "requires_pr", "pr_url", "merged_commit", "changed_files", "checks", "artifacts",
    ]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"Invalid schema_version: got {manifest.get('schema_version')!r}, expected {SCHEMA_VERSION!r}")

    allowed_status = {"ready", "running", "waiting_for_human_review", "accepted", "rejected", "merged", "done", "unknown"}
    if manifest.get("status") not in allowed_status:
        errors.append(f"Invalid status: {manifest.get('status')!r}")

    allowed_rec = {"accept", "revise", "reject", "unknown"}
    if manifest.get("recommendation") not in allowed_rec:
        errors.append(f"Invalid recommendation: {manifest.get('recommendation')!r}")

    if not isinstance(manifest.get("requires_pr"), bool):
        errors.append(f"requires_pr must be bool, got {type(manifest.get('requires_pr'))}")

    if not isinstance(manifest.get("changed_files"), list):
        errors.append(f"changed_files must be list")

    # checks validation
    if not isinstance(manifest.get("checks"), list):
        errors.append(f"checks must be list")
    else:
        for i, check in enumerate(manifest.get("checks", [])):
            if not isinstance(check, dict):
                errors.append(f"checks[{i}] must be object")
                continue
            if "name" not in check:
                errors.append(f"checks[{i}] missing name")
            if "result" not in check:
                errors.append(f"checks[{i}] missing result")

    # artifacts validation
    if not isinstance(manifest.get("artifacts"), list):
        errors.append(f"artifacts must be list")
    else:
        for i, artifact in enumerate(manifest.get("artifacts", [])):
            if not isinstance(artifact, dict):
                errors.append(f"artifacts[{i}] must be object")
                continue
            if "path" not in artifact:
                errors.append(f"artifacts[{i}] missing path")
            elif os.path.isabs(artifact.get("path", "")):
                if "exists" in artifact:
                    actual = os.path.exists(artifact["path"])
                    declared = bool(artifact["exists"])
                    if actual != declared:
                        errors.append(
                            f"artifacts[{i}].exists mismatch: declared={declared}, actual={'exists' if actual else 'not found'}"
                        )

    return len(errors) == 0, errors


def check_manifest(artifact_dir: str) -> list[dict]:
    """Validate artifact_manifest.json."""
    checks = []
    manifest_path = os.path.join(artifact_dir, "artifact_manifest.json")

    if not os.path.isfile(manifest_path):
        checks.append({
            "name": "manifest_validation",
            "status": "FAIL",
            "message": f"manifest not found at {manifest_path}",
        })
        return checks

    valid, errors = validate_manifest_file(manifest_path)
    if valid:
        checks.append({
            "name": "manifest_validation",
            "status": "PASS",
            "message": "artifact_manifest.json is valid",
        })
    else:
        for err in errors:
            checks.append({
                "name": "manifest_validation",
                "status": "FAIL",
                "message": err,
            })

    return checks


# ---------------------------------------------------------------------------
# Git worktree / branch state
# ---------------------------------------------------------------------------

def check_worktree_state(worktree: Optional[str], branch: Optional[str], phase: str, repo: str) -> list[dict]:
    """Check git worktree and branch state."""
    checks = []

    if not worktree:
        checks.append({
            "name": "worktree_path_provided",
            "status": "WARN",
            "message": "No worktree path provided — skipping worktree checks",
        })
        return checks

    if phase == "review":
        # For in-review: worktree should exist
        exists = os.path.isdir(worktree)
        checks.append({
            "name": "worktree_exists_review",
            "status": "PASS" if exists else "FAIL",
            "message": f"Worktree {'exists' if exists else 'not found'}: {worktree}",
        })

        # Branch should exist
        if exists and repo:
            rc, out, _ = run(["git", "branch", "--list", branch], cwd=repo)
            branch_exists = rc == 0 and out.strip() != ""
            checks.append({
                "name": "branch_exists_review",
                "status": "PASS" if branch_exists else "FAIL",
                "message": f"Branch '{branch}' {'exists' if branch_exists else 'not found'} in {repo}",
            })
        else:
            checks.append({
                "name": "branch_exists_review",
                "status": "WARN",
                "message": "Skipped branch check (repo not available or worktree missing)",
            })

    elif phase == "post-cleanup":
        # For post-cleanup: worktree should be removed, branch deleted
        exists = os.path.isdir(worktree)
        checks.append({
            "name": "worktree_removed_post_cleanup",
            "status": "PASS" if not exists else "FAIL",
            "message": f"Worktree {'removed' if not exists else 'STILL PRESENT'}: {worktree}",
        })

        if repo:
            rc, out, _ = run(["git", "branch", "--list", branch], cwd=repo)
            branch_gone = rc != 0 or out.strip() == ""
            checks.append({
                "name": "branch_deleted_post_cleanup",
                "status": "PASS" if branch_gone else "FAIL",
                "message": f"Branch '{branch}' {'deleted' if branch_gone else 'STILL PRESENT'} in {repo}",
            })
        else:
            checks.append({
                "name": "branch_deleted_post_cleanup",
                "status": "WARN",
                "message": "Skipped branch delete check (repo not available)",
            })

    elif phase == "post-handoff":
        # For post-handoff: worktree and branch should still exist
        # (handoff means PR created but not yet merged/cleaned up)
        exists = os.path.isdir(worktree)
        checks.append({
            "name": "worktree_exists_post_handoff",
            "status": "PASS" if exists else "FAIL",
            "message": f"Worktree {'exists' if exists else 'not found'}: {worktree}",
        })

        if exists and repo:
            rc, out, _ = run(["git", "branch", "--list", branch], cwd=repo)
            branch_exists = rc == 0 and out.strip() != ""
            checks.append({
                "name": "branch_exists_post_handoff",
                "status": "PASS" if branch_exists else "FAIL",
                "message": f"Branch '{branch}' {'exists' if branch_exists else 'not found'} in {repo}",
            })
        else:
            checks.append({
                "name": "branch_exists_post_handoff",
                "status": "WARN",
                "message": "Skipped branch check (repo not available or worktree missing)",
            })

    else:  # auto
        # Ambiguous — be lenient
        checks.append({
            "name": "worktree_phase_auto",
            "status": "WARN",
            "message": f"Phase is 'auto' — worktree state at {worktree} is ambiguous; skipping enforcement",
        })

    return checks


# ---------------------------------------------------------------------------
# Hermes Kanban task state
# ---------------------------------------------------------------------------

def check_hermes_task(task_id: str, phase: str) -> list[dict]:
    """Check Hermes Kanban task state."""
    checks = []

    if not task_id:
        checks.append({
            "name": "hermes_task_id_provided",
            "status": "WARN",
            "message": "No task_id provided — skipping Hermes task checks",
        })
        return checks

    rc, stdout, stderr = run(["hermes", "kanban", "show", task_id], timeout=15)

    if rc != 0:
        checks.append({
            "name": "hermes_task_state",
            "status": "WARN",
            "message": f"hermes kanban show failed (exit {rc}): {stderr.strip() or stdout.strip()}",
        })
        return checks

    # Parse output to find status and blocked_reason
    output = stdout
    status = None
    blocked_reason = None
    outcome = None

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("status:"):
            status = line.split(":", 1)[1].strip()
        if line.startswith("blocked_reason:"):
            blocked_reason = line.split(":", 1)[1].strip()
        if line.startswith("outcome:"):
            outcome = line.split(":", 1)[1].strip()

    if phase == "review":
        expected_status = "blocked"
        if status == expected_status:
            checks.append({
                "name": "hermes_status_review",
                "status": "PASS",
                "message": f"Task status is '{status}' (expected blocked for in-review)",
            })
        else:
            checks.append({
                "name": "hermes_status_review",
                "status": "FAIL",
                "message": f"Task status is '{status}', expected 'blocked' for in-review phase",
            })

        if blocked_reason and "waiting_for_human_review" in blocked_reason:
            checks.append({
                "name": "hermes_blocked_reason_review",
                "status": "PASS",
                "message": f"Blocked reason includes 'waiting_for_human_review': {blocked_reason}",
            })
        elif status == "blocked":
            checks.append({
                "name": "hermes_blocked_reason_review",
                "status": "WARN",
                "message": f"Task is blocked but reason does not include 'waiting_for_human_review': {blocked_reason}",
            })
        else:
            checks.append({
                "name": "hermes_blocked_reason_review",
                "status": "WARN",
                "message": f"Task is not blocked (status={status}) — cannot verify blocked reason",
            })

    elif phase == "post-cleanup":
        expected_status = "done"
        if status == expected_status:
            checks.append({
                "name": "hermes_status_post_cleanup",
                "status": "PASS",
                "message": f"Task status is '{status}' (expected done for post-cleanup)",
            })
        else:
            checks.append({
                "name": "hermes_status_post_cleanup",
                "status": "FAIL",
                "message": f"Task status is '{status}', expected 'done' for post-cleanup phase",
            })

        if outcome:
            checks.append({
                "name": "hermes_outcome_set",
                "status": "PASS",
                "message": f"Task outcome is set: {outcome}",
            })
        else:
            checks.append({
                "name": "hermes_outcome_set",
                "status": "WARN",
                "message": "Task outcome is not set (may still be pending human action)",
            })

    elif phase == "post-handoff":
        # For post-handoff: task should still be in blocked/waiting_for_human_review state
        # (PR is created but not yet merged; worker must not self-complete)
        if status == "blocked":
            if blocked_reason and "waiting_for_human_review" in blocked_reason:
                checks.append({
                    "name": "hermes_status_post_handoff",
                    "status": "PASS",
                    "message": f"Task is blocked with 'waiting_for_human_review': {blocked_reason}",
                })
            else:
                checks.append({
                    "name": "hermes_status_post_handoff",
                    "status": "WARN",
                    "message": f"Task is blocked but reason does not include 'waiting_for_human_review': {blocked_reason}",
                })
        elif status == "done":
            checks.append({
                "name": "hermes_status_post_handoff",
                "status": "FAIL",
                "message": "Task status is 'done' but PR handoff has not been cleaned up — worker self-completed",
            })
        else:
            checks.append({
                "name": "hermes_status_post_handoff",
                "status": "WARN",
                "message": f"Task status is '{status}' — expected blocked for post-handoff phase",
            })
    else:  # auto
        checks.append({
            "name": "hermes_status_auto",
            "status": "WARN",
            "message": f"Phase is 'auto' — cannot infer expected Hermes state; current status={status}",
        })

    return checks


# ---------------------------------------------------------------------------
# PR metadata
# ---------------------------------------------------------------------------

def check_pr_metadata(pr_number: Optional[int], pr_url: Optional[str], artifact_dir: str) -> list[dict]:
    """Check PR metadata and merged status."""
    checks = []

    # Try to load pr_info.json
    pr_info_path = os.path.join(artifact_dir, "pr_info.json")
    pr_info = None
    if os.path.isfile(pr_info_path):
        try:
            with open(pr_info_path, "r") as f:
                pr_info = json.load(f)
        except json.JSONDecodeError:
            pass

    effective_url = pr_url or (pr_info.get("url") if pr_info else None)
    effective_number = pr_number or (pr_info.get("number") if pr_info else None)

    if not effective_url and not effective_number:
        checks.append({
            "name": "pr_url_provided",
            "status": "WARN",
            "message": "No PR URL or PR number provided — skipping PR checks",
        })
        return checks

    checks.append({
        "name": "pr_url_reported",
        "status": "PASS",
        "message": f"PR URL: {effective_url or f'pr_info.json (number={effective_number})'}",
    })

    # Check merged status via gh
    if effective_number is not None:
        gh_args = ["gh", "pr", "view", str(effective_number), "--json", "state,mergedAt,url"]
    elif effective_url:
        gh_args = ["gh", "pr", "view", effective_url, "--json", "state,mergedAt,url"]
    else:
        gh_args = []
    if gh_args:
        rc, stdout, stderr = run(gh_args, timeout=15)

    if rc != 0:
        checks.append({
            "name": "pr_gh_available",
            "status": "WARN",
            "message": f"gh pr view failed (exit {rc}): {stderr.strip() or stdout.strip()} — cannot verify merged status",
        })
        return checks

    try:
        data = json.loads(stdout)
        state = data.get("state", "")
        merged_at = data.get("mergedAt")
        url = data.get("url", effective_url)
        is_merged = state == "MERGED" or (merged_at is not None and merged_at != "")
        checks.append({
            "name": "pr_merged_status",
            "status": "PASS" if is_merged else "FAIL",
            "message": f"PR {effective_number}: state={state}, mergedAt={merged_at} (url={url})",
        })
    except (json.JSONDecodeError, KeyError) as e:
        checks.append({
            "name": "pr_merged_status_parse",
            "status": "WARN",
            "message": f"Could not parse gh pr view output: {e}",
        })

    return checks


# ---------------------------------------------------------------------------
# Merged commit
# ---------------------------------------------------------------------------

def check_merged_commit(merged_commit: Optional[str], base: str, repo: str) -> list[dict]:
    """Verify merged commit exists and is reachable from base branch."""
    checks = []

    if not merged_commit:
        checks.append({
            "name": "merged_commit_provided",
            "status": "WARN",
            "message": "No --merged-commit provided — skipping merged commit check",
        })
        return checks

    if not repo:
        checks.append({
            "name": "repo_provided",
            "status": "WARN",
            "message": "No repo path provided — skipping merged commit check",
        })
        return checks

    # Check commit exists
    rc1, out1, err1 = run(["git", "cat-file", "-t", merged_commit], cwd=repo, timeout=10)
    if rc1 != 0:
        checks.append({
            "name": "merged_commit_exists",
            "status": "FAIL",
            "message": f"Commit {merged_commit} not found in repo {repo}",
        })
        return checks

    checks.append({
        "name": "merged_commit_exists",
        "status": "PASS",
        "message": f"Merged commit {merged_commit} exists in repo",
    })

    # Check reachable from base
    rc2, out2, err2 = run(["git", "merge-base", "--is-ancestor", merged_commit, base], cwd=repo, timeout=10)
    is_ancestor = rc2 == 0
    checks.append({
        "name": "merged_commit_reachable_from_base",
        "status": "PASS" if is_ancestor else "FAIL",
        "message": f"Merged commit {merged_commit} {'is' if is_ancestor else 'is NOT'} reachable from {base}",
    })

    return checks


# ---------------------------------------------------------------------------
# BJ-0024-style lifecycle checks
# (no-PR manifest with dirty worktree, self-completion instead of blocked)
# ---------------------------------------------------------------------------

def check_lifecycle_compliance(
    artifact_dir: str,
    task_id: Optional[str],
    phase: str,
    worktree_path: Optional[str] = None,
) -> list[dict]:
    """Detect BJ-0024-style lifecycle violations.

    Checks:
    - actual Hermes task status 'done' when phase=review expects 'waiting_for_human_review'
    - no-PR manifest (requires_pr=false) with dirty worktree
    - no-PR manifest with non-empty changed_files
    - missing git_status.txt when worktree is dirty

    For dirty worktree detection, this function prefers real worktree git checks
    (when worktree_path is provided and exists) over git_status.txt fallback.
    """
    checks = []

    if not artifact_dir:
        checks.append({
            "name": "lifecycle_check_skipped",
            "status": "WARN",
            "message": "No artifact_dir provided — skipping lifecycle compliance checks",
        })
        return checks

    manifest_path = os.path.join(artifact_dir, "artifact_manifest.json")
    git_status_path = os.path.join(artifact_dir, "git_status.txt")

    # Load manifest if available
    manifest_requires_pr: Optional[bool] = None
    manifest_changed_files: list = []
    manifest_status: Optional[str] = None
    manifest_worktree: Optional[str] = None
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r") as f:
                m = json.load(f)
            manifest_requires_pr = m.get("requires_pr")
            manifest_changed_files = m.get("changed_files") or []
            manifest_status = m.get("status")
            manifest_worktree = m.get("worktree")
        except (json.JSONDecodeError, OSError):
            pass

    # Load git_status.txt if available
    git_status_content = ""
    if os.path.isfile(git_status_path):
        try:
            git_status_content = open(git_status_path).read()
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Check 1: actual Hermes task status 'done' when phase=review expects
    # 'waiting_for_human_review' — must use real hermes kanban show, not
    # just the manifest status field.
    # ------------------------------------------------------------------
    if phase == "review" and task_id:
        rc, stdout, stderr = run(["hermes", "kanban", "show", task_id], timeout=15)
        hermes_actual_status: Optional[str] = None
        if rc == 0:
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("status:"):
                    hermes_actual_status = line.split(":", 1)[1].strip()
                    break

        if hermes_actual_status == "done":
            checks.append({
                "name": "lifecycle_hermes_task_done_in_review_phase",
                "status": "FAIL",
                "message": (
                    "BJ-0024 pattern: actual Hermes task status is 'done' but review-phase "
                    "tasks must end in 'blocked / waiting_for_human_review'. "
                    f"Worker self-completed (Hermes status={hermes_actual_status})."
                ),
            })
        elif hermes_actual_status is None and rc != 0:
            checks.append({
                "name": "lifecycle_hermes_task_status_unknown",
                "status": "WARN",
                "message": f"Could not determine Hermes task status: {stderr.strip() or stdout.strip()}",
            })

    # ------------------------------------------------------------------
    # Check 1b: fallback to manifest status if we have no task_id but
    # manifest_status is 'done' — less reliable but still informative.
    # Only fires when task_id was not provided (otherwise Check 1 covers it).
    # ------------------------------------------------------------------
    if phase == "review" and not task_id and manifest_status == "done":
        checks.append({
            "name": "lifecycle_done_in_review_phase_manifest",
            "status": "FAIL",
            "message": (
                "BJ-0024 pattern: manifest status is 'done' but review-phase tasks "
                "must end in 'blocked / waiting_for_human_review'. "
                "(No task_id available — checked manifest only.)"
            ),
        })

    # ------------------------------------------------------------------
    # Check 2: no-PR manifest (requires_pr=false) with dirty worktree.
    # Use real worktree git checks when available; fall back to
    # git_status.txt content only when worktree no longer exists.
    # ------------------------------------------------------------------
    if manifest_requires_pr is False:
        is_dirty = False
        dirty_details = ""

        # Prefer real worktree git checks
        effective_worktree = worktree_path or manifest_worktree
        if effective_worktree and os.path.isdir(effective_worktree):
            rc1, status_out, _ = run(
                ["git", "status", "--short", "--untracked-files=all"],
                cwd=effective_worktree,
            )
            rc2, diff_out, _ = run(
                ["git", "diff", "--stat"],
                cwd=effective_worktree,
            )
            is_dirty = (rc1 == 0 and status_out.strip() != "") or (rc2 == 0 and diff_out.strip() != "")
            dirty_details = (
                f"git status output: {status_out.strip()!r}; "
                f"git diff output: {diff_out.strip()!r}"
            )
        else:
            # Fall back to git_status.txt content analysis
            status_lines = [l.strip() for l in git_status_content.strip().splitlines() if l.strip()]
            dirty_indicators = [l for l in status_lines if l and not l.startswith("#")]
            is_dirty = len(dirty_indicators) > 0
            dirty_details = f"git_status.txt dirty indicators: {dirty_indicators!r}"

        if is_dirty:
            checks.append({
                "name": "lifecycle_nopr_with_dirty_worktree",
                "status": "FAIL",
                "message": (
                    f"BJ-0024 pattern: requires_pr=false but worktree is dirty. "
                    f"{dirty_details} "
                    "Manifest must not claim requires_pr=false when repo has changes."
                ),
            })

    # ------------------------------------------------------------------
    # Check 3: no-PR manifest with non-empty changed_files
    # ------------------------------------------------------------------
    if manifest_requires_pr is False and manifest_changed_files:
        checks.append({
            "name": "lifecycle_nopr_with_changed_files",
            "status": "FAIL",
            "message": (
                f"BJ-0024 pattern: requires_pr=false but changed_files is non-empty: "
                f"{manifest_changed_files!r}. Manifest is inconsistent."
            ),
        })

    # ------------------------------------------------------------------
    # Check 4: missing or empty git_status.txt when worktree is dirty
    #
    # Special case: if the worktree exists and is genuinely clean (verified
    # via real git commands), accept human-readable clean-state text like
    # "(empty — worktree clean)" even if git_status.txt contains the literal
    # string "git status" (which makes it look template-like at first glance).
    # ------------------------------------------------------------------
    git_status_missing = not os.path.isfile(git_status_path)
    git_status_empty = not git_status_content.strip()

    # Check if git_status.txt contains explicit clean-state indicators
    # that are valid evidence even when the file looks "template-like"
    clean_indicators = [
        "(empty — worktree clean)",
        "(empty — no repo diff)",
        "worktree clean",
        "no repo diff",
    ]
    has_explicit_clean = any(indicator in git_status_content for indicator in clean_indicators)

    # Determine if real worktree is clean (skip template check when confirmed clean)
    worktree_clean_bypass = False
    effective_worktree = worktree_path or manifest_worktree
    if effective_worktree and os.path.isdir(effective_worktree):
        rc1, status_out, _ = run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=effective_worktree,
        )
        rc2, diff_out, _ = run(
            ["git", "diff", "--stat"],
            cwd=effective_worktree,
        )
        worktree_really_clean = (
            rc1 == 0 and status_out.strip() == "" and rc2 == 0 and diff_out.strip() == ""
        )
        if worktree_really_clean and manifest_status in ("waiting_for_human_review", "accepted", "rejected", "done"):
            worktree_clean_bypass = True

    git_status_looks_template = (
        git_status_missing or
        (git_status_empty) or
        "git status" in git_status_content.lower()
    )
    real_git_status_content = (
        not git_status_missing and
        not git_status_empty and
        "git status" not in git_status_content.lower()
    )
    if git_status_looks_template and not real_git_status_content and manifest_status not in (None, "running"):
        # Bypass if worktree is confirmed clean and git_status.txt has explicit clean indicators
        if not (worktree_clean_bypass and has_explicit_clean):
            checks.append({
                "name": "lifecycle_missing_git_status",
                "status": "FAIL",
                "message": (
                    f"BJ-0024 pattern: git_status.txt is missing or empty but task status "
                    f"is '{manifest_status}'. Expected real git status output."
                ),
            })

    return checks


# ---------------------------------------------------------------------------
# Repo state (forbidden files / clean state)
# ---------------------------------------------------------------------------

def check_repo_state(repo: str) -> list[dict]:
    """Report whether repo is clean and check for forbidden files."""
    checks = []

    if not repo:
        checks.append({
            "name": "repo_clean_check",
            "status": "WARN",
            "message": "No repo path provided — skipping repo state check",
        })
        return checks

    if not os.path.isdir(repo):
        checks.append({
            "name": "repo_exists",
            "status": "FAIL",
            "message": f"Repo directory not found: {repo}",
        })
        return checks

    rc, status_out, _ = run(["git", "status", "--porcelain"], cwd=repo)
    if rc != 0:
        checks.append({
            "name": "repo_clean_check",
            "status": "WARN",
            "message": f"Could not read git status from {repo}",
        })
        return checks

    is_clean = status_out.strip() == ""
    checks.append({
        "name": "repo_clean_check",
        "status": "PASS" if is_clean else "FAIL",
        "message": f"Repo {'is clean' if is_clean else f'has uncommitted/untracked changes'} at {repo}",
    })

    if not is_clean:
        checks.append({
            "name": "repo_uncommitted_files",
            "status": "WARN",
            "message": f"Uncommitted changes:\n{status_out}",
        })

    return checks


# ---------------------------------------------------------------------------
# Load decision.md for merged commit hint
# ---------------------------------------------------------------------------

def load_decision_merged_commit(artifact_dir: str) -> Optional[str]:
    """Load decision.md to extract merged commit hint."""
    decision_path = os.path.join(artifact_dir, "decision.md")
    if not os.path.isfile(decision_path):
        return None
    try:
        content = open(decision_path).read()
        for line in content.splitlines():
            if line.strip().startswith("merged_commit:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Main audit runner
# ---------------------------------------------------------------------------

def run_audit(
    project: str,
    task_key: str,
    task_id: Optional[str],
    phase: str,
    artifact_dir: Optional[str],
    worktree: Optional[str],
    branch: Optional[str],
    base: str,
    remote: str,
    pr_url: Optional[str],
    pr_number: Optional[int],
    merged_commit: Optional[str],
    config_path: str,
    repo: Optional[str],
    json_output: bool,
) -> tuple[int, list[dict]]:
    """
    Run all audit checks. Returns (exit_code, checks).
    Exit code: 0=no FAIL, 1=at least one FAIL, 2=config error.
    """
    all_checks: list[dict] = []

    # Resolve artifact_dir from config if not provided
    if not artifact_dir and project and task_key:
        artifact_dir = resolve_artifact_dir(config_path, project, task_key)

    # Resolve worktree/branch from config if not provided
    if (not worktree or not branch) and project and task_key:
        w, b = resolve_worktree_branch(config_path, project, task_key)
        if not worktree:
            worktree = w
        if not branch:
            branch = b

    # Resolve repo from config if not provided
    if not repo and project:
        proj_cfg = load_project_config(config_path, project)
        if proj_cfg:
            repo = proj_cfg.get("repo", "")

    # Auto phase: infer from merged_commit presence
    if phase == "auto":
        if merged_commit:
            phase = "post-cleanup"
        elif task_id:
            phase = "review"
        else:
            phase = "review"

    # 1. Artifact directory checks
    if artifact_dir:
        all_checks.extend(check_artifact_dir(artifact_dir, phase))

    # 2. Manifest validation
    if artifact_dir:
        all_checks.extend(check_manifest(artifact_dir))

    # 3. Worktree / branch state
    all_checks.extend(check_worktree_state(worktree, branch, phase, repo or ""))

    # 4. Hermes task state
    if task_id:
        all_checks.extend(check_hermes_task(task_id, phase))

    # 5. PR metadata
    if artifact_dir or pr_url or pr_number:
        all_checks.extend(check_pr_metadata(pr_number, pr_url, artifact_dir or ""))

    # 6. Merged commit
    # Try to get merged_commit from decision.md if not provided
    if not merged_commit and artifact_dir:
        merged_commit = load_decision_merged_commit(artifact_dir)

    if merged_commit or repo:
        all_checks.extend(check_merged_commit(merged_commit, base or "main", repo or ""))

    # 7. Repo state
    if repo:
        all_checks.extend(check_repo_state(repo))

    # 8. BJ-0024 lifecycle compliance
    # Run for review phase tasks to detect self-completion, dirty worktree with
    # requires_pr=false, non-empty changed_files with requires_pr=false, etc.
    # Pass worktree path so real git checks can be used instead of git_status.txt fallback.
    # post-handoff also runs this check using review-like semantics because
    # the task should still be in blocked state, not done, until PR is merged.
    if phase in ("review", "post-handoff") and artifact_dir:
        all_checks.extend(check_lifecycle_compliance(artifact_dir, task_id, phase, worktree_path=worktree))

    # Compute summary status
    has_fail = any(c["status"] == "FAIL" for c in all_checks)
    exit_code = 1 if has_fail else 0

    return exit_code, all_checks


def format_human(project, task_key, task_id, phase, artifact_dir, checks):
    """Format audit results as human-readable text."""
    lines = []
    lines.append(f"Audit: {project} / {task_key} (task_id={task_id or 'n/a'}, phase={phase})")
    lines.append(f"Artifact dir: {artifact_dir or 'n/a'}")
    lines.append("")

    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks if c["status"] == "WARN")
    pass_count = sum(1 for c in checks if c["status"] == "PASS")

    summary = "PASS" if fail_count == 0 else "FAIL"
    lines.append(f"Summary: {summary} ({pass_count} passed, {warn_count} warnings, {fail_count} failures)")
    lines.append("")

    for check in checks:
        status = check["status"]
        name = check["name"]
        msg = check["message"]
        symbol = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}.get(status, "?")
        lines.append(f"  [{symbol}] {name}: {msg}")

    return "\n".join(lines)


def format_json(project, task_key, task_id, phase, artifact_dir, checks):
    """Format audit results as structured JSON."""
    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    summary_status = "FAIL" if fail_count > 0 else "PASS"
    return {
        "project": project,
        "task_key": task_key,
        "task_id": task_id,
        "phase": phase,
        "artifact_dir": artifact_dir,
        "summary_status": summary_status,
        "checks": checks,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        description="Read-only lifecycle audit for Hermes Kanban tasks.",
        prog="kanban_task_audit.py",
    )
    parser.add_argument("--project", required=True, help="Project name from config/projects.yaml")
    parser.add_argument("--task-key", required=True, help="Task key (e.g. BJ-0022)")
    parser.add_argument("--task-id", default=None, help="Hermes task ID (e.g. t_5cfe5f09)")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to projects.yaml")
    parser.add_argument("--artifact-dir", default=None, help="Override artifact directory")
    parser.add_argument("--manifest", default=None, help="Path to artifact_manifest.json (overrides artifact-dir)")
    parser.add_argument("--worktree", default=None, help="Override expected worktree path")
    parser.add_argument("--branch", default=None, help="Override expected branch name")
    parser.add_argument("--base", default="main", help="Base branch for commit reachability check (default: main)")
    parser.add_argument("--remote", default="origin", help="Remote name (default: origin)")
    parser.add_argument("--pr-url", default=None, help="PR URL")
    parser.add_argument("--pr-number", type=int, default=None, help="PR number")
    parser.add_argument("--merged-commit", default=None, help="Merged commit SHA")
    parser.add_argument(
        "--phase",
        choices=["auto", "review", "post-handoff", "post-cleanup"],
        default="auto",
        help="Audit phase: auto (default), review, post-handoff, or post-cleanup",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human-readable text")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Resolve config path (relative to git root if inside a worktree)
    config_path = args.config
    if not os.path.isabs(config_path):
        rc, git_root, _ = run(["git", "rev-parse", "--show-toplevel"])
        if rc == 0 and git_root:
            git_root = git_root.strip()
            candidate = os.path.join(git_root, config_path)
            if os.path.exists(candidate):
                config_path = candidate
            else:
                # Inside .worktrees/ — git toplevel is the worktree, not the parent repo.
                # Try parent of the git root (the actual repo that owns this worktree).
                parent = os.path.dirname(git_root.rstrip("/"))
                if parent and os.path.exists(os.path.join(parent, config_path)):
                    config_path = os.path.join(parent, config_path)

    # Validate config exists
    if not os.path.exists(config_path):
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        return 2

    # Determine artifact_dir
    artifact_dir = args.manifest
    if not artifact_dir:
        artifact_dir = args.artifact_dir
        if not artifact_dir:
            artifact_dir = resolve_artifact_dir(config_path, args.project, args.task_key)

    # Run audit
    exit_code, checks = run_audit(
        project=args.project,
        task_key=args.task_key,
        task_id=args.task_id,
        phase=args.phase,
        artifact_dir=artifact_dir,
        worktree=args.worktree,
        branch=args.branch,
        base=args.base,
        remote=args.remote,
        pr_url=args.pr_url,
        pr_number=args.pr_number,
        merged_commit=args.merged_commit,
        config_path=config_path,
        repo=None,  # resolved internally
        json_output=args.json,
    )

    # Output
    if args.json:
        result = format_json(args.project, args.task_key, args.task_id, args.phase, artifact_dir, checks)
        print(json.dumps(result, indent=2))
    else:
        output = format_human(args.project, args.task_key, args.task_id, args.phase, artifact_dir, checks)
        print(output)

    return exit_code


if __name__ == "__main__":
    sys.exit(main() or 0)