#!/usr/bin/env python3
"""
Hermes Artifact Manifest Helper

A generic tool for initializing and validating artifact_manifest.json files
produced by Hermes Kanban workers.

Usage:
    python3 scripts/kanban_artifact_manifest.py init [options]
    python3 scripts/kanban_artifact_manifest.py validate [options]
    python3 scripts/kanban_artifact_manifest.py --help
"""

import argparse
import json
import os
import sys


SCHEMA_VERSION = "hermes-task-artifacts/v1"

ALLOWED_STATUS = {
    "ready", "running", "waiting_for_human_review",
    "accepted", "rejected", "merged", "done", "unknown"
}

ALLOWED_RECOMMENDATION = {"accept", "revise", "reject", "unknown"}

ALLOWED_CHECK_RESULT = {"pass", "fail", "not_run", "unknown"}

DEFAULT_CONFIG_PATH = "config/projects.yaml"


def load_project_config(config_path, project):
    """Load project registry and resolve project info."""
    if not os.path.exists(config_path):
        return None
    with open(config_path, "r") as f:
        data = yaml_safe_load(f)
    projects = data.get("projects", {})
    if project not in projects:
        return None
    return projects[project]


def resolve_paths(config_path, project, task_key):
    """Resolve repo, worktree, branch, artifact_dir from project registry.

    Uses stdlib-only fallback parser for config/projects.yaml.
    Raises ValueError if project not found and no explicit overrides provided.
    """
    if not os.path.exists(config_path):
        raise ValueError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        data = yaml_safe_load(f)
    projects = data.get("projects", {})
    if project not in projects:
        raise ValueError(f"Project {project!r} not found in {config_path}")
    p = projects[project]
    repo = p["repo"]
    default_branch = p["default_branch"]
    artifact_root = p["artifact_root"]
    branch_prefix = p.get("branch_prefix", "worktree/")

    worktree = os.path.join(repo, ".worktrees", task_key)
    branch = branch_prefix + task_key
    artifact_dir = os.path.join(artifact_root, task_key)

    return {
        "repo": repo,
        "worktree": worktree,
        "branch": branch,
        "artifact_dir": artifact_dir,
    }


def yaml_safe_load(stream):
    """Load YAML using only the standard library."""
    try:
        import yaml
        return yaml.safe_load(stream)
    except ImportError:
        # Fallback: simple YAML parser for the projects.yaml format
        data = {}
        current_project = None
        for line in stream.readlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("projects:"):
                continue
            if line.startswith("  ") and ":" in line:
                key = line.strip().split(":")[0]
                rest = line.strip().split(":", 1)[1].strip()
                if rest:
                    if current_project:
                        data.setdefault("projects", {}).setdefault(current_project, {})[key] = rest
            else:
                project_name = line.strip().rstrip(":")
                if project_name:
                    current_project = project_name
        return data


def parse_artifact_arg(value):
    """Parse --artifact path:required:purpose string.

    Format: path:required:purpose
    required is 'true' or 'false' (case-insensitive).
    purpose is the remaining text after the second colon.
    """
    parts = value.split(":", 2)
    if len(parts) < 2:
        raise ValueError(f"Invalid --artifact format {value!r}, expected path:required:purpose")
    path = parts[0]
    required = parts[1].lower() in ("true", "1", "yes")
    purpose = parts[2] if len(parts) > 2 else ""
    return {"path": path, "required": required, "exists": True, "purpose": purpose}


def build_manifest(args):
    """Build a manifest dict from init arguments."""
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "project": args.project,
        "task_key": args.task_key,
        "task_id": args.task_id,
        "status": args.status,
        "recommendation": args.recommendation,
        "repo": args.repo,
        "worktree": args.worktree,
        "branch": args.branch,
        "artifact_dir": args.artifact_dir,
        "requires_pr": args.requires_pr,
        "pr_url": args.pr_url,
        "merged_commit": args.merged_commit,
        "changed_files": [],
        "checks": [],
        "artifacts": [],
    }

    if args.changed_file:
        manifest["changed_files"] = args.changed_file

    if args.artifact:
        parsed = []
        for a in args.artifact:
            try:
                parsed.append(parse_artifact_arg(a))
            except ValueError as e:
                raise SystemExit(f"ERROR: {e}")
        manifest["artifacts"] = parsed

    return manifest


