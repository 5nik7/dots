# dots

`dots` is becoming a fast, safe, modular command center for managing dotfiles, scripts, shells, themes, packages, and environment setup across Termux, Linux, WSL, and native Windows.

## Status

The repository contains the existing dotfiles collection, the Bash `bin/dots` prototype, and an isolated experimental Go core under `experiments/go-portability/`. The new command architecture is in the design and incremental-migration phase. Go remains provisional pending review of the portability evidence.

There is not yet a supported remote installer or a production-ready `dots apply` workflow. Installation examples will be added only after the planner, transaction engine, backup/rollback behavior, and first Termux profile have been verified.

## Try the Termux Experiment

**Implemented, experimental:** help, version output, and read-only platform diagnostics, verified natively on Termux Android/ARM64. The live `dots` command and dotfiles are unchanged.

From the repository root, using the installed Go 1.27.x toolchain and Python 3:

```bash
DOTS_SPIKE_BIN="$(python3 experiments/go-portability/tools/verify.py build)"
DOTS="$PWD" "$DOTS_SPIKE_BIN" --help
"$DOTS_SPIKE_BIN" --version
"$DOTS_SPIKE_BIN" doctor
"$DOTS_SPIKE_BIN" doctor --json
```

The build command prints the executable path on stdout and progress on stderr. It retains the binary, a public logo copy, and `evidence.json` in a unique directory under the temporary directory. Tool caches and build work are disposable; nothing is installed or added to `PATH`, and no dependencies are downloaded. Temporary artifacts may be removed by the system; rebuild when needed.

Help loads the optional `logo.txt` from `$DOTS` or, when unset, beside the executable's parent `bin/` directory. Missing or unusable logos do not prevent help. Version and diagnostic output contain no logo. Diagnostics reports candidate paths and `not_probed` filesystem capabilities; it does not create files, load configuration contents, or apply changes.

Run focused checks or startup measurements with:

```bash
python3 experiments/go-portability/tools/verify.py check
python3 experiments/go-portability/tools/verify.py bench
```

Checks additionally use installed `gofmt` and `readelf`; measurements use installed `hyperfine`. Missing prerequisites are reported without installation. See the [experiment plan and results](plans/phase-1-portability.md), [testing instructions](docs/testing.md), and [platform evidence](docs/platforms.md). Linux/Windows compilation does not establish that those artifacts run on their target platforms.

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
