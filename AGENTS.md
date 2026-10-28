# Dots Agent Guide

This file is the project-wide operating contract for agents and contributors working on `dots`. Keep it concise, authoritative, and current. Put task procedures in `agents/guides/`, architecture reference in `docs/`, and implementation plans in `plans/`.

## Mission

`dots` is a fast, safe, intuitive, modular, and extensible command center for managing dotfiles, scripts, shells, themes and environment setup across Termux, Linux, WSL, and native Windows.

The intended experience is one command family with discoverable routes such as `dots files`, backed by built-in commands and optional executables named `dots-*`. Managed source files remain in the repository and are linked by default. Copying is an explicit alternative. Existing machine state must be planned, backed up, recorded, and reversible.

## Current Focus

Maintain the existing dotfiles, scripts, configurations and command framework. The live entry points are `bin/dots` (Bash) and `bin/dots.ps1` (native PowerShell), backed by shared Python controllers. The independent Anodize engine provides palette authoring.

- `dots files` provides catalog inspection and journaled adoption, linking, removal, checkout installation/uninstallation and recovery. See [checkout installation](docs/installation.md).
- `dots git` provides recursive status/publish/sync under [decision 0010](docs/decisions/0010-git-and-managed-file-operations.md).
- Themes use bounded publication and fixed app connectors under [decision 0008](docs/decisions/0008-config-catalog-and-theme-apps.md).
- Platform resources live under `profiles/{termux,linux,wsl,windows}`; Androidots/Windots IDs and root compatibility paths remain during migration. See [profiles](docs/profiles.md).
- `config/` is canonical; retain temporary `configs -> config` aliases until a separately reviewed cleanup.
- Termux is the primary local development target. Preserve native Linux, WSL and Windows boundaries and distinguish local fixtures from native evidence.

Focused work and acceptance criteria are indexed in [plans](plans/README.md). Never present a proposed feature as currently usable.

## Required Reading

Read the guide matching the work before changing files:

- [`agents/guides/worktrees.md`](agents/guides/worktrees.md) — default checkout workflow and optional worktree creation, enrollment, preview, and cleanup.
- [`agents/guides/commands.md`](agents/guides/commands.md) — dispatcher behavior, command naming, metadata, help, and completions.
- [`agents/guides/managed-files.md`](agents/guides/managed-files.md) — catalogs, link/copy behavior, adoption, planning, and rollback.
- [`agents/guides/bootstrap.md`](agents/guides/bootstrap.md) — checkout-local setup, prerequisites, source selection and recovery.
- [`agents/guides/platforms.md`](agents/guides/platforms.md) — Termux, Linux, WSL, and Windows-specific work.
- [`agents/guides/testing.md`](agents/guides/testing.md) — test isolation, safety tests, integration tests, and benchmarks.
- [`agents/guides/documentation.md`](agents/guides/documentation.md) — documentation ownership and synchronization requirements.
- [`agents/guides/codex-notifications.md`](agents/guides/codex-notifications.md) — Codex attention preferences, observational hooks, tmux acknowledgement and Termux alerts.

Reference documents:

- [`docs/principles.md`](docs/principles.md) — product and engineering priorities.
- [`docs/architecture.md`](docs/architecture.md) — component boundaries and execution flow.
- [`docs/commands.md`](docs/commands.md) — implemented CLI vocabulary and extension protocol.
- [`docs/specification.md`](docs/specification.md) — implemented theme, catalog and installation data contracts.
- [`docs/safety.md`](docs/safety.md) — mutation, backup, transaction, undo, and secrets rules.
- [`docs/platforms.md`](docs/platforms.md) — platform model, paths, capabilities and acceptance limits.
- [`docs/testing.md`](docs/testing.md) — test strategy and performance verification.

## Sources of Truth

Do not maintain competing exhaustive lists.

- Product priorities: `docs/principles.md`.
- Architecture and component ownership: `docs/architecture.md`.
- Command routes and semantics: static command metadata and `docs/commands.md`.
- Human output style and acceptance: `docs/presentation.md`.
- Data schemas and precedence: `docs/specification.md`.
- Destructive-operation rules: `docs/safety.md`.
- Platform support claims: `docs/platforms.md`.
- Active scope and sequencing: focused plans indexed in `plans/README.md`.
- End-user capabilities that actually exist: `README.md`.

When documents disagree, follow the latest explicit user direction, then this file, then the specialized guide, then the reference docs. Resolve the disagreement in the same change instead of choosing silently.

## Core Principles

Apply these in priority order when tradeoffs conflict:

1. Protect existing user data and preserve a reliable path back.
2. Keep common commands and shell startup fast.
3. Make the plan visible before changing the machine.
4. Prefer simple, predictable behavior over hidden magic.
5. Keep platform-specific behavior behind explicit adapters.
6. Keep the core useful without optional interactive tools or private repositories.
7. Make extensions easy without allowing them to bypass core safety rules silently.
8. Keep documentation and tests synchronized with behavior.

See `docs/principles.md` for the consequences of each principle.

## Working Architecture

