# Dots Documentation

The live CLI combines Bash and native PowerShell entry points with shared Python controllers. These references describe current commands, configuration ownership, managed operations, platform limits and Anodize palette authoring.

## Start Here

- [Git operations](git.md) and [managed files](files.md) — implemented bounded workflows.

- [`principles.md`](principles.md) — priorities and engineering invariants.
- [`architecture.md`](architecture.md) — system boundaries, execution flow, and target repository shape.
- [`commands.md`](commands.md) — implemented CLI vocabulary and external command model.
- [`presentation.md`](presentation.md) — required human output style, color/icon policy, data-interface boundaries and acceptance gate for new or changed commands.
- [`specification.md`](specification.md) — implemented theme, catalog, shell and installation schemas.
- [`safety.md`](safety.md) — plan, apply, backup, transaction, rollback, undo, and secret handling.
- [`platforms.md`](platforms.md) — Termux, Linux, WSL, and Windows behavior.
- [`testing.md`](testing.md) — isolation, test layers, safety cases, and performance measurement.
- [`decisions/`](decisions/) — architectural decision records.

Active sequencing and acceptance criteria live under [`../plans/`](../plans/).

Agents and contributors must begin with [`../AGENTS.md`](../AGENTS.md), then read the applicable task guide under [`../agents/guides/`](../agents/guides/).

## Document Roles

| Location | Audience | Purpose |
| --- | --- | --- |
| `AGENTS.md` | Agents and contributors | Project-wide operating contract and guide routing |
| `agents/guides/` | Agents and contributors | Procedures for a particular kind of change |
| `docs/` | Contributors and maintainers | Durable architecture and behavior reference |
| `plans/` | Contributors and maintainers | Active scope, sequence, acceptance criteria, and open questions |
| `README.md` | Users and contributors | Truthful overview of capabilities that currently exist |

## Status Labels

- **Implemented** means the behavior exists and has been verified.
- **Proposed** means it is the preferred direction but may change before implementation.
- **Draft** means important details or validation are still missing.
- **Deprecated** means the behavior remains temporarily for compatibility.

When implementation changes a documented behavior, update the authoritative document in the same change. When a proposed design becomes real, replace its status label and remove stale caveats.

- [Anodize](anodize.md) — implemented palette authoring, recipe, CLI and publication boundaries.

- [Wiki](wiki.md) — canonical source projection, navigation and associated Git workflow.
