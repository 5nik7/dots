# Command Model

**Status: Bash command framework and separate Go development interfaces implemented; broader managed command family proposed**

The permanent built-in table in `internal/cli/cli.go` is authoritative for its implemented surface. This document remains the design source for the broader future CLI. The live Bash framework implements dispatch, file inventory and bounded theme workflows; the broader managed command set remains proposed.

The existing Zsh helper `mkcd <directory>` is separate from the `dots` command family. Its [usage and path handling](../README.md#zsh-configuration) are implemented by `scripts/mkcd`, sourced through the Zsh function to change the current shell's directory.

## Implemented Files and Theme Routes

The [files reference](files.md) defines `dots files sources|discover|list|locate|show|source|target|track`,
filters, sorting and schema-1 JSON. `track` changes catalog metadata only; bounded
managed operations are documented separately below. The [themes reference](themes.md) defines
`dots theme list|show|current|dir|color|set|refresh|init|switcher|install|update|remove`
and `dots theme bg list|current|set|next|select|switcher`. The plural `dots themes`
commands retain their documented native palette interfaces. Shell completion reads
static route metadata and core-owned data providers; it never executes extensions.

## Implemented Git and managed-file operations

The [Git reference](git.md) defines `dots git status|publish|sync`, recursive
semantics, configuration, compact views and JSON. Git synchronization now belongs
to `dots git sync`; the former proposed `dots repo pull` spelling is superseded.
This remains distinct from future bootstrap and optional-source resolution.

The [files reference](files.md) also defines `locations`, `discover --system`,
`add`, `link`, `remove`/`rm`, `history`, `undo`, `recover` and
`backups list|show|restore`. Metadata-only `track` and existing inventory formats
remain compatible. These operations do not implement the future global
`dots apply`, `undo`, `history` or `backup` namespaces.

`files discover --system` groups config candidates by directory by default and
summarizes managed/excluded entries. `--verbose` shows individual files and source
mappings; `--all` includes the summarized statuses. Both flags require `--system`.
`--repo` filters owners, and `--json` always emits complete schema-1 `items` without
human grouping/filtering or decoration. Repository discovery keeps its existing
filters and format; see [files](files.md#user-configuration-discovery).

## Implemented Bash Command Framework

The live `bin/dots` follows [decision 0006](decisions/0006-bash-command-framework.md).
It requires Bash 4.4+. The Go interfaces below remain separate and paused.

### Routing and Roots

`dots-themes-apply` is callable as `dots themes apply`. Filenames use lowercase
segments matching `[a-z][a-z0-9]*`, separated by hyphens. Probe the longest initial
sequence of route words first, stopping at a flag, `--`, or another non-route
word; remaining arguments, including `--`, pass unchanged. Execute the selected
file directly with its shebang; no shell inference, output interception, or
argument evaluation occurs. Extension status and standard handles are preserved.

Search `$DOTS/bin`, `$DOTS/local/bin`, and repeated prefix
`--command-dir ABSOLUTE_DIRECTORY` additions. Missing default directories are
optional; explicit directories must exist. The same directory selected through
multiple aliases is searched once. `$DOTS` selects the repository; when unset,
infer it from the dispatcher location, resolving executable symlinks. Internal
libraries always come from the dispatcher installation. No PATH-wide or recursive
search occurs. Executable symlinks to regular files are allowed. Duplicate routes
across distinct roots fail; a nonexecutable or broken deeper candidate blocks
fallback. Roots are trusted execution inputs, not a sandbox.

The protected first tokens are `help`, `doctor`, `commands`, `completion`,
`version`, `status`, `spec`, `plan`, `apply`, `undo`, `history`, `backup`, `config`,
`bootstrap`, and `self`, plus the private `__complete` endpoint. Reserved but
unimplemented routes remain unavailable. Reservations do not add features.

### Public Interface

- `dots`, `dots help`, `dots -h`, `dots --help`: global help and visible commands.
- `dots help ROUTE...`, `dots ROUTE... --help`: static contextual help without
  executing an extension. A help flag before the first `--` is intercepted;
  after `--` it belongs to the extension. Groups show their visible descendants, including groups with an executable. An executable group runs normally when called without help.
- `dots commands`: visible built-ins and external commands in deterministic
  root/directory order. `dots commands --check` validates every definition,
  including hidden commands, and reports success only after complete validation.
- `dots completion bash|zsh|fish`: print the native adapter, without installation.
- `dots [-r|--raw] -d|--dir`: repository path, abbreviated beneath HOME unless raw.
- Prefix `--color=auto|always|never` and `--icons=auto|always|never`: presentation.
  Flags after the route belong to the extension, except intercepted help.

Success is 0. Unknown routes, collisions, malformed metadata, and access errors
are 1. Invalid dispatcher syntax is 2. `exec` launch failures retain Bash's
126/127 behavior. No `--version`, JSON catalog, or management operation is added.

### Optional Metadata

Read the initial shebang/comment/blank-line header only, up to 128 lines and
16 KiB. Stop at the first code line. Metadata is literal text, never sourced.
Control characters are refused in declarations; CRLF line endings are accepted.
Routes come from filenames, not headers. Missing declarations get generic help;
malformed declarations fail help/discovery/validation but do not block ordinary
direct execution. Discovery validates before emitting its catalog.

```bash
#!/usr/bin/env bash
# dots:summary=Manage example themes
# dots:usage=[OPTIONS] DIRECTORY
# dots:example=dots themes --flavor mocha ./themes
# dots:option=--flavor|-f|choice:mocha,latte|Palette flavor
# dots:option=--verbose|-v|flag|Verbose output
# dots:argument=1|directory|Theme directory
# dots:hidden=false
```

This is an authoring example, not a shipped theme command. `summary`, `usage`,
and `hidden` may appear once; `example`, `option`, and `argument` repeat. Unknown
fields fail validation. `hidden` is `true` or `false`, defaulting to false.

Option records are `LONG|SHORT|TYPE|DESCRIPTION`, with an empty SHORT allowed.
Long names use `--[a-z][a-z0-9-]*`; short names are one alphanumeric character
preceded by `-`. Option names must be unique. Positional records are
`POSITION|TYPE|DESCRIPTION`: positions start at 1 and are contiguous; a final `*`
applies to remaining positions. Types are `flag` (options only), `string`, `file`,
`directory`, `choice:VALUE,VALUE`, or the core-owned theme data types
`theme`, `flavor`, `palette-color`, `color-format`, `theme-id`, `file-resource`, and
`file-repository`. The latter three read flat theme IDs and qualified catalog IDs. Flavor/color providers
use preceding positional theme/flavor arguments; they read data and never execute
extensions. Fields cannot contain `|`; choice values
cannot contain commas. Descriptions are required. No code callbacks, aliases,
implicit option grammar, or combined-short-option parsing are provided.

### Presentation Helpers

The [presentation contract](presentation.md) defines the required visual language and acceptance gate for every new or changed first-party human view. The helpers and controls below are implemented; broader adoption follows each command's authorized implementation scope.

Bash extensions may `source "$DOTS_LIB_DIR/ui.bash"` when launched through dots.
The sourceable helpers are `dots::heading`, `dots::row`, `dots::kv`, `dots::info`,
`dots::success`, `dots::warning`, and `dots::error`. Rows/kv take label and value;
other helpers take message text. Warnings/errors write stderr, other helpers
stdout. Directly invoked standalone extensions must locate/source the library
explicitly if `DOTS_LIB_DIR` is absent.

`DOTS_COLOR` and `DOTS_ICONS` default to `auto`; explicit prefix flags override
them and are exported to extensions. Automatic color requires the destination
stream to be a terminal, TERM other than dumb, and empty/unset NO_COLOR. Explicit
always can override NO_COLOR. Automatic icons require a usable terminal; there
is no font detection. Use `--icons=never` for ASCII status markers. Stdout and
stderr are styled independently. Directory output and completion data remain
plain. Shared helpers use Bash builtins and ANSI colors, not the shell startup
chain, theme generators, or the existing general-purpose util script.

Theme and file human views share this presentation policy. Terminal listings use
headings, status colors/icons, counts and readable paths; forced color or icons also
enable that layout when redirected. `NO_COLOR` disables automatic color while
retaining the terminal layout. `dots --color=never --icons=never ...` gives a plain
terminal view. Lists piped without forced decoration retain their existing line/TSV
formats. JSON, file source/target queries, theme current/dir/color/background-current
queries, shell initialization and completion keep their data format even when
color is forced (explicit ANSI color-value formats still return ANSI as requested).

`dots::human`, `dots::path` and `dots::swatch` support the Bash theme views. The
Python file catalog implements the same color/icon policy for its own output.
Completion explicitly requests undecorated catalog rows, regardless of global
presentation settings. Neither view loads shell configuration or introduces a
startup scan. Executable-group help lists static child metadata without running
commands, so `dots theme`, `dots files` and `dots theme bg` are discoverable menus.

### Completion

All adapters query the dispatcher on Tab, not on shell startup. A typed route prefix restricts metadata reads to matching filenames; an empty prefix enumerates the full catalog. New commands and
metadata edits are reflected on the next request. Hints cover route words,
built-in flags, declared extension options, fixed choices, and native shell
file/directory completion. Options consuming values, long `--name=value`, `--`,
and cursor position are respected. Completion handles literal quoting without evaluating shell substitutions. Unknown option grammar stops argument hints
rather than guessing. Undeclared arguments do not get inferred file candidates.
Descriptions are supplied where supported. Zsh menu labels show `value -- description`, padding names to a shared column
(including FZF-tab); accepting a match inserts only its value. Hidden routes are omitted from normal
suggestions, but explicit use remains possible.

Repository Bash startup sources its adapter; Zsh and Fish use their existing
completion directories. Zsh does not run another compinit. Fresh shells load the
new files; other installations can source the output of `dots completion SHELL`
using that shell's normal mechanisms. No live-home installation is performed.

The internal `__complete SHELL INDEX -- WORDS...` interface takes the command
word at index 0 and includes an empty current word when appropriate. It emits
literal tab-separated candidate/value/description records or file/directory
instructions; adapters never eval them. It is private to these adapters, not a
versioned public API. Failed queries produce no candidates or diagnostics.

## Permanent Development Interface

The root module builds `cmd/dots` into a separate test-owned executable, never `bin/dots`. It implements the same bounded read-only requests as the experiment below, with `dots` branding and `--version` output `dots 0.0.0-dev <Go version> <GOOS>/<GOARCH>`. Help identifies it as a development binary and renders its entries from the validated registry. The bounded external interface below adds `commands` and static `completion zsh`; no `version` token route or managed mutation is enabled. The live Bash framework's directory flags remain exclusive to that executable.

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
| `dots themes` | List, preview, query, initialize and select shared palettes | Bash implementation; broader app support later |
| `dots packages` | Inspect and install normalized package sets | Bootstrap/packages |
| `dots env` | Inspect and generate shell-specific environment integration | Later MVP |
| `dots backup` | Inspect, create, restore, and prune explicit snapshots and transaction backups | Transaction foundation |
| `dots profiles` | List, inspect, select, and explain profile composition | Resolver |
| `dots config` | Locate, inspect, edit, get, set, and validate configuration | Resolver |
| `dots commands` | Discover, validate, and serialize command metadata | Dispatcher |
| `dots completion` | Generate shell completion definitions; installation deferred | Zsh generation implemented |
| `dots repo` | Inspect future clone/bootstrap metadata; Git operations use `dots git` | Bootstrap/packages |
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
| `dots git sync` | Fetch and integrate repository changes under explicit Git safety rules (implemented) |
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

The exact spelling remains draft. Apply the same semantics consistently rather than allowing each command to reinterpret them. These options are not additions to the live Bash interface; it already uses prefix `--color=auto|always|never` and `--icons=auto|always|never`. Future human views must follow the [presentation contract](presentation.md).

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

For the paused Go development executable, recursive group help remains proposed. Its current global help is built-in-only; external help is targeted and static as specified below. The live Bash framework already implements static group help as documented above.

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

## Implemented Bash Theme Commands

The route, argument, format, compatibility and exit-status contract is maintained
in [Shared themes](themes.md#commands). Static headers on the official
`dots-themes-*` entry points drive dispatcher help and completion. The closed
palette providers augment that metadata with current theme files; they do not
introduce extension callbacks or change the Go protocol. `themes set` delegates
state publication to the shared helper described in [decision 0007](decisions/0007-data-driven-themes.md).
The supported families include hyphenated `rose-pine` identifiers and native palette
keys such as `sumiInk3`. All three shell providers discover their flavors/colors;
pywal16 flavor discovery works without its optional generated input. No new routes
or flags are needed for these families.

## Implemented Anodize commands

`dots anodize` and standalone `anodize` expose the same authoring commands. The complete [command and flag contract](anodize.md#commands-and-flags) covers modes, extract, create, import, list, show, edit, preview, export, apply and completion. `anodize completion bash|zsh|fish` (also `dots anodize completion`) emits standalone shell integration as plain source. Static choices cover extraction modes, adjustment/color keys, formats and apps; the `anodize-theme` metadata type supplies repository-owned authored theme IDs for edit. See the [completion and manual guide](anodize.md#shell-completion-and-manual). Static wrapper metadata supplies Dots help/discovery/completion without running the engine. Standalone `anodize --help` and `anodize COMMAND --help` use width-aware Dots presentation with command examples and option descriptions; argparse coloring is disabled so only the shared renderer emits ANSI. Mutations preview by default without interactive confirmation or `--yes`; raw exports/app previews remain undecorated. The private engine is built explicitly with `python3 -B tools/verify_anodize.py build`.
