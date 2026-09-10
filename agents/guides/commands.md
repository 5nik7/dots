# Command Work Guide

Read this guide before adding or changing the `dots` dispatcher, a built-in route, an external `dots-*` command, command metadata, help, completion, or structured discovery output.

## Design Goal

The command family should retain the useful properties of Omarchy's dispatcher while remaining portable to Termux, Linux, WSL, and native Windows:

- A direct executable such as `dots-themes` is available as `dots themes`.
- A deeper executable such as `dots-themes-apply` is available as `dots themes apply`.
- The longest matching prefix wins and unused arguments are forwarded unchanged.
- Known direct routes avoid a full command-registry scan.
- Help, completions, validation, JSON output, and generated Markdown share one metadata source.

The external-command protocol is an extension mechanism. Safety-critical operations remain owned by the core even if their user-facing routes look identical to extension routes.

## Before Editing

1. Read `docs/commands.md` and `docs/architecture.md`.
2. Determine whether the route is built in, official external, or user external.
3. Search existing routes, aliases, and proposed commands for collisions.
4. Decide whether the change affects the stable interface, structured output, or completion data.
5. Update or create a focused plan if dispatcher semantics or command metadata are changing.

## Naming

- The main command is `dots`.
- External command basenames start with `dots-`.
- Filename hyphens map to route spaces; schema 1 sidecars must match the basename exactly.
- Use plural nouns for browsable collections when that is the established group: `files`, `links`, `scripts`, `shells`, `themes`, `packages`, `profiles`, `commands`, and `sources`.
- Use verbs for lifecycle actions: `plan`, `apply`, `undo`, and `bootstrap`.
- Avoid synonyms and aliases for new commands. Add an alias only to preserve an established name.
- Keep `self update`, `repo pull`, `packages install`, and `apply` distinct; do not create one ambiguous command that performs all of them.

## Resolution

Given `dots themes apply tokyonight`, resolution should try candidates from longest to shortest:

1. `dots-themes-apply-tokyonight`
2. `dots-themes-apply`
3. `dots-themes`

If `dots-themes-apply` exists, execute it with `tokyonight` as the remaining argument.

Resolution requirements:

- Built-in routes have explicit precedence and cannot be shadowed silently.
- Development roots are explicitly repeated prefix `--command-dir` options only; duplicates fail instead of selecting a winner.
- Duplicate canonical routes are errors surfaced by command validation.
- Platform-incompatible commands may be discoverable as unavailable, but must not fail with a misleading "unknown command" result.
- Native Windows accepts `.exe` only, with the argument convention and NTFS root restrictions in decision 0003. Do not infer an interpreter or Unix permission semantics.

## Metadata

The mandatory JSON sidecar is accepted in [decision 0003](../../docs/decisions/0003-trusted-external-command-protocol.md). Read it before changing roots, routes, metadata, discovery/help or execution. Its exact keys, limits, reservations and failure categories are normative. Richer future metadata must preserve:

- Canonical route.
- Short summary.
- Argument synopsis.
- Examples.
- Hidden/internal status.
- Supported platforms or capability requirements.
- Aliases retained for compatibility.
- Structured-output support.
- Mutation classification, when useful for help and policy checks.

Do not add comment-header parsing or runtime metadata handshakes. Static help/discovery must not execute extensions; completion and structured discovery remain deferred.

## Output

- Human help belongs on stdout for successful help requests.
- Usage errors and diagnostics belong on stderr.
- Structured output must be valid even when color is enabled globally; never mix decoration into JSON.
- Respect `NO_COLOR` and non-interactive output once color support exists.
- Use stable field names and version structured records if they become externally consumable.
- Avoid forcing a pager or interactive selector when stdout is not a terminal.

## Performance

- The common direct-dispatch path must not parse every command file.
- Do not invoke Git merely to locate the installed executable or dispatch a route.
- No persistent cache in this slice. Targeted direct probes and enumeration must remain separate.
- Completion should consume generated or cached metadata rather than repeatedly resolving the complete machine specification.
- Add or update dispatcher benchmarks whenever route lookup changes materially.

## Required Updates

A command change normally requires all of the following:

- Command implementation or registry entry.
- Command metadata.
- Route and collision tests.
- Argument and error-path tests.
- Completion data or generation tests.
- `docs/commands.md`.
- README examples if the command is user-facing and implemented.
- Relevant focused plan status.

Before finishing, verify that proposed commands are not presented as implemented and that generated documentation, once introduced, is regenerated rather than edited by hand.

