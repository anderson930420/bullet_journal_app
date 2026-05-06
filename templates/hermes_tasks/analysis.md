# Analysis Task Template

## Purpose

Analysis tasks are read-only investigations that produce artifacts (reports, decisions, recommendations) without modifying source code.

## Task type

Analysis / read-only.

## Key characteristics

- **No source changes** unless explicitly allowed
- **Produce artifact/report** as primary output
- **No PR required** unless repo files changed as part of the analysis

## Sections

```markdown
## Goal

<One-paragraph description of what this analysis must achieve.>

## Background

<Context and motivation for this analysis.>

## Analysis scope

<Specific questions this analysis must answer.>

## Required artifacts

- analysis_report.md with findings
- git_status.txt
- worktree_info.txt
```

## Governance notes

- Final state: `blocked / waiting_for_human_review`
- Do not push, merge, or self-approve
- Write all artifacts to `~/.hermes/task-artifacts/<task-key>/`
