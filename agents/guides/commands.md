# Command Work Guide

Read this guide before adding or changing the `dots` dispatcher, a built-in route, an external `dots-*` command, command metadata, help, completion, or structured discovery output.

## Live Bash Framework

The live `bin/dots` follows [decision 0006](../../docs/decisions/0006-bash-command-framework.md) and the [Bash command contract](../../docs/commands.md#implemented-bash-command-framework). Its executable-relative libraries are independent of user startup. Default repository/local roots, executable symlinks, optional `# dots:` headers, and on-demand three-shell completion define the live extension contract. Preserve byte-for-byte argument/stream forwarding and keep catalog parsing off direct dispatch. Update the shared built-in metadata and shell adapters together when changing their interfaces.

Run `python3 -B tools/test_bash_dots.py`, shell syntax checks and ShellCheck for Bash changes; use `python3 -B tools/bench_bash_dots.py` for measured lookup changes. Shell-completion work also requires the existing Zsh/FZF-tab acceptance. See the testing guide.

## Design Goal

The command family should retain the useful properties of Omarchy's dispatcher while remaining portable to Termux, Linux, WSL, and native Windows:

- A direct executable such as `dots-example` is available as `dots example`.
- A deeper executable such as `dots-example-apply` is available as `dots example apply`.
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
6. Assess menu suitability for every new or changed command. Record add/update/no-menu and its reason in the focused plan or change notes; check existing family entries and use the menu-authoring skill when appropriate.

## Naming

- The main command is `dots`.
- External command basenames start with `dots-`.
- Filename hyphens map to route spaces; optional static comment headers provide help and completion metadata.
- Use plural nouns for browsable collections when that is the established group: `files`, `themes` and `commands`.
- Follow existing action names within each family, such as `install`, `uninstall`, `add` and `undo`.
- Avoid synonyms and aliases for new commands. Add an alias only to preserve an established name.
- Keep checkout updates, Git synchronization and configuration installation explicit and independently reviewable.

## Output

- Human help belongs on stdout for successful help requests.
- Usage errors and diagnostics belong on stderr.
- Structured output must be valid even when color is enabled globally; never mix decoration into JSON.
- Follow the [presentation contract](../../docs/presentation.md) for every new or changed first-party human view, including help, empty results and diagnostics. Reuse the shared renderer or verify equivalent behavior.
- Use the implemented color/icon controls and their documented `NO_COLOR`, terminal and forced-output precedence. Preserve readable plain layouts and all script-facing data formats.
- Prefer optional Gum for suitable interactive flows under the [Gum convention](../../docs/presentation.md#optional-gum-interactions). Reuse the lazy interaction adapter; keep tool probes out of help, completion and ordinary dispatch. Test missing tools, fallbacks, cancellation and noninteractive behavior.
- Include the presentation acceptance gate in the focused plan and review representative output alongside related commands.
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

Theme metadata providers and command behavior follow [Shared themes](../../docs/themes.md).
They read palette data without extension execution; test with `python3 -B tools/test_themes.py`.

The implemented singular `theme` routes and `files` routes are documented in
[themes](../../docs/themes.md) and [files](../../docs/files.md). Flat theme/resource
completion uses core-owned readers (`theme-id`, `file-resource`, `file-repository`),
never extension callbacks. Keep static headers, contextual help and completion
cases synchronized. Theme selection retains full-ID routes under `dots theme`; the shared handler also owns generated family/flavor palette commands. Keep the single parser, data-only help/completion and standalone `theme` forwarding equivalent. Collection routes now live under `dots themes`, with singular compatibility routes. Keep one palette parser; follow decision 0013.

The [Git family](../../docs/git.md) uses static Bash headers and a dots-owned backend; it never requires the standalone git-it executable. Run `python3 -B tools/test_git_operations.py` for changes, including literal paths and recursive safety. Keep raw JSON separate from compact human views. File mutations use the shared engine described in the managed-files guide.

## Dual-shell maintenance

Every first-party change must cover Bash on Termux/Linux/WSL and native Windows PowerShell 5.1/7: routes, flags, aliases, contextual completion, exact data output, styled human output, progress and optional pickers. Keep native filesystem/app differences in adapters and reuse transactions. Read [native PowerShell](../../docs/powershell.md); update its capability limits and the [parity plan](../../plans/powershell-parity.md) when affected. Run focused isolated tests for both controller paths, require actual PowerShell engines in Windows CI, and report missing native/desktop evidence explicitly.
