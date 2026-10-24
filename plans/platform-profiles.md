# Platform profiles and consolidated shell startup

**Status: Implemented; native desktop acceptance pending.** Implements the approved platform-profile, environment,
startup bundle, bootstrap and Androidots/Windots absorption plan.

## Accepted contract

Universal root trees remain universal. Optional profile trees live under
`profiles/{termux,linux,wsl,windows}`, with distro overrides under `distros/ID`.
WSL inherits Linux and its distro layer. Distro directories are created only for
real overrides. Profile inspection is read-only; configuration replacements are
explicit catalog mappings. Environment overrides win over defaults; checkout
identity remains checkout-owned. Hooks are tracked without persisting secrets.
Bash/Zsh startup bundles are prepared by Python and loaded natively. Bare init
stays lightweight; full rc/bootstrap adds interactive configuration. Other native
shells retain the shared environment contract. Bootstrap fetches only a missing
checkout, with no packages, application installation or recursive submodules.

## Work and acceptance

- [x] Shared platform detection, profile resolution, catalog and command roots.
- [x] Environment registry, provenance, hook tracking and read-only diagnostics.
- [x] Consolidated Bash/Zsh sources and validated atomic startup bundles.
- [x] Bounded missing-checkout bootstrap and native shell adapters.
- [x] Archived snapshot imports with compatibility paths. Original resource IDs were retained initially; [platform identity cleanup](platform-file-identities.md) supersedes that choice.
- [x] Isolated regression tests, startup measurements, documentation synchronization.

Follow the [presentation gate](README.md#presentation-gate-for-every-plan).
Test 40/80/120-column views and exact scalar/JSON interfaces. Use owned fixtures
for environment, bootstrap, migration, rollback and interrupted operations.
Native Linux, WSL and Windows PowerShell 5.1/7 acceptance is pending until run
on those systems; Termux fixtures do not establish native desktop behavior.
Preserve all existing working-tree changes. Do not publish or activate themes,
install application links, commit or push as part of this source migration.


## Verification on Termux (2026-10-24)

Owned-fixture checks passed: 13 profile/bootstrap/bundle tests, 9 environment
reporting tests (including 40/80/120-column views and scalar/JSON boundaries),
24 Bash dispatcher tests, 6 user-local completion tests, and 13 native CLI
controller tests with one unavailable-engine skip. The 25 installation cases
passed across the initial run and focused fixture/source-layout corrections;
this includes WSL installation, connector handling and undo in portable fixtures.
Native Fish and Nushell environment/reload checks passed. No live private shell
configuration was sourced for verification.

The existing broader shell suites retain six assertions reproduced against the
pre-change source snapshot: two shell-init assertions and four shared-shell
assertions. Five Xonsh launch errors are caused by its unavailable interpreter.
They are not counted as successful acceptance. The broader tmux status suite
also hit a timing-sensitive two-client PREFIX indicator assertion; focused
helper-path checks passed (4 cases), alongside 7 Termux autostart, 6 location
completion and 3 weather-helper cases. Broad dispatcher ShellCheck did not
complete within its bounded run; focused new shell adapters passed ShellCheck.
Python/native syntax, command metadata and documentation-link checks are run
separately. Native PowerShell 5.1/7, Linux and WSL execution remain pending.

## Startup measurements

Five sequential samples with the same isolated public configuration and tool
availability produced these median milliseconds. They are Termux measurements,
not native desktop results or a universal speed claim.

| Fixture | Before | After |
| --- | ---: | ---: |
| Zsh public plugins | 2052.553 | 1729.289 |
| Bash native tools | 1894.365 | 1982.823 |
| Bash minimal tools | 24.435 | 63.368 |

The minimal path pays for environment application and cache metadata validation;
optional tools dominate the fuller fixtures. Keep this regression visible when
optimizing further. Traced Dots-owned source calls decreased from 31 to 13 for
Bash and 46 to 22 for Zsh (unique paths 26 to 12 and 38 to 21). Later native
adapter correctness changes do not establish new performance measurements.

## Migration recovery

Before gitlink conversion, verified history bundles, tracked-file snapshots,
original worktrees and the original submodule manifest were retained at:

`~/.local/state/dots/source-archives/20261024T202200Z`

`migration.json` records the source commits. Original worktree Git metadata now
points to the archived trees; Rainmeter retains its separate pinned history at
the new nested path. Root compatibility links preserve legacy lookup paths.
Only the two gitlink removals and relocated Rainmeter gitlink were staged as
part of conversion. Other source edits remain uncommitted. No application
installation, package operation, theme activation, commit or push occurred.
