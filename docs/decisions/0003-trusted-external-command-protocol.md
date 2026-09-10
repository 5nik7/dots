# 0003: Trusted External Command Protocol

Status: Accepted
Date: 2026-09-10

## Authorization and Scope

The owner approved decisions 1–4 of the bounded external-command proposal and explicitly authorized this development-only implementation. This settles the external protocol left open by [0002](0002-phase-1-go-adoption.md); it does not authorize installation, bootstrap, packages, managed mutations, releases or merging. The existing prototype and independent experiment remain unchanged. Only disposable fixtures implement external commands in this task. Native execution acceptance is tracked in [the Phase 2 plan](../../plans/phase-2-command-center.md).

## Roots, Identity and Limits

Only repeated prefix `--command-dir <absolute-path>` options select roots. No equals form, environment search variable, PATH search, current-directory default, DOTS fallback or executable-relative root is supported. Parse these options before the route only. A missing value or more than eight roots is usage error 2. Syntactically valid root values are not inspected until external resolution or discovery is needed: all existing built-ins and commands help resolve before root health checks.

Canonicalize roots with absolute clean paths and resolved root symlinks; require existing directories and reject repeated object identities with `os.SameFile`, not merely repeated strings. Root order determines diagnostics only. No definition may override another at the same route. Roots are explicit executable trust inputs; no ownership, ACL, signature or sandbox guarantee follows from selecting them. The development boundary assumes these files and their parent directories remain under trusted control.

Unix accepts ordinary absolute roots. Windows accepts local fixed-drive NTFS roots only, with case-sensitive directory mode disabled; reject UNC/device paths, alternate streams, drive-relative names and unsupported directory query results. Resolve root aliases before identity comparison. Windows filenames are ASCII case-insensitive for protocol names; metadata routes are always lowercase. Case-sensitive Windows directories are refused, so case variants cannot hold independent definitions. Unix filenames must use canonical lowercase spelling. Root aliases may resolve through links, but immediate command/sidecar entries must be plain regular files, never symlinks or Windows reparse points.

Limits: 8 roots; 8 route segments; 24 ASCII bytes per segment matching `[a-z][a-z0-9]*`; 65,536 bytes per metadata file; JSON nesting depth 16; 1,024 bytes per display string; 16 examples; at most 4,096 immediate directory entries per root and 1,024 distinct command definitions across discovery. Exceeding limits fails explicitly, never returns a truncated discovery result. More than eight consecutive route-like input tokens is usage error; use `--` to delimit long argument lists. The limit applies to matching, not to arbitrary extension argument sizes accepted by the OS.

## Protected Names and Routing

The exact protected first-token set is `help`, `doctor`, `commands`, `completion`, `version`, `status`, `spec`, `plan`, `apply`, `undo`, `history`, `backup`, `config`, `bootstrap`, `self`. These tokens and all descendants cannot be supplied by extensions. Existing built-ins have precedence even when roots are missing, malformed on disk, or contain collisions. Reserved but unimplemented requests remain unknown/usage error 2. Discovery validation reports all encountered protected definitions as conflicts. Reservation is not implementation.

For an unprotected request, grow candidates only across route-grammar tokens, stopping at the first flag, `--`, or non-route token, then probe from longest to shortest across every root at each depth. Each candidate checks exact metadata/native/recognized unsupported-launcher names without directory enumeration. Two definitions of the same route fail, regardless of platform availability or root order. An existing malformed, unavailable, unsupported, nonregular or inaccessible candidate blocks fallback to shorter routes. An executable without metadata is an invalid definition; metadata without the current native executable is explicitly unavailable. No cache, aliases, implicit interpreter, metadata handshake or recursive search exists.

## Metadata Schema 1

A sidecar `dots-files-list.json` describes route `["files", "list"]`. Required exact keys are `schema_version` (1), `route` (segment array), `summary`, `synopsis`, `examples` (1–16 display strings), `platforms` (nonempty unique IDs from termux/linux/windows/wsl), `hidden` (boolean), `outputs` (nonempty unique objects with `format` and `schema_version`: text/0 or json/positive integer), `mutation` (read-only), `aliases` (empty array), and `capabilities` (empty array). Null values, missing/unknown keys, duplicate keys at any depth, trailing JSON, invalid UTF-8 and control/format characters in display strings are rejected. Each display string is nonempty, at most 1,024 UTF-8 bytes, and single-line. The route must match the sidecar basename. No executable path, interpreter or shell-expression field is accepted.

