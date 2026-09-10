# Dots Agent Guide

This file is the project-wide operating contract for agents and contributors working on `dots`. Keep it concise, authoritative, and current. Put task procedures in `agents/guides/`, architecture reference in `docs/`, and implementation plans in `plans/`.

## Mission

`dots` is a fast, safe, intuitive, modular, and extensible command center for managing dotfiles, scripts, shells, themes, packages, and environment setup across Termux, Linux, WSL, and native Windows.

The intended experience is one command family with discoverable routes such as `dots files`, backed by built-in commands and optional executables named `dots-*`. Managed source files remain in the repository and are linked by default. Copying is an explicit alternative. Existing machine state must be planned, backed up, recorded, and reversible.

## Current Phase

The project is in the design and incremental-migration phase.

- The existing `bin/dots` is a prototype, not the final command architecture.
- The existing dotfiles tree remains live and must not be reorganized wholesale without an approved migration plan.
- Commands and manifests described in `docs/` may be proposed rather than implemented. Never document a proposed command as currently usable.
- Termux is the first implementation target. Cross-platform boundaries must still be preserved from the first change.
- Go adoption and the bounded next core slice are accepted in [decision 0002](docs/decisions/0002-phase-1-go-adoption.md). The first permanent read-only core/registry slice is implemented; the development-only external protocol is accepted in [decision 0003](docs/decisions/0003-trusted-external-command-protocol.md) and implemented alongside it. Broader command-center features remain deferred. Untested platform and release capabilities stay deferred.

Track phase status in [`plans/roadmap.md`](plans/roadmap.md) and Termux scope in [`plans/termux-mvp.md`](plans/termux-mvp.md).

## Required Reading

Read the guide matching the work before changing files:

- [`agents/guides/worktrees.md`](agents/guides/worktrees.md) — one-worktree capacity, explicit enrollment, preview and authorized cleanup.
- [`agents/guides/commands.md`](agents/guides/commands.md) — dispatcher behavior, command naming, metadata, help, and completions.
- [`agents/guides/managed-files.md`](agents/guides/managed-files.md) — modules, manifests, link/copy behavior, adoption, planning, and rollback.
- [`agents/guides/bootstrap.md`](agents/guides/bootstrap.md) — remote installers, repository cloning, first-run setup, and private sources.
- [`agents/guides/platforms.md`](agents/guides/platforms.md) — Termux, Linux, WSL, and Windows-specific work.
- [`agents/guides/testing.md`](agents/guides/testing.md) — test isolation, safety tests, integration tests, and benchmarks.
- [`agents/guides/documentation.md`](agents/guides/documentation.md) — documentation ownership and synchronization requirements.

Reference documents:

- [`docs/principles.md`](docs/principles.md) — product and engineering priorities.
- [`docs/architecture.md`](docs/architecture.md) — component boundaries and execution flow.
- [`docs/commands.md`](docs/commands.md) — proposed CLI vocabulary and extension protocol.
- [`docs/specification.md`](docs/specification.md) — draft module/profile manifest model.
- [`docs/safety.md`](docs/safety.md) — mutation, backup, transaction, undo, and secrets rules.
- [`docs/platforms.md`](docs/platforms.md) — platform model, paths, capabilities, and support matrix.
- [`docs/testing.md`](docs/testing.md) — test strategy and performance verification.
- [`docs/current-repository.md`](docs/current-repository.md) — baseline inventory and migration constraints.

## Sources of Truth

Do not maintain competing exhaustive lists.

- Product priorities: `docs/principles.md`.
- Architecture and component ownership: `docs/architecture.md`.
- Command routes and semantics: eventually the command registry; until implemented, `docs/commands.md` is the design source.
- Manifest semantics and precedence: `docs/specification.md`.
- Destructive-operation rules: `docs/safety.md`.
- Platform support claims: `docs/platforms.md`.
- Active scope and sequencing: `plans/roadmap.md` and focused plans under `plans/`.
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

Go is the accepted core language under [decision 0002](docs/decisions/0002-phase-1-go-adoption.md), which owns the initial toolchain/development targets, performance policy, release-trust direction, and remaining gates. The permanent read-only core now lives beside the preserved independent experiment. The development external protocol now uses explicit roots, strict sidecars and native adapters. POSIX shell/PowerShell bootstrap and production installation remain unimplemented.

The core owns operations that require consistent safety or state:

