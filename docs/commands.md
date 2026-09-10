# Command Model

**Status: Development built-ins and bounded external protocol implemented; production command family proposed**

The permanent built-in table in `internal/cli/cli.go` is authoritative for its implemented surface. This document remains the design source for the broader future CLI. The current `bin/dots` prototype does not implement this command set.

## Implemented Bash Prototype

`bin/dots` supports no arguments, `help`, `-h`, and `--help` for help. `-d`/`--dir` prints `$DOTS`; preceding it with `-r`/`--raw` disables home abbreviation. Unknown input prints an error and help to stderr and exits 1. It has no version or diagnostic command. This behavior remains separate from the experiment.

## Permanent Development Interface

The root module builds `cmd/dots` into a separate test-owned executable, never `bin/dots`. It implements the same bounded read-only requests as the experiment below, with `dots` branding and `--version` output `dots 0.0.0-dev <Go version> <GOOS>/<GOARCH>`. Help identifies it as a development binary and renders its entries from the validated registry. The bounded external interface below adds `commands` and static `completion zsh`; no `version` token route or managed mutation is enabled. The live prototype's directory flags remain exclusive to that prototype.

No arguments select help. `help`, `-h`, and `--help` display global help; `doctor -h` and `doctor --help` display contextual help without running diagnostics. `doctor` and `doctor --json` report the same candidate-path and `not_probed` capability model, diagnostic schema 1, and Windows missing-path warning as the experiment. Version and JSON never read the logo. Built-in extra/unknown arguments are rejected without echoing their values. Core exit codes are 0 for success, 1 for output/validation/access/launch failure, and 2 for usage/unknown routes; native external exit status is propagated. Future managed-operation statuses remain undecided.

The optional logo retains the experiment's bounded handle validation, Unix nonblocking opening, DOTS-first lookup and executable-symlink-relative fallback. Only successful help reads it. Registry construction/lookup does not inspect the repository, load configuration, scan PATH, or collect platform evidence. See the [core verification instructions](testing.md#permanent-core-verification) and [first-slice plan](../plans/phase-2-command-center.md).

### Built-in Metadata Contract

`internal/dispatch.Metadata` is the private typed carrier accepted for this slice under [decision 0002](decisions/0002-phase-1-go-adoption.md). It is not a public discovery schema or an extension metadata format.

| Field | Implemented meaning |
| --- | --- |
| `ID` | Unique handler identity, bound to a non-nil `Entry.Handler` |
| `Route` | Canonical token sequence; empty only for global-only entries such as `--version` |
| `GlobalOptions` | Separate dash-prefixed invocation spellings; they do not expose a `version` token route |
| `Aliases` | Compatibility token routes, validated in the same collision namespace as canonical routes |
| `Summary`, `Synopsis`, `Examples` | Required help text and executable examples |
| `Platforms`, `Capabilities` | Explicit platform IDs or sole wildcard `*`, plus injected required capability identifiers |
| `Hidden` | Omit from normal help without changing lookup |
| `Outputs` | Unique `text` (schema 0) or `json` (positive schema version) descriptors |
| `Mutation` | Only `read-only` accepted in this slice |

`dispatch.New` validates the complete table before exposing handlers: duplicate IDs/routes/aliases/options, invalid route tokens, missing/default metadata, unsupported platforms/outputs/mutation classes, and nil handlers are refused. The default entry is help. All shipped entries declare `*` and no required capabilities, so startup never needs platform collection to resolve a route.

An in-memory token tree chooses the deepest exact built-in match and forwards the remaining argument slice unchanged. The chosen handler validates its arguments. Global options are resolved separately. Injected unavailable-platform/capability cases produce `ErrUnavailable`, distinct from `ErrUnknown`; no shipped command requires a probe or uses this distinction to claim new platform support. Direct lookup depends on argument depth, not repository or registry size.

