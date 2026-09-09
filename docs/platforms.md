# Platform Model

**Status: Proposed; no future platform support is yet claimed as implemented**

`dots` targets Termux, conventional Linux, WSL, and native Windows. Platform support is capability-based and tracked by subsystem rather than treated as a single yes/no label.

## Terminology

- Platform identifies the execution environment.
- Distribution identifies a Linux-family package and system environment where relevant.
- Architecture identifies the release artifact and binary behavior.
- Capability describes what can actually be done at a particular destination.
- Profile selects desired modules independently of platform.

## Initial Platform IDs

| ID | Meaning | First priority |
| --- | --- | --- |
| `termux` | Termux userland hosted on Android | Primary MVP |
| `linux` | Conventional native Linux userland | After Termux foundation |
| `wsl` | Linux distribution running under Windows Subsystem for Linux | After Linux |
| `windows` | Native Windows process and filesystem APIs | After WSL |

## Detection Evidence

Detection should collect evidence rather than use one fragile variable.

### Termux

Potential evidence includes Termux-specific environment variables, prefix layout, Android runtime/kernel information, and Termux filesystem locations. The final detector must be tested in a real supported Termux installation and must not classify an arbitrary Android shell as Termux without required capabilities.

### WSL

Potential evidence includes WSL-specific environment variables and kernel/runtime markers. WSL detection occurs before generic Linux classification.

### Linux

Use operating-system runtime evidence, then read `/etc/os-release` or its documented fallback for distribution details when available. Do not treat distribution name as package-manager proof.

### Windows

Native runtime identity is authoritative. PowerShell availability, Developer Mode, elevation, package managers, and link types are separate capabilities.

All detection can be overridden explicitly for fixtures and advanced testing, but the override must appear in diagnostics and plans.

## Standard Paths

| Purpose | Termux/Linux/WSL | Native Windows |
| --- | --- | --- |
| Home | Adapter-resolved user home | Known user profile folder |
| Repository default | `~/dots` initially | `%USERPROFILE%\dots` initially |
| Config | `$XDG_CONFIG_HOME/dots` or `~/.config/dots` | `%APPDATA%\dots` |
| Data | `$XDG_DATA_HOME/dots` or `~/.local/share/dots` | `%LOCALAPPDATA%\dots\data` |
| State | `$XDG_STATE_HOME/dots` or `~/.local/state/dots` | `%LOCALAPPDATA%\dots\state` |
| Cache | `$XDG_CACHE_HOME/dots` or `~/.cache/dots` | `%LOCALAPPDATA%\dots\cache` |
| User executable | Adapter-selected path on `PATH` | User-owned application/bin path on `PATH` |

The repository path is configurable. Runtime state must not depend on the repository remaining at its default path.

## Filesystem Capabilities

Capability checks may depend on destination filesystem and volume.

| Capability | Termux | Linux | WSL filesystem | Native Windows |
| --- | --- | --- | --- | --- |
| File symbolic link | Validate in spike | Expected, verify errors | Expected inside distribution | Capability-test permissions/policy |
| Directory symbolic link | Validate in spike | Expected, verify errors | Expected inside distribution | Capability-test permissions/policy |
| Hardlink | Later capability | Same-filesystem only | Same-filesystem only | Same-volume file only |
| Junction | Not applicable | Not applicable | Not Linux-native | Directory option |
| Cross Windows/WSL link | Block by default | Not applicable | Block by default | Block by default |

The planner reports the requested strategy and effective capability. It never silently copies because a link failed.

## Package Adapters

Initial candidates, subject to capability detection:

| Platform | Candidate managers |
| --- | --- |
| Termux | `pkg`, Termux `apt`, optional Termux `pacman` environments |
| Linux | `apt`, `pacman`, and later explicitly supported managers |
| WSL | Manager provided by the selected Linux distribution |
| Windows | `winget`, with Scoop or Chocolatey considered later if deliberately supported |

Manager discovery is not permission to install. Package operations remain explicit planned stages.

## Privilege

- Termux does not use `sudo` for its ordinary userland package and configuration paths.
- Linux and WSL may or may not provide `sudo`; query the required operation and available mechanism.
- Native Windows elevation is distinct from Developer Mode and link capability.
- User-owned dotfile operations should not request elevation merely for convenience.
- A future privileged/system mode requires a separate safety design and is outside the initial MVP.

## Shell Integration

| Shell | Termux/Linux/WSL | Native Windows |
| --- | --- | --- |
| Bash | Supported target | Only when explicitly installed; not a native requirement |
| Zsh | Supported target | Only when explicitly installed in a compatible environment |
| Fish | Later supported target | Only when explicitly installed |
| PowerShell | Optional where installed | Primary native shell integration |

Environment data should generate correctly quoted shell-specific files. Shell startup should source generated static content instead of performing full CLI resolution every time.

## Windows and WSL Boundary

Native Windows and WSL may share the same remote Git repository and common modules, but they must use:

- Separate machine configuration.
- Separate transaction journals and backups.
- Platform-native canonical paths.
- Separate capability results.
- Explicit interop operations if one side needs to reference the other.

Do not place the WSL state database on a mounted Windows path by default. Do not assume a symlink created on one side has safe or equivalent behavior on the other.

## Support Matrix

Update this matrix only with verified results.

| Subsystem | Termux | Linux | WSL | Windows |
| --- | --- | --- | --- | --- |
| Core starts | Planned spike | Planned | Planned | Planned |
| Platform diagnostics | Planned | Planned | Planned | Planned |
| Spec resolution | Planned | Planned | Planned | Planned |
| Read-only plan | Planned MVP | Planned | Planned | Planned |
| Link/copy apply | Planned MVP | Planned | Planned | Planned |
| Backup/rollback/undo | Planned MVP | Planned | Planned | Planned |
| Package install | Planned after file MVP | Planned | Planned | Planned |
| Bootstrap | Planned after file MVP | Planned | Planned | Planned |
| Shell integration | Planned Zsh/Bash | Planned | Planned | Planned PowerShell |
| Hosted CI | To decide | Planned | To decide | Planned |

`Planned` is not a support claim. Replace it with explicit experimental or supported labels only after acceptance criteria and tests are documented.

