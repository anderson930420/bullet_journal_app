# Bug Fix Task Template

## Purpose

Bug fix tasks address defects or incorrect behavior in the codebase.

## Task type

Bug fix.

## Key characteristics

- **Reproduce or explain the bug** — describe steps to reproduce or the root cause
- **Patch root cause** — fix the underlying issue, not just the symptom
- **Add or update tests where practical** — ensure the bug doesn't regress

## Sections

```markdown
## Goal

<What bug needs to be fixed.>

## Background

<Description of the bug and its impact.>

## Allowed changes

- <files that need to be modified to fix the bug>
- <test files to add or update>

## Bug fix guidance

1. Reproduce or explain the bug
2. Patch root cause
3. Add or update tests where practical
4. Verify the fix
```

## Governance notes

- Final state: `blocked / waiting_for_human_review`
- Do not push, merge, or self-approve
- Write all artifacts to `~/.hermes/task-artifacts/<task-key>/`