`Project` returns an ordered defensive metadata copy for help and future renderers. Tests cover help/example agreement and projection mutation isolation. The schema-1 catalog uses this projection. The Zsh generator shares the in-memory catalog builder; Markdown-command-reference generation remains deferred.

## Development External Protocol

[Accepted decision 0003](decisions/0003-trusted-external-command-protocol.md) is the normative protocol, including the exact protected namespace list and resource limits. No real management extension ships with this slice.

```text
dots --command-dir <absolute-trusted-root> [--command-dir <another-root>] commands
dots --command-dir <absolute-trusted-root> commands --check
dots --command-dir <absolute-trusted-root> files --help
dots --command-dir <absolute-trusted-root> files -- --help
```

The `files` examples require an explicitly supplied `dots-files` executable (Windows: `dots-files.exe`) and `dots-files.json`. They are protocol examples, not shipped dotfile commands. There is no implicit PATH, DOTS, repository, installation or current-directory search. Roots are prefix-only, repeatable up to eight, and must be absolute existing directories when external access is needed. Missing option values are usage errors. Built-ins resolve before directory health is checked. Duplicate root identities and duplicate routes fail; root order never shadows a definition.

Schema 1 requires exactly these keys (example for a disposable read-only fixture):

```json
{
  "schema_version": 1,
  "route": ["probe"],
  "summary": "Disposable verification fixture",
  "synopsis": "probe [args]",
  "examples": ["dots probe --"],
  "platforms": ["termux", "linux", "windows"],
  "hidden": false,
  "outputs": [{"format": "text", "schema_version": 0}],
  "mutation": "read-only",
  "aliases": [],
  "capabilities": []
}
```

The filename must be `dots-probe.json`; the executable is derived from that route. Reject missing/unknown/duplicate keys, null, trailing JSON, invalid UTF-8, invalid display text, over-limit data, and route/basename mismatches. Mutation/output/platform declarations are assertions by trusted authors, not sandbox guarantees. Unix files require execute bits and native OS execution; Windows accepts only native `.exe` files using Go's CommandLineToArgvW-compatible argument convention. No interpreter inference or script-suffix launch is implemented. Windows roots are limited to local fixed-drive, case-insensitive NTFS; WSL execution is deferred.

Candidate routing is pure and bounded; filesystem access happens in the separate resolver. Probe longest route first across all roots at each depth. Existing malformed, unavailable or unsupported deeper definitions block shorter fallback. Direct dispatch/help performs targeted probes only; explicit `commands` enumeration is bounded, sorted, and fails without partial output. Hidden definitions are omitted from ordinary listing but checked by `--check`. Valid foreign-platform definitions are listed as unavailable; `--check` tolerates an intentionally foreign declaration but refuses a missing/unsupported executable declared for the current platform.

For external routes, any `-h` or `--help` before the first `--` selects static metadata help. A `--` stops matching and is itself forwarded; help flags after it are literal. All remaining values, environment, cwd and actual standard streams pass through unchanged. Extensions receive no shell expansion or output rewriting. Unix replaces the dispatcher process; Windows waits in the shared console and preserves child exit status after Ctrl+C/Ctrl+Break. Unsupported input is 2; metadata/root/conflict/entry/unavailable/unsupported/launch failures are 1 with distinct fixed diagnostics. Static help/discovery never execute extensions. There is no persistent cache. Zsh generation is specified below. The JSON catalog below is a separate rendering of ordinary discovery.

## Machine-Readable Command Catalog

`dots commands --json` is implemented for the development executable. Prefix it with repeated explicit `--command-dir` roots to include external definitions. With no roots it returns only the registered built-ins without implicit search or platform collection. It uses the same projections and ordinary discovery as text listing, never extension execution.

