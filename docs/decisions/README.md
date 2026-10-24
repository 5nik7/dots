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

- [0006: Modular Bash command framework](0006-bash-command-framework.md) — Accepted; live Bash protocol.

- [0007: Data-driven themes and bounded Bash selection state](0007-data-driven-themes.md).

- [0008: Configuration catalogs and application themes](0008-config-catalog-and-theme-apps.md) — Accepted; canonical config paths, files metadata and Omarchy-style themes.

- [0009: Cohesive command presentation](0009-cohesive-command-presentation.md).
- [0010: Git and managed-file operations](0010-git-and-managed-file-operations.md).

- [0011: Anodize palette authoring](0011-anodize-authoring.md) — accepted scoped core/CLI implementation.

- [0012: One theme command family](0012-unified-theme-cli.md) — Accepted; supersedes plural CLI compatibility.

- [0013: Dots environment and theme collection ownership](0013-shell-environment-and-theme-collection.md).

- [0014: Native PowerShell parity](0014-native-powershell-parity.md) — native adapter/shared-controller direction, Windows paths and permanent dual-shell maintenance; native acceptance pending.
