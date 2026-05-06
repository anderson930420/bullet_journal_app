# Hermes Artifact Contract

## Purpose

The Hermes Artifact Contract defines a machine-readable schema and standard folder layout for task artifacts produced by Hermes Kanban workers. It enables:

- Generic PR handoff helpers
- Generic accept / cleanup helpers
- Lightweight dashboards
- Cross-project task tracking
- Automated artifact validation and reporting

## Standard Folder Layout

```
<artifact_root>/<task-key>/
  artifact_manifest.json   # required — machine-readable contract
  completion_report.md      # required — human-readable summary
  git_status.txt            # required — `git status --short --untracked-files=all`
  worktree_info.txt         # required — git worktree list + branch info
  guard_report.txt          # conditionally required — when guard runs with --write-artifacts
  decision.md               # conditionally required — after human review/acceptance
  test_output.txt           # optional
  diff_stat.txt             # optional
  review_notes.md           # optional
  pr_info.json              # optional
```

`<artifact_root>` is defined per-project in `config/projects.yaml` (field: `artifact_root`).
`<task-key>` is the Hermes task key (e.g. `BJ-0012R`).

## Required vs Optional Artifacts

### Required (always)

| File | Purpose |
|------|---------|
| `artifact_manifest.json` | Machine-readable contract with schema version and status |
| `completion_report.md` | Human-readable worker completion report |
| `git_status.txt` | `git status --short --untracked-files=all` output |
| `worktree_info.txt` | `git worktree list` + current branch info |

### Conditionally Required

| File | Condition |
|------|-----------|
| `guard_report.txt` | Required when the worker guard runs with `--write-artifacts` |
| `decision.md` | Required after human review / acceptance |

### Optional

| File | Purpose |
|------|---------|
| `test_output.txt` | Raw test runner output |
| `diff_stat.txt` | `git diff --stat` output |
| `review_notes.md` | Human review notes |
| `pr_info.json` | PR metadata (URL, number, merged commit) |

## artifact_manifest.json Schema

**Schema version:** `hermes-task-artifacts/v1`

### Minimum Fields

```json
{
  "schema_version": "hermes-task-artifacts/v1",
  "project": "bullet-journal",
  "task_key": "BJ-0012R",
  "task_id": null,
  "status": "waiting_for_human_review",
  "recommendation": "accept",
  "repo": "/home/ubuntu/bullet_journal_app",
  "worktree": "/home/ubuntu/bullet_journal_app/.worktrees/BJ-0012R",
  "branch": "worktree/BJ-0012R",
  "artifact_dir": "/home/ubuntu/.hermes/task-artifacts/BJ-0012R",
  "requires_pr": true,
  "pr_url": null,
  "merged_commit": null,
  "changed_files": [],
  "checks": [],
  "artifacts": []
}
```

### Allowed `status` Values

| Status | Meaning |
|--------|---------|
| `ready` | Task is ready to be picked up |
| `running` | Task is in progress |
| `waiting_for_human_review` | Worker completed; awaiting human review |
| `accepted` | Human accepted the work |
| `rejected` | Human rejected the work |
| `merged` | Changes merged to main branch |
| `done` | Task fully completed |
| `unknown` | Status could not be determined |

### Allowed `recommendation` Values

| Recommendation | Meaning |
|---------------|---------|
| `accept` | Worker recommends accepting the artifacts |
| `revise` | Worker recommends revision before accept |
| `reject` | Worker recommends rejecting the artifacts |
| `unknown` | No recommendation made |

### `checks[]` Item Schema

Each item describes a verification check run by the worker:

```json
{
  "name": "py_compile",
  "command": "python3 -m py_compile scripts/kanban_artifact_manifest.py",
  "result": "pass",
  "exit_code": 0,
  "artifact": null
}
```

Allowed `result` values: `pass`, `fail`, `not_run`, `unknown`

### `artifacts[]` Item Schema

Each item describes a file in the artifact folder:

```json
{
  "path": "/home/ubuntu/.hermes/task-artifacts/BJ-0012R/completion_report.md",
  "required": true,
  "exists": true,
  "purpose": "Worker completion report"
}
```

## Using the Manifest Helper

The `scripts/kanban_artifact_manifest.py` script manages artifact manifests:

### Initialize a manifest

```bash
python3 scripts/kanban_artifact_manifest.py init \
  --project bullet-journal \
  --task-key BJ-0012R \
  --status waiting_for_human_review \
  --recommendation accept \
  --requires-pr true \
  --output /home/ubuntu/.hermes/task-artifacts/BJ-0012R/artifact_manifest.json
```

### Validate a manifest

```bash
python3 scripts/kanban_artifact_manifest.py validate \
  --path /home/ubuntu/.hermes/task-artifacts/BJ-0012R/artifact_manifest.json
```

## Example: Worker Completion

When a worker completes a task:

1. All required artifacts are written to the artifact folder
2. `kanban_artifact_manifest.py init` is called with `status: waiting_for_human_review`
3. The manifest is validated with `kanban_artifact_manifest.py validate`
4. The task is marked `blocked / waiting_for_human_review` on the Kanban board

```bash
python3 scripts/kanban_artifact_manifest.py init \
  --project bullet-journal \
  --task-key BJ-0012R \
  --status waiting_for_human_review \
  --recommendation accept \
  --requires-pr true \
  --output /home/ubuntu/.hermes/task-artifacts/BJ-0012R/artifact_manifest.json \
  --overwrite
```

## Example: Human Acceptance

After human review and acceptance:

1. Reviewer writes `decision.md` to the artifact folder
2. Reviewer updates `artifact_manifest.json` with `status: accepted`
3. If a PR was opened: `pr_url` and `merged_commit` are filled in

## What Happens When a Task Has No Repo Diff

A task that only reads or analyzes (no source changes) should:

- Set `requires_pr: false`
- Leave `changed_files: []`
- Still produce all required artifacts (completion_report, git_status, worktree_info)

## What Happens When a Task Requires a PR

A task that modifies source code should:

- Set `requires_pr: true`
- List all changed files in `changed_files: []`
- After PR merge: set `pr_url` and `merged_commit`
- Set `status: merged` once the PR is merged

## How Dashboard / PR Handoff / Accept Helpers Will Use It

Downstream tools read `artifact_manifest.json` to:

1. Determine task status and recommendation
2. List all changed files for the PR
3. Verify all required artifacts exist
4. Check pass/fail results of worker-run tests
5. Resolve PR URL and merged commit for handoff

## Relation to the Generic Workflow

The artifact contract is the final layer in the generic workflow:

```
config/projects.yaml          → project registry
kanban_create_safe.py         → safe task creation + worktree setup
kanban_worker_guard.py        → preflight workspace verification
kanban_artifact_manifest.py   → postflight artifact contract
docs/hermes_artifact_contract.md → this document
```

Workers produce artifacts following this contract. Review tools consume them.

## Backward Compatibility

Existing artifact files (`completion_report.md`, `git_status.txt`, `worktree_info.txt`, `guard_report.txt`) are still produced and remain valid. The `artifact_manifest.json` layer is additive — it adds machine-readable structure without removing the human-readable layer.
