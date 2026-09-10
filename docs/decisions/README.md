# Architecture Decision Records

Use this directory for material decisions whose reasoning should survive completed plans and conversations.

## When to Add a Record

Create a decision record when choosing or changing:

- Core implementation language or distribution model.
- Manifest format or schema-version policy.
- Command metadata and extension protocol.
- State/journal format or compatibility policy.
- Platform/profile/host composition semantics.
- Link fallback, force, backup, rollback, or secret policy.
- Optional-source and dependency model.
- A major repository-layout or history migration.

Small implementation details that follow an existing decision belong in code and reference docs, not a new record.

## Filename

```text
NNNN-short-kebab-title.md
```

Use the next number. Do not renumber existing records.

## Template

```markdown
# NNNN: Decision title

Status: Proposed | Accepted | Superseded | Rejected
Date: YYYY-MM-DD

## Context

What problem and constraints require a decision?

## Decision

What is being chosen?

## Consequences

What becomes easier, harder, required, or intentionally unsupported?

## Alternatives Considered

What credible alternatives were considered and why were they not selected?

## Validation

What experiment, benchmark, test, or production evidence supports the decision?

## Supersedes or Superseded By

Link related records when applicable.
```

Do not edit an accepted record to make an old decision appear different. Add a new record that supersedes it, then update the relevant reference documentation.

## Records

- [0001: Evaluate Go in an isolated Termux experiment](0001-go-portability-experiment.md) — Accepted for the experiment only.
- [0002: Adopt Go for the core with bounded initial coverage](0002-phase-1-go-adoption.md) — Accepted by the owner on 2026-09-10; bounded permanent-core implementation is present; production support remains pending.
- [0003: Trusted external command protocol](0003-trusted-external-command-protocol.md) — Accepted; bounded development extension mechanism implemented.
- [0004: Versioned machine-readable command discovery](0004-versioned-command-discovery.md) — Accepted by the owner; schema-1 catalog over shared static metadata.
