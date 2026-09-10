# Platform Work Guide

Read this guide before adding platform detection, filesystem behavior, package-manager support, shell integration, environment paths, privilege handling, or a platform-specific module.

## Model

Platform is detected execution context. Profile is selected intent. Host is optional device-specific configuration. Do not blur these layers to avoid a short-term shortcut.

The initial platform identifiers are proposed as:

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
7. Update profile/module examples only after the capability works.

Platform support is not complete merely because the CLI starts. Track planning, links, copies, undo, packages, bootstrap, shell integration, and CI separately in the support matrix.


## Development External Adapters

Follow [decision 0003](../../docs/decisions/0003-trusted-external-command-protocol.md): Unix direct exec with execute bits; native Windows `.exe` only, local fixed-drive NTFS, case-sensitive roots refused, and same-console waiting. No PATH/suffix/interpreter inference or WSL path translation. Test Windows quoting and real Ctrl+C/Ctrl+Break natively; preserve explicit deferred known-folder, ACL, WSL and filesystem coverage.