The binary basename is derived from the route: `dots-files-list` on Unix or `dots-files-list.exe` on Windows. `.cmd`, `.bat`, `.ps1`, `.com` and `.sh` suffix launchers are unsupported; their presence without a native executable produces an unsupported-launcher result. A directory may contain both Unix and Windows native payloads for one sidecar. Declared read-only/output/platform properties are author assertions, not verified behavior or permission to bypass future transaction APIs.

## Execution, Arguments and Interruption

Unix executes the absolute extension path by replacing the dispatcher process. Require a regular file with execute bits; the OS handles native format and shebang semantics. Never retry through a shell, infer an interpreter, rewrite a Termux shebang or translate WSL paths. Native Windows launches only `.exe`, passing an argument vector through Go's CommandLineToArgvW-compatible quoting convention. Shell/custom command-line parsers are outside the protocol. WSL execution is refused pending native coverage; metadata can still describe it.

Preserve remaining argument values/order, environment, working directory and actual standard handles. No logging of arbitrary argument/environment values, no output interception, decoration or redaction, no shell expansion. Prefix dispatcher options are consumed; options after the route belong to the extension. `--` stops matching and is forwarded unchanged. A `-h` or `--help` anywhere before the first `--` requests core-rendered static help for the resolved route; no extension is run. Matching still uses the initial route-token prefix. After `--`, help tokens are literal extension arguments. Existing built-in argument contracts remain unchanged, except the newly documented commands/help surfaces and prefix option.

Core success is 0; internal/output/validation/collision/access/unavailable/unsupported/launch errors are 1; malformed dispatcher syntax and unknown routes are 2. Internal typed failure categories and fixed diagnostics distinguish these without echoing arguments. Once execution starts, propagate the child's ordinary native exit status. Unix replacement preserves the extension's PID, signal and terminal behavior. Windows inherits the same console, consumes the wrapper's own Ctrl+C/Ctrl+Break notifications while waiting, and does not duplicate console broadcasts. The child's exit code is preserved, including native status values. Tests must prove real console Ctrl+C and Ctrl+Break delivery and waiting, not just injected cancellation. No detached descendants, process-tree cleanup, forced parent-only termination, or console-close/logoff cleanup guarantee is made.

## Discovery and Help

`dots commands` lists built-in metadata and sorted visible external definitions; unavailable platform entries are marked. `dots commands --check` validates all definitions, including hidden entries, duplicates and protected routes, with no execution. `commands -h`/`--help` is built-in help and does not inspect roots. Ordinary global help stays built-in-only with a pointer to commands; external contextual help reads only the selected sidecar, shows availability, and never executes. Shared normalized metadata supports future projections; public discovery JSON, Markdown generation, recursive group help and completion remain deferred. No filesystem enumeration occurs on direct dispatch or contextual help.

## Security Boundary and Alternatives

Opened-handle metadata checks, regular-file checks, root identity and bounded parsing reject malformed inputs and accidental unsafe objects. They do not authenticate code, inspect interpreter dependencies, enforce the read-only declaration, or prevent an adversary concurrently replacing trusted files between validation and execution. There is no execute-by-handle identity guarantee or hostile-filesystem containment claim. Static help/discovery execute no extension at all. No automatic credential/elevation flow exists.

Implicit PATH/repository discovery would expand trust without selection. First-directory-wins would hide collisions. Runtime metadata handshakes could execute code during inspection. General Windows script/interpreter support would require a separate quoting and interpreter-trust decision. Those alternatives are deferred.

## Validation

Require native isolated Termux ARM64, Linux AMD64 and Windows AMD64 checks with Go 1.27.1 and standard-library dependencies. Preserve offline/telemetry isolation and independent experiment checks. Test routing, strict metadata, root/case identity, protected precedence, argument/stream/exit contracts, native console interruption, no-execution discovery/help and unchanged owned roots. Benchmark help/version, targeted external dispatch and enumerated discovery separately using the existing warm method; numeric limits remain advisory under decision 0002. Preserve raw samples, source/binary/logo identities and gaps outside Git. Implementation results belong in the plan and must not turn untested capabilities into support claims.