- Platform and capability detection.
- Configuration and manifest loading.
- Profile resolution and collision detection.
- Current-state inspection and plan generation.
- Transactional apply, backup journals, history, and undo.
- Command discovery, validation, structured output, and completion data.

External `dots-*` commands may add cohesive features. They must not replace or circumvent the transaction engine for managed filesystem changes.

## Command Contract

Follow [decision 0003](docs/decisions/0003-trusted-external-command-protocol.md) for development extensions: no implicit roots, protected namespaces, mandatory static JSON, targeted direct lookup, native execution only, and no claim of sandboxing or protection from concurrent trusted-file replacement. Tests use disposable fixture commands only. Follow [decision 0004](docs/decisions/0004-versioned-command-discovery.md) for the versioned static command catalog; Zsh generation follows [decision 0005](docs/decisions/0005-static-zsh-completion.md).

- User-facing routes use spaces: `dots files list`.
- External command filenames use hyphens: `dots-files` or `dots-files-list`.
- Resolve the longest matching command prefix and forward remaining arguments unchanged.
- Use a fast direct-resolution path. Do not scan or parse every extension for an ordinary known route.
- Built-ins cannot be shadowed silently. Duplicate routes are validation failures.
- Help, completion, JSON discovery, and Markdown command reference must derive from the same metadata.
- Do not require `fzf`, `jq`, `sed`, `awk`, Git, or a package manager merely to start the CLI or display basic help.
- Keep stdout machine-consumable when a command promises structured output. Send diagnostics to stderr.

Do not add a new command or rename an existing route without updating `docs/commands.md`, completion behavior, command metadata tests, and user-facing documentation when applicable.

## Platform, Profile, and Host

Use these terms precisely:

- A **platform** is detected execution context, such as `termux`, `linux`, `wsl`, or `windows`.
- A **profile** is a selected collection of desired modules, such as `personal`, `minimal`, or `work`.
- A **host** is an optional device-specific layer.

Do not encode a platform as an ordinary profile internally, even if a temporary compatibility alias presents it that way to a user. Resolution order and collision behavior are defined in `docs/specification.md`.

## Safety Invariants

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
- Load only the selected profile and its dependency graph.
- Avoid content hashing when metadata or symlink identity is sufficient; hash when correctness requires it.
- Generate or cache shell initialization and completion data instead of invoking expensive resolution during every shell startup.
- Keep large optional assets and vendored dependencies out of the minimum bootstrap path.
- Any meaningful startup or planning regression requires an explanation and updated measurements.

## Cross-Platform Rules

- Do not assume `$HOME`, XDG directories, `sudo`, executable permission bits, GNU utilities, or POSIX symlink behavior in portable core code.
- Centralize path, privilege, link, shell, and package-manager differences in platform adapters.
- Treat native Windows and WSL as separate installations with separate state stores.
- Never silently translate a path between Windows and WSL or create a cross-filesystem link.
- Shell and PowerShell scripts are platform adapters or extensions, not duplicated implementations of the transaction engine.
- Optional dependencies must be capability-checked at the boundary that needs them.

## Repository and Migration Discipline

- Preserve unrelated existing files and user changes.
- Migrate incrementally by module, beginning with a deliberately small Termux slice.
- Do not initialize private or optional submodules merely to run general tests or documentation checks.
- Do not add generated caches, bytecode, build outputs, downloaded archives, or machine-local state to Git.
- Prefer dependency manifests or lazily fetched optional sources over vendoring large third-party trees.
- Do not rewrite repository history, remove existing submodules, or move large directory trees without explicit approval and a recovery plan.

## Development Worktree Lifecycle

Keep at most one active development worktree alongside the original checkout. Inspect existing worktrees before creating another. Follow [the worktree guide](agents/guides/worktrees.md): explicitly enroll workflow-managed worktrees; automatically remove eligible merged ones during authorized maintenance/implementation, after a verified merge or at the next eligible task boundary. Do not repeatedly request owner approval for already authorized eligible cleanup. Read-only planning reports candidates without removal or fetch. Preserve original/current-session/helper worktrees, all branch/recovery refs, review evidence and uncertain/local work. No name-pattern authorization, force removal, backup archives, hooks or scheduled cleanup.

An older original checkout does not automatically load policy committed elsewhere. Future sessions must explicitly read current instructions from the reviewed fetched revision as described in the guide; preserve the original HEAD, index and unrelated edits.

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
- Manifest field, precedence, variable, or collision behavior changed: update `docs/specification.md`.
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
