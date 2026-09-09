# Dots Documentation

The `dots` CLI is currently in the design and incremental-migration phase. These documents define the working direction without claiming that proposed commands already exist.

## Start Here

- [`principles.md`](principles.md) — priorities and engineering invariants.
- [`architecture.md`](architecture.md) — system boundaries, execution flow, and target repository shape.
- [`commands.md`](commands.md) — proposed CLI vocabulary and external command model.
- [`specification.md`](specification.md) — draft modules, profiles, hosts, manifests, and resolution rules.
- [`safety.md`](safety.md) — plan, apply, backup, transaction, rollback, undo, and secret handling.
- [`platforms.md`](platforms.md) — Termux, Linux, WSL, and Windows behavior.
- [`testing.md`](testing.md) — isolation, test layers, safety cases, and performance measurement.
- [`current-repository.md`](current-repository.md) — baseline inventory and migration constraints.
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