def validate_manifest(manifest, artifact_dir=None):
    """Validate a manifest dict. Returns (valid, errors)."""
    errors = []

    # Required top-level fields
    required_fields = [
        "schema_version", "project", "task_key", "task_id", "status", "recommendation",
        "repo", "worktree", "branch", "artifact_dir", "requires_pr",
        "pr_url", "merged_commit", "changed_files", "checks", "artifacts"
    ]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"Missing required field: {field}")

    # schema_version
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"Invalid schema_version: got {manifest.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION!r}"
        )

    # status enum
    if manifest.get("status") not in ALLOWED_STATUS:
        errors.append(
            f"Invalid status: got {manifest.get('status')!r}, "
            f"expected one of {sorted(ALLOWED_STATUS)}"
        )

    # recommendation enum
    if manifest.get("recommendation") not in ALLOWED_RECOMMENDATION:
        errors.append(
            f"Invalid recommendation: got {manifest.get('recommendation')!r}, "
            f"expected one of {sorted(ALLOWED_RECOMMENDATION)}"
        )

    # requires_pr must be bool
    if not isinstance(manifest.get("requires_pr"), bool):
        errors.append(f"requires_pr must be a bool, got {type(manifest.get('requires_pr'))}")

    # changed_files must be list
    if not isinstance(manifest.get("changed_files"), list):
        errors.append(f"changed_files must be a list, got {type(manifest.get('changed_files'))}")

    # checks must be list
    if not isinstance(manifest.get("checks"), list):
        errors.append(f"checks must be a list, got {type(manifest.get('checks'))}")
    else:
        for i, check in enumerate(manifest.get("checks", [])):
            if not isinstance(check, dict):
                errors.append(f"checks[{i}] must be an object, got {type(check)}")
                continue
            if "name" not in check:
                errors.append(f"checks[{i}] missing required field: name")
            if "result" not in check:
                errors.append(f"checks[{i}] missing required field: result")
            elif check["result"] not in ALLOWED_CHECK_RESULT:
                errors.append(
                    f"checks[{i}].result: invalid value {check['result']!r}, "
                    f"expected one of {sorted(ALLOWED_CHECK_RESULT)}"
                )

    # artifacts must be list
    if not isinstance(manifest.get("artifacts"), list):
        errors.append(f"artifacts must be a list, got {type(manifest.get('artifacts'))}")
    else:
        for i, artifact in enumerate(manifest.get("artifacts", [])):
            if not isinstance(artifact, dict):
                errors.append(f"artifacts[{i}] must be an object, got {type(artifact)}")
                continue
            if "path" not in artifact:
                errors.append(f"artifacts[{i}] missing required field: path")
            elif os.path.isabs(artifact.get("path", "")):
                # Validate artifacts[].exists against actual filesystem state
                if "exists" in artifact:
                    actual_exists = os.path.exists(artifact["path"])
                    declared_exists = bool(artifact["exists"])
                    if actual_exists != declared_exists:
                        errors.append(
                            f"artifacts[{i}].exists mismatch: declared {declared_exists}, "
                            f"actual {'exists' if actual_exists else 'not found'} for path {artifact['path']!r}"
                        )

    return len(errors) == 0, errors


def cmd_init(args):
    """Initialize an artifact manifest."""
    config_path = args.config or DEFAULT_CONFIG_PATH

    # Resolve paths from project registry if project + task_key provided
    if args.project and args.task_key:
        try:
            paths = resolve_paths(config_path, args.project, args.task_key)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print("Hint: provide explicit --repo, --worktree, --branch, --artifact-dir to bypass project lookup, or use --project that exists in config/projects.yaml.", file=sys.stderr)
            return 1
        # Apply resolved values as defaults (CLI args override)
        args.repo = args.repo or paths["repo"]
        args.worktree = args.worktree or paths["worktree"]
        args.branch = args.branch or paths["branch"]
        args.artifact_dir = args.artifact_dir or paths["artifact_dir"]

    # Build manifest
    manifest = build_manifest(args)

    # Ensure output dir exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"ERROR: Could not create output directory {output_dir}: {e}", file=sys.stderr)
            return 1

    # Check overwrite
    if os.path.exists(args.output) and not args.overwrite:
        print(f"ERROR: Output file {args.output} already exists. Use --overwrite to replace.", file=sys.stderr)
        return 1

    # Write manifest
    try:
        with open(args.output, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)
        print(f"PASS: Manifest written to {args.output}")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to write manifest: {e}", file=sys.stderr)
        return 1


def cmd_validate(args):
    """Validate an artifact manifest."""
    if not os.path.exists(args.path):
        print(f"ERROR: Manifest file not found: {args.path}", file=sys.stderr)
        return 1

    try:
        with open(args.path, "r") as f:
            manifest = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        return 1

    # Infer artifact_dir from manifest if available
    artifact_dir = manifest.get("artifact_dir")

    valid, errors = validate_manifest(manifest, artifact_dir=artifact_dir)

    if valid:
        print(f"PASS: Manifest is valid ({args.path})")
        return 0
    else:
        print(f"ERROR: Manifest validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Hermes Artifact Manifest Helper — init and validate artifact_manifest.json",
        prog="kanban_artifact_manifest.py",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init subcommand
    init_parser = subparsers.add_parser("init", help="Initialize an artifact manifest")
    init_parser.add_argument("--project", help="Project name (looks up config/projects.yaml)")
    init_parser.add_argument("--task-key", help="Task key (e.g. BJ-0012R)")
    init_parser.add_argument("--task-id", default=None, help="Hermes task ID")
    init_parser.add_argument("--status", required=True, help=f"Status value. Allowed: {sorted(ALLOWED_STATUS)}")
    init_parser.add_argument("--recommendation", required=True, help=f"Recommendation. Allowed: {sorted(ALLOWED_RECOMMENDATION)}")
    init_parser.add_argument("--repo", help="Repo path (resolved from --project if not given)")
    init_parser.add_argument("--worktree", help="Worktree path (resolved from --project if not given)")
    init_parser.add_argument("--branch", help="Branch name (resolved from --project if not given)")
    init_parser.add_argument("--artifact-dir", help="Artifact dir (resolved from --project if not given)")
    init_parser.add_argument("--requires-pr", type=lambda v: v.lower() in ("true", "1", "yes"), required=True,
                             help="Whether this task requires a PR")
    init_parser.add_argument("--pr-url", default=None)
    init_parser.add_argument("--merged-commit", default=None)
    init_parser.add_argument("--changed-file", action="append", default=[],
                             help="Changed file (can be specified multiple times)")
    init_parser.add_argument("--artifact", action="append", default=[],
                             help="Artifact as path:required:purpose (can be specified multiple times)")
    init_parser.add_argument("--output", required=True, help="Output path for manifest JSON")
    init_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing manifest")
    init_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to projects.yaml")

    # validate subcommand
    val_parser = subparsers.add_parser("validate", help="Validate an artifact manifest")
    val_parser.add_argument("--path", required=True, help="Path to manifest JSON")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "validate":
        return cmd_validate(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
