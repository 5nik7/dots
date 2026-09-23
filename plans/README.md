# Implementation Plans

Plans describe active, paused, proposed, or completed work. Durable architecture and behavior belong in `docs/`; plans link to those references rather than redefining them.

## Planning Documents

The [roadmap](roadmap.md#current-priority) owns current priorities: repository maintenance is active; further Go implementation and migration are paused until the owner requests resumption.

- [`bash-dispatcher.md`](bash-dispatcher.md) — modular Bash dispatcher, presentation, completion, and verification.
- [`zsh-startup.md`](zsh-startup.md) — existing Zsh optimization, compatibility checks, and measured results.
- [`roadmap.md`](roadmap.md) — project phases, dependencies, decision gates, and completion criteria.
- [`phase-1-portability.md`](phase-1-portability.md) — completed isolated Go experiment, retained evidence, accepted adoption decision, and deferred portability coverage.
- [`phase-2-command-center.md`](phase-2-command-center.md) — implemented command-center slices and native verification; further development paused.
- [`termux-mvp.md`](termux-mvp.md) — implemented file inventory plus deferred installation stages and acceptance criteria.

## Plan Rules

- State whether a plan is proposed, active, paused, blocked, or completed. A pause describes scheduling, not the implementation status of completed work.
- Define scope, non-goals, dependencies, risks, verification, and acceptance criteria.
- Keep task status current in the same change that completes or changes the task.
- Move durable conclusions into the relevant file under `../docs/`.
- Link decision records for choices that constrain future work.
- Do not leave completed plans as the only documentation for implemented behavior.

When a plan is complete, retain it if it explains migration or decision history. Mark it complete and link the resulting implementation/reference rather than rewriting its original goal.

- [Shared theme implementation](themes.md): TOML palettes, compatibility, Zsh and Neovim integration.
- [Additional theme families](theme-families.md): native palettes/adapters and pywal16 snapshot import.

## Completed configuration and command work

- [Configuration path migration](config-path-migration.md).
- [Files catalog](files-catalog.md).
- [Omarchy-style themes](omarchy-themes.md).

These authorized Bash/Python workstreams extend the existing implementation without resuming Go development.
