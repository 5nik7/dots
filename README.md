# dots

`dots` is becoming a fast, safe, modular command center for managing dotfiles, scripts, shells, themes, packages, and environment setup across Termux, Linux, WSL, and native Windows.

## Status

The repository contains the existing dotfiles collection, the Bash `bin/dots` prototype, and an isolated experimental Go core under `experiments/go-portability/`. The new command architecture is in the design and incremental-migration phase. [Go adoption is accepted](docs/decisions/0002-phase-1-go-adoption.md), with Go 1.27.1 as the initial build/test baseline. The first permanent-core slice now adds a development executable and validated read-only built-in registry; the broader Phase 2 command center remains deferred.

There is not yet a supported remote installer or a production-ready `dots apply` workflow. Installation examples will be added only after the planner, transaction engine, backup/rollback behavior, and first Termux profile have been verified.

## Try the Permanent Development Core

With Go 1.27.1 and Python 3 already installed, run from this checkout (not the original live checkout):

```bash
DOTS_DEV_BIN="$(python3 -B tools/verify_core.py build)"
"$DOTS_DEV_BIN" --help
"$DOTS_DEV_BIN" --version
"$DOTS_DEV_BIN" doctor
"$DOTS_DEV_BIN" doctor --json
```

The verifier creates test-owned build/config/cache/output roots, disables Go downloads and telemetry, and prints only the resulting binary path on stdout. Nothing is installed or added to PATH. The artifact includes `bin/dots`, the optional public logo and sanitized build evidence; it may be removed with temporary storage. A configured `$DOTS` still controls optional-logo lookup. The active `bin/dots` and its directory flags are unchanged.

PowerShell uses `python -B tools/verify_core.py build` to obtain the separate `.exe` path:

```powershell
$dev = python -B tools/verify_core.py build
if ($LASTEXITCODE -ne 0) { throw "Development build failed" }
& $dev --help
& $dev --version
& $dev doctor --json
```

Run `python3 -B tools/verify_core.py check` for isolated validation and `python3 -B tools/verify_core.py bench` for warm startup and registry measurements (`python` on Windows). Checks additionally need installed gofmt/readelf or LLVM; benchmarks need hyperfine. Missing tools are reported without installation. See [testing](docs/testing.md#permanent-core-verification) and [the first-slice results](plans/phase-2-command-center.md). No external command execution, completion, installation, manifest, transaction, bootstrap, or release functionality is included.

## Try the Portability Experiment

**Implemented, experimental:** help, version output, and read-only platform diagnostics, verified natively on Termux Android/ARM64 and on Linux/AMD64 and Windows/AMD64 in GitHub Actions. The live `dots` command and dotfiles are unchanged. Linux and Windows CI results establish execution on the recorded runners; bounded distribution bundles have also been packaged, verified, extracted, and executed natively on all three targets. The minimal bundle direction and publisher-authentication requirement are accepted, but permanent release tooling, the signing mechanism, and production support remain pending.

From the repository root, using the verified Go 1.27.1 toolchain and Python 3 without optimization (`PYTHONOPTIMIZE` unset or `0`; no `-O`/`-OO`). The verifier rejects optimized Python before invoking tools or creating build artifacts:

```bash
DOTS_SPIKE_BIN="$(python3 experiments/go-portability/tools/verify.py build)"
DOTS="$PWD" "$DOTS_SPIKE_BIN" --help
"$DOTS_SPIKE_BIN" --version
"$DOTS_SPIKE_BIN" doctor
"$DOTS_SPIKE_BIN" doctor --json
```

The build command prints the executable path on stdout and progress on stderr. It retains the binary, a public logo copy, and `evidence.json` in a unique directory under the temporary directory. Tool caches and build work are disposable; nothing is installed or added to `PATH`, and no dependencies are downloaded. Temporary artifacts may be removed by the system; rebuild when needed.

The preserved experimental help still says “Go remains provisional”; that historical banner does not reflect the later adoption decision. It is unchanged to preserve the verified executable and evidence.

Help loads the optional `logo.txt` from `$DOTS` or, when unset, beside the executable's parent `bin/` directory. Missing or unusable logos are omitted, and valid file symlinks are supported. Version and diagnostic output contain no logo. Diagnostics reports candidate paths and `not_probed` filesystem capabilities; it does not create files, load configuration contents, or apply changes.

Run focused checks or startup measurements with:

```bash
python3 experiments/go-portability/tools/verify.py check
python3 experiments/go-portability/tools/verify.py bench
```

Checks additionally use installed `gofmt` and `readelf` on Unix or `llvm-readobj` on Windows; measurements use installed `hyperfine`. Missing prerequisites are reported without installation. See the [experiment plan and results](plans/phase-1-portability.md), [testing instructions](docs/testing.md), and [platform evidence](docs/platforms.md). Linux/Windows compilation does not establish that those artifacts run on their target platforms.

The Windows harness accepts native Windows/AMD64. With Go and Python already installed, PowerShell can build and try the separate executable:

```powershell
$spike = python experiments/go-portability/tools/verify.py build
if ($LASTEXITCODE -ne 0) { throw "Experimental build failed" }
& $spike --help
& $spike --version
& $spike doctor --json
python experiments/go-portability/tools/verify.py check
```

Windows diagnostics explicitly leave known-folder resolution unimplemented and filesystem capabilities unprobed. Link tests report actual availability without changing security policy; copy checks run independently.

The experimental distribution check builds, packages, verifies, extracts, and runs the native executable in disposable directories:

```bash
python3 experiments/go-portability/tools/verify.py dist
```

In PowerShell use `python experiments/go-portability/tools/verify.py dist`. This additionally needs installed Git. It uses the **committed** public logo, preserving and excluding any local logo edit. Go source inputs must match the recorded commit. Bundles contain the executable under `bin/`, the logo, and `bundle.json`; an external `SHA256SUMS` covers the `.tar.gz` (Termux/Linux) or `.zip` (Windows). The printed executable path belongs to the retained temporary artifact; bundles, checksums, and CLI logs are under its sibling `distribution/` directory. Nothing is installed. Checksums establish agreement with the supplied manifest, not publisher authentication. See the [distribution guarantees and limitations](docs/testing.md#experimental-distribution-check).

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
