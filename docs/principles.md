# Project Principles

**Status: Working baseline**

These principles guide design decisions for `dots`. Their order matters when goals conflict.

## 1. Protect Existing State

The primary failure to avoid is losing or silently replacing a user's existing configuration.

- Inspect and classify a destination before changing it.
- Preflight the complete operation set before the first mutation.
- Back up replaced state in a durable transaction.
- Make recovery possible after failure or interruption.
- Refuse ambiguous ownership and path escapes.

Convenience does not justify an untracked overwrite.

## 2. Keep the Common Path Fast

`dots` should feel like a native utility, including on Termux and during shell startup.

- Direct command dispatch must not depend on repository size.
- Basic help and version output must not invoke Git, a package manager, or the profile resolver.
- Load only the selected profile and dependency graph.
- Avoid mandatory subprocesses for work the core can perform directly.
- Generate or cache shell initialization and completion data when dynamic execution would affect startup.
- Keep optional assets and third-party payloads outside the minimum bootstrap path.

Performance claims require repeatable measurements rather than impressions.

## 3. Plan Before Apply

The desired specification, current machine state, and proposed changes are distinct things:

```text
desired specification + observed state = plan
plan + explicit approval = transaction
transaction journal = history and undo
```

Every mutating feature should expose its intended effects before performing them. `--dry-run` must not be a collection of branches that merely skip some writes; it must use the same planning representation that apply consumes.

## 4. Prefer Predictability Over Magic

Defaults should reduce repetition without obscuring ownership or precedence.

- Conventions may infer ordinary home-relative destinations.
- Exceptional destinations and overrides must be explicit.
- Conflicting modules fail unless a replacement relationship is declared.
- Link failure does not silently become a copy.
- Platform detection reports its evidence and can be overridden for testing.

A user should be able to explain why a file is managed and which layer selected it.

## 5. Separate Portable Policy from Platform Mechanics

The core defines desired state, planning, transactions, and normalized operations. Platform adapters implement paths, link capabilities, package managers, privilege behavior, and shell locations.

Native Windows and WSL are separate execution environments. Termux is Android-hosted and must not inherit conventional Linux assumptions accidentally.

## 6. Make the Minimum Installation Self-Contained

The core experience must not require optional interactive tools, a specific shell, all submodules, or access to private repositories.

- `fzf` may enhance selection but cannot be necessary for non-interactive operation.
- Private sources are synchronized after public bootstrap and authentication checks.
- Large fonts, wallpapers, and third-party bundles are optional modules or sources.
- Structured output must remain usable without color or a terminal.

## 7. Extend at Clear Boundaries

The Omarchy-inspired `dots-*` protocol makes new commands discoverable without expanding one dispatcher indefinitely. Extensions still operate within a defined trust and safety model.

- Core state mutations go through the transaction engine.
- Built-in routes cannot be shadowed silently.
- Duplicate routes are validation errors.
- Metadata drives discovery, help, completions, and generated reference.
- Platform-specific behavior belongs in an adapter or explicitly platform-scoped extension.

## 8. Be Reproducible Without Pretending Every Operation Is Reversible

The resolved specification should identify selected modules, sources, platform, profile, host, CLI version, schema version, and repository revision.

Filesystem changes can generally be backed up and undone. Package-manager upgrades, arbitrary hooks, and external services may not be fully reversible. Plans and journals must state that distinction instead of implying transactional guarantees that do not exist.

## 9. Make State Observable

Users and automation should be able to inspect:

- The selected platform, profile, and host.
- The fully resolved desired specification.
- Current drift and broken links.
- The next operation plan.
- Prior transactions and backups.
- Why an item is selected, skipped, blocked, or in conflict.

Human output can be concise; structured output must be stable and complete enough for tooling.

## 10. Treat Documentation and Tests as Part of the Interface

Behavior, help, examples, completions, schemas, tests, and plans must not evolve independently.

- Each concept has one named source of truth.
- Proposed behavior is labeled honestly.
- Command metadata is generated into secondary references once generation exists.
- Safety invariants receive failure-path tests.
- Material architectural decisions are recorded under `docs/decisions/`.

## Non-Goals for the Initial MVP

The first Termux milestone does not need to:

- Replace every current script or configuration.
- Support every Linux distribution or Windows package manager.
- Manage arbitrary system configuration outside user-owned paths.
- Automatically synchronize secrets.
- Roll back operating-system upgrades.
- Provide a full-screen TUI.
- Implement templates, remote sources, and hooks before safe file planning and transactions work.

Keeping these out of the first milestone protects the foundations that later features depend on.

