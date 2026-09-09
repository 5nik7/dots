# dots

`dots` is becoming a fast, safe, modular command center for managing dotfiles, scripts, shells, themes, packages, and environment setup across Termux, Linux, WSL, and native Windows.

## Status

The repository currently contains the existing dotfiles collection and an early `bin/dots` prototype. The new command architecture is in the design and incremental-migration phase.

There is not yet a supported remote installer or a production-ready `dots apply` workflow. Installation examples will be added only after the planner, transaction engine, backup/rollback behavior, and first Termux profile have been verified.

## Intended Experience

The proposed CLI uses discoverable command groups:

```text
dots status
dots spec
dots plan
dots apply
dots files list
dots links check
dots themes apply <name>
```

External commands named `dots-*` will be automatically available through the main command. For example, `dots-themes-apply` can provide `dots themes apply` without adding routing code to the dispatcher.

These examples describe the intended interface and are not yet implemented.

## Design Priorities

1. Protect existing files and preserve a reliable path back.
2. Keep command dispatch, planning, and shell startup fast.
3. Show a complete plan before changing a machine.
4. Use symbolic links by default and copy only when explicitly selected.
5. Compose shared files with platform-, profile-, and host-specific modules.
6. Keep private sources and large optional assets out of the minimum bootstrap path.
7. Keep behavior, tests, help, completions, and documentation synchronized.

## Documentation

- [`AGENTS.md`](AGENTS.md) — authoritative instructions for agents and contributors.
- [`docs/principles.md`](docs/principles.md) — product and engineering priorities.
- [`docs/architecture.md`](docs/architecture.md) — proposed system boundaries and repository structure.
- [`docs/commands.md`](docs/commands.md) — proposed command family and extension model.
- [`docs/specification.md`](docs/specification.md) — draft modules, profiles, hosts, and manifests.
- [`docs/safety.md`](docs/safety.md) — planning, transactions, backups, rollback, and undo.
- [`docs/platforms.md`](docs/platforms.md) — Termux, Linux, WSL, and Windows model.
- [`docs/testing.md`](docs/testing.md) — test isolation, failure cases, and performance measurement.
- [`docs/current-repository.md`](docs/current-repository.md) — baseline inventory and migration constraints.
- [`plans/roadmap.md`](plans/roadmap.md) — phased implementation roadmap.
- [`plans/termux-mvp.md`](plans/termux-mvp.md) — first end-to-end implementation target.

The complete documentation index is in [`docs/README.md`](docs/README.md).

## Contributing With an Agent

Agents must read [`AGENTS.md`](AGENTS.md) before changing the project and then read the task-specific guide under [`agents/guides/`](agents/guides/). A behavior change is incomplete until the corresponding tests, plans, and source-of-truth documentation are updated in the same change.

## Migration Approach

The current dotfiles remain in place while the new core is developed beside them. Migration will proceed one module at a time, beginning with a small Termux profile. Existing submodules, platform repositories, large assets, and actively used scripts will not be removed or reorganized without a focused plan and recovery path.
