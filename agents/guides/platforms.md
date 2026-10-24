# Platform Work Guide

Read this guide before adding platform detection, filesystem behavior, package-manager support, shell integration, environment paths, privilege handling, or a platform-specific module.

## Model

Platform is detected execution context. Catalog locations and resources define source ownership and target mappings; keep these separate from platform detection.

The platform identifiers are:

- `termux`
- `linux`
- `wsl`
- `windows`

Linux distribution and package manager are capabilities beneath the `linux` or `wsl` platform, not additional top-level platform identities unless a later decision changes the model.

## Adapter Boundary

Portable core code asks adapters for capabilities and operations. It does not scatter runtime checks throughout unrelated packages.

Adapters should own:

- Config, data, state, cache, home, and executable paths.
- OS and runtime detection evidence.
- File-link capabilities and primitives.
- Privilege availability and invocation policy.
- Shell discovery and initialization paths.
- Package-manager discovery and normalized package operations.
- Platform-specific path validation.

## Rules

- Capability evidence is preferable to platform-name assumptions.
- A detected capability must still be scoped to the tested filesystem and destination when relevant.
- Native Windows and WSL use separate state and must not be conflated because both can access Windows files.
- Do not translate paths or cross the Windows/WSL boundary without an explicit operation designed for it.
- Do not assume all Linux distributions have `apt`, `pacman`, `sudo`, systemd, or XDG variables set.
- Do not assume Termux behaves exactly like a conventional Linux distribution.
- Do not duplicate the resolver or transaction engine in Bash and PowerShell.

## Adding Support

For each new capability or platform:

1. Document detection inputs and false-positive risks.
2. Define the normalized adapter interface.
3. Implement a read-only capability report first.
4. Add isolated unit tests.
5. Add integration coverage in a disposable environment when possible.
6. Document limitations and untested behavior honestly in `docs/platforms.md`.
7. Update catalog and command examples only after the capability works.

Platform support is not complete merely because the CLI starts. Track links, copies, undo, checkout setup, shell integration and CI separately in the feature references.

## Catalog and Theme Adapters

The catalog's `--platform` is an observation override, not proof of native support.
Androidots catalogs apply only to Termux; missing/private submodules must remain
uninitialized. Theme wallpaper calls use explicit Android, Wayland or X11 adapters;
mock tests do not establish actual desktop or Android wallpaper rendering.

## Dual-shell maintenance

Every first-party change must cover Bash on Termux/Linux/WSL and native Windows PowerShell 5.1/7: routes, flags, aliases, contextual completion, exact data output, styled human output, progress and optional pickers. Keep native filesystem/app differences in adapters and reuse transactions. Read [native PowerShell](../../docs/powershell.md); update its capability limits and the [parity plan](../../plans/powershell-parity.md) when affected. Run focused isolated tests for both controller paths, require actual PowerShell engines in Windows CI, and report missing native/desktop evidence explicitly.