Shell entry points own native invocation and initialization. Shared Python controllers under `lib/dots/` own file catalogs, configuration, Git operations, themes and checkout setup. `lib/dots/files/transactions.py` owns managed file preflight, journals, backups, rollback and recovery; platform adapters own filesystem primitives. The independent `plugins/anodize/engine/` Go module owns palette extraction and color transformations.

External `dots-*` commands may add cohesive features. They must not circumvent the transaction engine for managed filesystem changes. See [architecture](docs/architecture.md) for component ownership.

## Command Contract

For the live Bash executable, follow [decision 0006](docs/decisions/0006-bash-command-framework.md): repository/local roots plus explicit extras, executable symlinks, optional static comment headers, shared presentation helpers, and on-demand Bash/Zsh/Fish completion. No catalog scans during shell startup or ordinary direct dispatch; no extension execution for help or completion.

- User-facing routes use spaces: `dots files list`.
- External command filenames use hyphens: `dots-files` or `dots-files-list`.
- Resolve the longest matching command prefix and forward remaining arguments unchanged.
- Use a fast direct-resolution path. Do not scan or parse every extension for an ordinary known route.
- Built-ins cannot be shadowed silently. Duplicate routes are validation failures.
- Help, completion, JSON discovery, and Markdown command reference must derive from the same metadata.
- Do not require `gum`, `fzf`, `jq`, `sed`, `awk`, Git, or a package manager merely to start the CLI or display basic help.
- Keep stdout machine-consumable when a command promises structured output. Send diagnostics to stderr.
- Every new or changed first-party human view must follow [the presentation contract](docs/presentation.md): cohesive layouts and wording, shared semantic colors, readable plain fallbacks, and preserved data interfaces. Apply its acceptance gate in every focused plan.
- Prefer optional Gum for suitable new or changed interactive workflows, following [the presentation contract](docs/presentation.md#optional-gum-interactions). Use shared adapters, capability checks and useful fallbacks; preserve scripts, cancellation and explicit approval semantics.

Do not add a new command or rename an existing route without updating `docs/commands.md`, completion behavior, command metadata tests, and user-facing documentation when applicable.

For every new or changed command, record whether a Dots menu should be added, updated or left unchanged, with a reason. Follow command maintenance and menu authoring; this is a development review, not runtime discovery or automatic approval of menu actions.

## Platform Boundaries

A platform is the execution context: `termux`, `linux`, `wsl` or `windows`. Keep native Windows and WSL destinations and state separate. Catalog locations identify source repositories and explicitly mapped resources; their implemented schemas are defined in [data contracts](docs/specification.md).

## Safety Invariants

The transaction requirements below govern managed installation, replacement, backup, and undo operations. Ordinary edits to repository source files, including live dotfiles, use ordinary repository editing safeguards; preserve unrelated work and use Git history for committed source recovery.

- Read-only inspection and planning must not mutate the target machine, repository, package database, or state store.
- Every managed filesystem mutation must belong to a transaction with a durable journal.
- Existing targets are never overwritten or deleted without classification and an applicable backup or explicit refusal policy.
- Apply must preflight the complete operation set before the first mutation.
- A failed apply must roll back completed reversible operations in reverse order.
- Undo must detect post-apply drift and refuse destructive restoration unless explicitly forced.
- Link-to-copy fallback must never be silent.
- Package removal is never an automatic consequence of filesystem rollback.
- Bootstrap must not recursively initialize all submodules or request private credentials by default.
- Secrets must not appear in plans, logs, diagnostics, diffs, or structured output unless a dedicated explicit reveal operation is designed and approved.
- Tests must never target the developer's real home, config, state, cache, registry, or package manager.

Read `docs/safety.md` before changing any mutating path.

## Performance Rules

- Measure before adding caches or complexity, and retain benchmark baselines once established.
- Keep dispatch independent of repository size for direct routes.
- Load only the selected route’s inputs.
- Avoid content hashing when metadata or symlink identity is sufficient; hash when correctness requires it.
- Generate or cache shell initialization and completion data instead of invoking expensive resolution during every shell startup.
- Keep large optional assets and vendored dependencies out of the minimum bootstrap path.
- Any meaningful startup or planning regression requires an explanation and updated measurements.

## Cross-Platform Rules

- Maintain every first-party route, option, alias, completion, preview, verbose event and data contract for Bash (Termux, native Linux, WSL) and native Windows PowerShell 5.1/7 in the same change. Use shared Python controllers and explicit platform adapters; no Bash dependency on native Windows. Record an explicit platform exception where an operation has no native equivalent.
- Every focused plan must include both shell surfaces, Windows app destinations, isolated tests and actual native evidence or a named pending acceptance check. Follow [native PowerShell](docs/powershell.md) and the [parity plan](plans/powershell-parity.md). Future work must not silently extend only one shell.

- Do not assume `$HOME`, XDG directories, `sudo`, executable permission bits, GNU utilities, or POSIX symlink behavior in portable core code.
- Centralize path, privilege, link, shell, and package-manager differences in platform adapters.
- Treat native Windows and WSL as separate installations with separate state stores.
- Never silently translate a path between Windows and WSL or create a cross-filesystem link.
- Shell and PowerShell scripts are platform adapters or extensions, not duplicated implementations of the transaction engine.
- Optional dependencies must be capability-checked at the boundary that needs them.

## Repository and Migration Discipline

- Any repository file may be edited when relevant to the requested task, including `bin/dots`, live configurations, scripts, documentation and Anodize sources. File restrictions in earlier implementation slices are historical task boundaries, not a permanent allowlist.
- Preserve unrelated existing files and user changes; inspect Git status before editing.
- For task-relevant submodule edits, follow the submodule's local instructions and separate Git history. Editing permission does not authorize unrelated submodule initialization, updates, commits, or pushes.
- Keep configuration migrations bounded and reversible.
- Do not initialize private or optional submodules merely to run general tests or documentation checks.
- Do not add generated caches, bytecode, build outputs, downloaded archives, or machine-local state to Git.
- Prefer dependency manifests or lazily fetched optional sources over vendoring large third-party trees.
- Do not rewrite repository history, remove existing submodules, or move large directory trees without explicit approval and a recovery plan.

## Development Worktree Lifecycle

Work directly in the existing checkout on `main` by default. A separate branch or worktree is optional when the task calls for it; ordinary maintenance requires no worktree creation, enrollment, remote-policy fetch, or cleanup. Read the instructions in the current checkout.

When deliberately using or maintaining linked worktrees, follow [the worktree guide](agents/guides/worktrees.md), including its one-additional-worktree capacity and guarded cleanup. Preserve unrelated work, branch/recovery refs, and review evidence.

Git history provides recovery for committed repository edits. Preserve uncommitted and untracked work separately; reverting a commit does not recover those changes or undo external machine effects. Do not commit, push, reset, or revert without task authorization.

## Change Workflow

For non-trivial work:

1. Read this file and the relevant task guide.
2. Inspect the current implementation, tests, plans, and Git state.
3. Identify whether the work changes a proposed design or implemented behavior.
4. Write or update the focused plan when scope spans multiple components or contains migration risk.
5. Implement the smallest coherent change.
6. Run focused tests, then the broader safe suite when available.
7. Update every affected source-of-truth document in the same change.
8. Report behavior, verification, remaining risk, and any deferred documentation explicitly.

Do not mix opportunistic cleanup with a behavioral change unless the cleanup is required for that change.

## Documentation Contract

A behavior change without matching documentation is incomplete.

- Architecture or directory ownership changed: update `docs/architecture.md`.
- Product priority or invariant changed: update `docs/principles.md` and record the decision.
- Command, flag, output, or metadata changed: update `docs/commands.md` and applicable user docs.
- Data schema, precedence, variable, or collision behavior changed: update `docs/specification.md`.
- Mutation, backup, rollback, force, package, or secret behavior changed: update `docs/safety.md`.
- Platform detection, paths, link strategies, or support changed: update `docs/platforms.md`.
- Test entry points or guarantees changed: update `docs/testing.md` and the relevant agent guide.
- Milestone or scope changed: update the applicable file under `plans/`.
- User-visible implemented behavior changed: update `README.md`.

Proposed behavior must be labeled **Proposed** or **Draft**. Implemented behavior must be labeled accurately. Remove stale labels as part of implementation.

## Testing and Verification

- Use temporary, test-owned home/config/state/cache/repository roots.
- Test paths containing spaces, Unicode, leading dashes, broken links, and missing parents.
- Test interrupted apply and reverse-order rollback.
- Test idempotence: a second apply of an unchanged spec produces no mutations.
- Test route collisions and longest-prefix dispatch.
- Test structured output as an API, not incidental text.
- Run `git diff --check` and verify relative Markdown links for documentation changes.

Until formal runners exist, never invent commands in documentation. Record intended runners as proposed in `docs/testing.md`.

## Git

- Before pushing, verify the remote push destination and intended branch ref. Use an explicit branch refspec such as `HEAD:refs/heads/<branch>`; do not rely on upstream or default push routing. Direct updates to `main` require explicit task authorization.
- Keep commits atomic and limited to one coherent purpose.
- Use succinct commit messages that describe the change.
- Do not discard, reset, or overwrite unrelated working-tree changes.
- Do not commit secrets, machine state, generated backups, or credentials.

## Definition of Done

A change is done only when:

- The implementation matches the documented design or the design was updated deliberately.
- Existing user data remains protected by the applicable safety rules.
- Focused tests pass in isolated paths.
- Cross-platform effects were considered and documented.
- Performance-sensitive paths were measured when affected.
- Help, metadata, completions, examples, README, reference docs, and plans are synchronized where applicable.

Repository-local workflow skills are indexed in [.codex/README.md](.codex/README.md);
they supplement this contract and the task guides.

Wiki documentation is generated from canonical Dots sources. For behavior/documentation changes, update source docs, then rebuild and check the wiki when its checkout is available; otherwise run source-only validation and report synchronization pending. Use the `dots-documentation-maintenance` and `dots-wiki-maintenance` skills and follow [the wiki guide](agents/guides/wiki.md). Documentation work does not authorize commits or pushes.