[Decision 0004](decisions/0004-versioned-command-discovery.md#catalog-schema-1) owns the complete public schema, ordering and compatibility rules. The envelope has integer `schema_version: 1` and a `commands` array; each record includes kind/ID, route/global spellings/aliases, descriptive metadata, declared platforms/capabilities/outputs/mutation, hidden status and static availability. Arrays are never null. External IDs join canonical route tokens with hyphens. Version remains a global-only entry, not a `dots version` route. Available records have a null reason; unavailable records have typed stable reason codes.

JSON includes hidden and valid unavailable records; human listing continues filtering hidden entries. Unavailability is static eligibility, not proof of successful execution or authenticated/sandboxed code. No resolved executable/root paths are added. Metadata descriptions are author-provided text. Command inventory changes do not change schema version; breaking structure or field meaning does. Zsh generation consumes the same in-memory records. Argument grammar and Markdown generation remain deferred.

Successful JSON is a complete two-space-indented object and final newline on stdout, with no logo or stderr. `--json` is mutually exclusive with all other commands flags, including `--check`; repeated/extra flags and prefix syntax/root-count errors return 2. Discovery validation, collisions, inaccessible/invalid entries and discovery resource limits return 1 with empty stdout and fixed stderr diagnostics. Hidden metadata is validated too. Serialization completes before writing; writer errors return 1 when reported to the CLI and may leave incomplete output. Native signal termination is unchanged. No JSON error envelope is emitted. Existing `--check` semantics and built-in/help precedence remain unchanged.

## Static Zsh Completion

`dots completion zsh` emits a complete native Zsh script to stdout. `completion -h` and `completion --help` show help without checking root health. Source the generated script only in a shell where `compinit` has already initialized completion. The generator does not initialize or install anything. See [decision 0005](decisions/0005-static-zsh-completion.md) for the exact contract and [README](../README.md#disposable-zsh-completion-demo) for an isolated example.

The shared catalog builder validates all selected definitions before output, then the renderer omits hidden/unavailable entries and includes canonical routes, represented aliases, intermediate prefixes and represented global spellings. No `version` route or inferred flags/values are added. `synopsis` and examples are descriptions, not argument grammar: even known `--json`/`--check` flags and the `zsh` argument are outside completion until represented structurally.

Explicit prefix `--command-dir` roots create an external snapshot. Completion compares the exact ordered root argument strings (decoded shell quoting, no expansion or path normalization) against the embedded generation context. Different count, order, case, trailing separators or alias spelling falls back to built-ins only. While entering a root value or after malformed/excess prefix pairs, completion returns nothing. Prefix options are recognized only before a route. After `--` or a completed token outside the known route tree, it returns nothing; terminal routes offer only known deeper routes.

Generation, loading and completion execute no extensions. The generated function uses embedded arrays and Zsh builtins without invoking dots, Git, JSON tools or filesystem discovery. Root strings are safely quoted literals in the script, while descriptive metadata is omitted. Snapshots require explicit regeneration after changes; execution still revalidates real roots.

Success is script-only stdout, no logo/stderr, exit 0. Unsupported shell/extra arguments and prefix syntax failures return 2; discovery validation/access/collision/limit and writer failures return 1. Validation failures produce empty stdout; writer failure may leave incomplete output. Bash/Fish/PowerShell, installation and richer argument metadata remain deferred.

## Implemented Experimental Interface

The isolated `dots-spike` executable is built explicitly using the [README instructions](../README.md#try-the-portability-experiment). It implements only:

| Invocation | Behavior |
| --- | --- |
| No arguments, `help`, `-h`, `--help` | Human help with the optional logo, on stdout |
| `--version` | One line: `dots-spike 0.0.0-spike <Go version> <GOOS>/<GOARCH>`; no logo or repository inspection |
| `doctor` | Read-only platform evidence, quoted candidate paths, warnings, and unprobed capabilities |
| `doctor --json` | A single JSON report without a logo, ANSI styling, or diagnostic text on stdout |
| `doctor -h`, `doctor --help` | Contextual help with the optional logo; does not run diagnostics |

Extra arguments and unimplemented commands are rejected, including `version`, `completion`, `apply`, and the prototype's directory flags. Exit codes are 0 for successful output (including diagnostic reports with warnings or unknown platforms), 1 for output failure, and 2 for unsupported arguments. Usage errors go to stderr without echoing potentially sensitive argument values. This mapping does not settle future apply/undo statuses.

Help follows the prototype's logo lookup: if `$DOTS` is nonempty, read its `logo.txt`; otherwise resolve executable symlinks and look in the executable directory's parent. A configured but missing logo does not fall back to another repository. The harness provides an artifact `bin/dots-spike` and parent `logo.txt`. Empty, unreadable, missing, broken-link, or non-regular logos are silently omitted. The experiment also omits logos larger than 64 KiB to bound help work. Content is preserved, its final line terminated if necessary, and a separating newline added. Only successful help requests read the logo. The loader checks the pathname, then validates the opened file handle before reading. On Unix it opens in nonblocking mode so replacement with a FIFO between the checks does not wait for a writer; valid symlinks to regular files still work. This is not a general timeout for filesystem path lookup or regular-file I/O. No recursive repository search or Git invocation occurs.

The small table in `experiments/go-portability/internal/cli/cli.go` is the source for accepted built-in names and help descriptions; tests check metadata completeness, name collisions, and advertised entries. The permanent core implements discovery and bounded Zsh generation separately; generated Markdown remains proposed. The experiment provides no completion command or installation, and tests explicitly reject that route. The experiment does not implement the later permanent external metadata carrier.

### Experimental Diagnostic JSON Schema 1

The fixed top-level keys are `schema_version`, `platform`, `os`, `architecture`, `go_version`, `evidence`, `paths`, `capabilities`, and `warnings`. `evidence` and `warnings` are arrays; `paths` and `capabilities` are objects, never null. Available path candidates are included; unavailable paths are omitted with warnings where applicable. `capabilities` contains `file_symlink`, `directory_symlink`, and `copy`, all set to `not_probed`. Detection and path limitations are defined in [platforms.md](platforms.md). This schema describes the experiment, not a resolved specification or transaction state.

## Interface Shape

The [accepted next implementation boundary](decisions/0002-phase-1-go-adoption.md#next-bounded-implementation-task) is implemented for the read-only built-in registry. The bounded external protocol is implemented under decision 0003. Schema-1 JSON discovery and bounded Zsh completion generation are implemented. Other completion renderers, real management commands and installation remain deferred; live and experimental interfaces are unchanged.

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

Built-ins cannot be shadowed silently. The development protocol uses only explicit roots and refuses duplicates; official installation/configured roots remain proposed.

## Proposed Top-Level Commands

| Route | Purpose | Initial milestone |
| --- | --- | --- |
| `dots status` | Show selection, repository state, drift, broken links, and pending changes | Termux MVP |
| `dots spec` | Show the fully resolved desired specification and provenance | Resolver |
| `dots plan` | Produce the operation plan without mutation | Transaction foundation |
| `dots apply` | Apply an approved plan as a transaction | Transaction foundation |
| `dots undo` | Validate and reverse a recorded transaction | Transaction foundation |
| `dots history` | List and inspect transactions and backups | Transaction foundation |
| `dots doctor` | Report platform, paths, capabilities, requirements, and recovery issues | Read-only candidate diagnostics implemented; full route at resolver |
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
| `dots completion` | Generate shell completion definitions; installation deferred | Zsh generation implemented |
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

The development sidecar format is fixed below. The following broader production metadata model remains proposed:

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

Schema 1 uses mandatory JSON sidecars, without a runtime handshake. Richer mutation classes, aliases and capability requirements require a later decision.

## Discovery

`commands`, `commands --json` and `commands --check` are implemented. `--all` and `--markdown` below remain proposed:

```text
dots commands
dots commands --all
dots commands --json
dots commands --markdown
dots commands --check
```

`--check` should detect at least missing summaries, invalid metadata, duplicate routes, unsupported interpreters, impossible platform declarations, and attempts to shadow protected built-ins.

## Future Help

Recursive group help remains proposed. Current global help is built-in-only; external help is targeted and static as specified below.

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
