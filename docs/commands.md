# Command Model

**Status: Experimental interface implemented below; production command model proposed**

This is the design source for the future CLI until a validated command registry becomes authoritative. The current `bin/dots` prototype does not implement this command set.

## Implemented Bash Prototype

`bin/dots` supports no arguments, `help`, `-h`, and `--help` for help. `-d`/`--dir` prints `$DOTS`; preceding it with `-r`/`--raw` disables home abbreviation. Unknown input prints an error and help to stderr and exits 1. It has no version or diagnostic command. This behavior remains separate from the experiment.

## Implemented Experimental Interface

The isolated `dots-spike` executable is built explicitly using the [README instructions](../README.md#try-the-termux-experiment). It implements only:

| Invocation | Behavior |
| --- | --- |
| No arguments, `help`, `-h`, `--help` | Human help with the optional logo, on stdout |
| `--version` | One line: `dots-spike 0.0.0-spike <Go version> <GOOS>/<GOARCH>`; no logo or repository inspection |
| `doctor` | Read-only platform evidence, quoted candidate paths, warnings, and unprobed capabilities |
| `doctor --json` | A single JSON report without a logo, ANSI styling, or diagnostic text on stdout |
| `doctor -h`, `doctor --help` | Contextual help with the optional logo; does not run diagnostics |

Extra arguments and unimplemented commands are rejected, including `version`, `completion`, `apply`, and the prototype's directory flags. Exit codes are 0 for successful output (including diagnostic reports with warnings or unknown platforms), 1 for output failure, and 2 for unsupported arguments. Usage errors go to stderr without echoing potentially sensitive argument values. This mapping does not settle future apply/undo statuses.

Help follows the prototype's logo lookup: if `$DOTS` is nonempty, read its `logo.txt`; otherwise resolve executable symlinks and look in the executable directory's parent. A configured but missing logo does not fall back to another repository. The harness provides an artifact `bin/dots-spike` and parent `logo.txt`. Empty, unreadable, missing, broken-link, or non-regular logos are silently omitted. The experiment also omits logos larger than 64 KiB to bound help work. Content is preserved, its final line terminated if necessary, and a separating newline added. Only successful help requests read the logo. The loader checks the pathname, then validates the opened file handle before reading. On Unix it opens in nonblocking mode so replacement with a FIFO between the checks does not wait for a writer; valid symlinks to regular files still work. This is not a general timeout for filesystem path lookup or regular-file I/O. No recursive repository search or Git invocation occurs.

The small table in `internal/cli/cli.go` is the source for accepted built-in names and help descriptions; tests check metadata completeness, name collisions, and advertised entries. Full discovery, generated Markdown, and shell completion remain Phase 2 proposals. The experiment provides no completion command or installation, and tests explicitly reject that route. No extension metadata carrier has been selected.

### Experimental Diagnostic JSON Schema 1

The fixed top-level keys are `schema_version`, `platform`, `os`, `architecture`, `go_version`, `evidence`, `paths`, `capabilities`, and `warnings`. `evidence` and `warnings` are arrays; `paths` and `capabilities` are objects, never null. Available path candidates are included; unavailable paths are omitted with warnings where applicable. `capabilities` contains `file_symlink`, `directory_symlink`, and `copy`, all set to `not_probed`. Detection and path limitations are defined in [platforms.md](platforms.md). This schema describes the experiment, not a resolved specification or transaction state.

## Interface Shape

Users interact with space-separated routes:

```text
dots status
dots files list
dots themes apply tokyonight
```

External command files use an Omarchy-inspired hyphenated form:

```text
dots-files
dots-themes-apply
```

For `dots themes apply tokyonight`, the dispatcher searches from the longest candidate toward the group command. If `dots-themes-apply` exists, it receives `tokyonight` unchanged.

## Command Classes

| Class | Ownership | Intended use |
| --- | --- | --- |
| Core built-in | Compiled core | Safety, state, specification, dispatcher, and lifecycle operations |
| Official external | Repository `commands/` | Cohesive features that do not need to live in the core binary |
| User external | Explicit configured directory | Personal commands using the documented extension contract |
| Compatibility route | Registry alias or shim | Temporary preservation of an established older command name |

Built-ins cannot be shadowed silently. Search precedence and trust must be explicit before user extension discovery is enabled.

## Proposed Top-Level Commands

| Route | Purpose | Initial milestone |
| --- | --- | --- |
| `dots status` | Show selection, repository state, drift, broken links, and pending changes | Termux MVP |
| `dots spec` | Show the fully resolved desired specification and provenance | Resolver |
| `dots plan` | Produce the operation plan without mutation | Transaction foundation |
| `dots apply` | Apply an approved plan as a transaction | Transaction foundation |
| `dots undo` | Validate and reverse a recorded transaction | Transaction foundation |
| `dots history` | List and inspect transactions and backups | Transaction foundation |
| `dots doctor` | Report platform, paths, capabilities, requirements, and recovery issues | Limited diagnostics in Phase 1 experiment; full route at resolver |
| `dots files` | Inspect, edit, diff, and adopt managed files | Termux MVP |
| `dots links` | Inspect, check, and repair managed links | Termux MVP |
| `dots scripts` | Discover, run, edit, and optionally expose repository scripts | Later MVP |
| `dots shells` | Inspect and configure shell integrations | Later MVP |
| `dots themes` | Inspect, preview, and apply coordinated themes | Later |
| `dots packages` | Inspect and install normalized package sets | Bootstrap/packages |
| `dots env` | Inspect and generate shell-specific environment integration | Later MVP |
| `dots backup` | Inspect, create, restore, and prune explicit snapshots and transaction backups | Transaction foundation |
| `dots profiles` | List, inspect, select, and explain profile composition | Resolver |
| `dots config` | Locate, inspect, edit, get, set, and validate configuration | Resolver |
| `dots commands` | Discover, validate, and serialize command metadata | Dispatcher |
| `dots completion` | Generate or install shell completion definitions | Dispatcher |
| `dots repo` | Inspect and deliberately synchronize the main repository | Bootstrap/packages |
| `dots sources` | Inspect and synchronize optional, private, or third-party sources | Later |
| `dots self` | Install, update, and diagnose the CLI executable itself | Releases |
| `dots version` | Show CLI, schema, repository, and build information | Dispatcher |

The table describes intended vocabulary, not current availability. Update milestone ownership as implementation plans evolve.

## Lifecycle Semantics

Avoid using `install`, `update`, or `sync` without a qualifying object.

| Operation | Meaning |
| --- | --- |
| `dots bootstrap` or remote bootstrap script | Prepare a fresh machine and hand control to the installed CLI |
| `dots self install` | Install the CLI executable |
| `dots self update` | Update the CLI executable |
| `dots repo pull` | Fetch and integrate repository changes under explicit Git safety rules |
| `dots sources sync` | Fetch selected optional/private source revisions |
| `dots packages install` | Install missing packages selected by the specification |
| `dots apply` | Reconcile managed machine state with the resolved specification |

A future orchestrated workflow may call several stages, but it must show those stages and preserve their individual logs and failure boundaries.

## Resource Group Sketches

These routes are draft and should be reduced or adjusted before implementation rather than implemented mechanically.

### Files

```text
dots files list
dots files show <resource>
dots files edit <resource>
dots files diff [resource]
dots files adopt <path> [--module <name>]
dots files source <resource>
dots files target <resource>
```

### Links

```text
dots links list
dots links check [resource]
dots links repair [resource]
```

`repair` must still generate and apply a transaction plan. It is not permission to replace arbitrary links directly.

### Profiles

```text
dots profiles list
dots profiles show [name]
dots profiles use <name>
dots profiles explain [resource]
```

Platform is detected context, not a profile, though bootstrap may accept a compatibility shortcut such as `--platform termux`.

### Backup and History

```text
dots history list
dots history show <transaction>
dots undo <transaction>
dots backup list
dots backup show <backup>
dots backup restore <backup>
dots backup prune
```

Automatic transaction backups and explicit snapshots may share storage infrastructure, but their retention and restoration semantics must remain distinguishable.

## Proposed Global Options

The exact spelling remains draft. Apply the same semantics consistently rather than allowing each command to reinterpret them.

| Option | Meaning |
| --- | --- |
| `-h`, `--help` | Contextual help for the resolved route |
| `--version` | Version output without full initialization |
| `--json` | Structured output with decoration disabled |
| `--no-color` | Disable ANSI styling |
| `-q`, `--quiet` | Suppress nonessential human output, not errors |
| `-v`, `--verbose` | Add diagnostic context without revealing secrets |
| `--repo <path>` | Override repository for this invocation |
| `--profile <name>` | Override selected profile for this invocation |
| `--host <name>` | Override selected host layer |
| `--platform <name>` | Override detection for testing or deliberate advanced use |
| `--offline` | Refuse network-dependent work |
| `--yes` | Approve the already displayed or persisted plan in non-interactive flows |

Do not make `--force` a universal bypass. Force behavior must be scoped to the operation whose safety check it overrides and documented in `safety.md`.

## Metadata

The metadata carrier remains undecided. The model must support:

| Field | Requirement |
| --- | --- |
| Route | Canonical space-separated user route |
| Binary | Executable or built-in implementation identifier |
| Summary | One-line discovery description |
| Arguments | Usage synopsis, with optionality represented consistently |
| Examples | Executable examples or clearly labeled conceptual examples |
| Platforms | Required platform or normalized capabilities |
| Hidden | Omit internal commands from ordinary discovery |
| Aliases | Compatibility only, never a substitute for choosing a clear canonical name |
| Output formats | Supported structured formats and schema version |
| Mutation class | Read-only, planned mutation, external side effect, or privileged operation |

Possible carriers include comment headers for scripts, sidecar TOML for any executable, and a metadata handshake for compiled plugins. The final design must allow command validation without executing untrusted plugin logic.

## Discovery

The proposed discovery surface is:

```text
dots commands
dots commands --all
dots commands --json
dots commands --markdown
dots commands --check
```

`--check` should detect at least missing summaries, invalid metadata, duplicate routes, unsupported interpreters, impossible platform declarations, and attempts to shadow protected built-ins.

## Help

- `dots --help` lists stable common commands and discoverable groups.
- `dots <group> --help` lists routes in that group.
- `dots <route> --help` renders metadata and command-specific details without executing the command's normal behavior.
- Help must distinguish unavailable-on-this-platform from unknown.
- Help must distinguish proposed documentation from implemented commands during development; the shipped CLI lists only implemented registry entries.

## Structured Output

Structured output is an API.

- Use valid JSON without ANSI sequences, banners, progress bars, or diagnostic text on stdout.
- Include a schema version once consumers may persist or parse output.
- Use stable identifiers rather than localized display labels.
- Represent warnings, blocked operations, and partial reversibility explicitly.
- Send debug and diagnostic logs to stderr.

## Exit Status Draft

Exit statuses need a final decision before public automation examples are published. The model should distinguish:

- Success or no drift.
- Valid request with detected drift or pending changes for check-style commands.
- Usage error.
- Specification or validation error.
- Conflict or blocked plan.
- Apply failure with successful rollback.
- Apply failure requiring recovery.
- Command unavailable on this platform.
- Unknown command or missing executable.

Record the final stable mapping in this document and in machine-readable command documentation.
