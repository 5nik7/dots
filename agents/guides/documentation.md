# Documentation Work Guide

Read this guide when changing project documentation or when implementation work affects documented behavior.

## Documentation Layers

- `AGENTS.md` — concise project-wide rules and routing.
- `agents/guides/` — task procedures: what to read and do when changing an area.
- `docs/` — durable architecture and behavior reference for contributors.
- `plans/` — scoped sequencing, acceptance criteria, open questions, and status.
- `README.md` — truthful user-facing overview and implemented quick start.

Do not turn `AGENTS.md` into an exhaustive design document. Link to the authoritative reference instead.

## Status Language

Use status labels consistently:

- **Implemented** — present and verified in the repository.
- **Proposed** — intended direction that may still change.
- **Draft** — incomplete specification requiring decisions or validation.
- **Deprecated** — still present for compatibility with a documented replacement.
- **Removed** — historical only; do not show as usable.

Never place a proposed installation command in the README as if it is safe to run.

## Synchronization Matrix

| Change | Required documentation |
| --- | --- |
| Component or directory ownership | `docs/architecture.md` |
| Product invariant or priority | `docs/principles.md`, plus a decision record when material |
| Command, flag, help, output, or metadata | `docs/commands.md`, generated reference, README when user-facing |
| Manifest, profile, variable, or precedence | `docs/specification.md` |
| Mutation, backup, rollback, force, package, or secret handling | `docs/safety.md` |
| Platform paths, detection, capability, or limitation | `docs/platforms.md` |
| Test runner, safety case, benchmark, or CI claim | `docs/testing.md` |
| Milestone, scope, dependency, or open question | Applicable file under `plans/` |

## Style

- Write complete sentences and use direct language.
- Do not hard-wrap prose at an arbitrary column; break at structural boundaries.
- Use relative links for repository files.
- Prefer tables for exact mappings and comparisons.
- Mark examples as conceptual when the command or manifest is not implemented.
- Keep one authoritative exhaustive list and link to it elsewhere.
- Use `Termux`, `Linux`, `WSL`, `Windows`, `PowerShell`, `Bash`, and `Zsh` consistently.
- Spell the project and command as lowercase `dots` except at the beginning of a title.

## Plans and Decisions

- Plans are living documents while work is active.
- Update checkboxes and status in the same change that completes or changes work.
- Move durable conclusions from a plan into the relevant reference document.
- Record a material architectural decision in `docs/decisions/` rather than leaving its reasoning only in chat or a completed plan.
- Do not rewrite a decision record to hide history; add a superseding decision.

## Verification

Before finishing a documentation change:

1. Run `git diff --check`.
2. Verify every relative Markdown link resolves.
3. Search for stale names, paths, and status claims.
4. Confirm examples do not imply unimplemented behavior.
5. Confirm repeated lists have a named source of truth.
6. Update the applicable plan status.

