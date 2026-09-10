# Platform Model

**Status: Permanent read-only core and independent experiment verified on native Termux and Linux/Windows CI; broader platform model proposed**

`dots` targets Termux, conventional Linux, WSL, and native Windows. Platform support is capability-based and tracked by subsystem rather than treated as a single yes/no label.

## Permanent Development Core

The root core ports the experimental read-only platform adapter and optional-logo opening unchanged, including schema 1, marker heuristics, candidate Unix paths, missing Windows path warnings and `not_probed` capabilities. Its registry uses injected availability metadata and does not perform capability probes. Root-core checks and fresh benchmarks passed on Termux Android/ARM64 and on Linux/AMD64 and Windows/AMD64 in CI; this is development coverage of the read-only surface. The native root-core verification and fresh timing results are tracked separately in the [first-slice plan](../plans/phase-2-command-center.md); the historical observations below retain their original executable identities. Native Windows known folders/restricted ACLs, WSL execution, other architectures, broader filesystems and production OS floors remain deferred. No apply/package/bootstrap/shell support follows from core startup.

### Development External Execution

[Decision 0003](decisions/0003-trusted-external-command-protocol.md) adds native execution behind explicit trusted roots. Termux/Linux require regular executable files and use direct process replacement; shebang resolution belongs to the OS, with no shell retry or Termux rewriting. Windows accepts `.exe` with Go's CommandLineToArgvW-compatible quoting, inherited standard handles and the same console. Root policy requires local fixed-drive NTFS and disabled per-directory case sensitivity; UNC/device/ADS/drive-relative paths and immediate reparse entries are refused. Resolved root aliases are deduplicated by object identity. No POSIX permission assumption is applied on Windows.

Native interruption acceptance requires Unix signal/PID checks and actual Windows console broadcasts for Ctrl+C and Ctrl+Break. Results are tracked in the [external slice](../plans/phase-2-command-center.md#authorized-external-command-slice). A .exe extension using a custom shell parser is outside the argument contract. WSL execution remains explicitly unavailable even with matching metadata. These restrictions do not establish production OS floors, known-folder resolution, restricted ACL policy, cross-volume/network filesystems, other architectures, or descendant cleanup.

## Implemented Phase 1 Observations

The separate `dots-spike` executable has been built and run natively with Go 1.27.1 on Termux 0.119.0-beta.3, Android API 35, ARM64, kernel `5.4.274-qgki-30957850-abG996USQSJHZB1`. Test-owned directories under the Termux temporary directory report f2fs. Successful file/directory symlinks and explicit regular-file copies apply only to these fixtures, not Android shared storage or every possible destination.

The Android/ARM64 build uses `CGO_ENABLED=0`, the default Android PIE mode, `-trimpath`, `-buildvcs=false`, and no third-party modules. ELF inspection reports `/system/bin/linker64` as interpreter and no `DT_NEEDED` shared-library entries. Thus the executable still requires the Android runtime/loader; it does not require an installed Go runtime, Python, shell helpers, or additional declared shared libraries. It starts with an empty `PATH`. Rebuilding the same source from another directory with the same toolchain produced identical bytes; this is not a multi-toolchain or release reproducibility claim.

Linux/AMD64 and Windows/AMD64 executables and test binaries were cross-compiled using the installed Termux toolchain. They were not executed. Windows/WSL detector fixtures ran on Termux, not on those systems. Native Linux and Windows CI execution is recorded separately below. WSL execution, Windows policy/filesystem variations beyond these fixtures, Android shared storage, other Android architectures, public release delivery, and installation remain unverified. See the [focused results](../plans/phase-1-portability.md).

### Native Linux Validation Status

The shared harness built and executed the Linux/AMD64 executable and all 13 Go tests in [GitHub Actions run 34416309614](https://github.com/5nik7/dots/actions/runs/34416309614) on 2026-09-09. The runner reported Ubuntu 24.04.5 LTS, image `20260907.300.1`, kernel `6.17.0-1022-azure`, and `stat -f` filesystem type `ext2/ext3` (an ext-family magic label, not a precise mounted-filesystem claim). Four Python tests, empty-PATH CLI checks, read-only snapshots, logo replacement cases, file/directory symlinks, exclusive copies, and relocated identical rebuild all passed in owned roots. The 3,991,208-byte Go 1.27.1 binary has no ELF interpreter or `DT_NEEDED` entries. Startup measurements are Linux CI observations, not controlled cold-cache or physical desktop-hardware results. Windows execution and bounded distribution validation are recorded below; public release delivery and installation remain pending. See [testing.md](testing.md#native-linux-and-windows-ci) for tool provisioning, telemetry isolation, and artifact retention.

### Native Windows Validation Status

[Run 34421915915](https://github.com/5nik7/dots/actions/runs/34421915915), at `fe0e5d722a322bca9d97c48aaa1dac688752e17a` on 2026-09-10, built and executed the Windows/AMD64 executable, 14 top-level Go tests, and six Python regressions. The `windows-2025` runner reported Windows build 26100, image `win25-vs2026` / `20260907.229.1`, four logical CPUs, and NTFS. Empty-PATH help/version/human and JSON diagnostics, optional logos, unchanged fixture snapshots, independent copies, file/directory links, existing-target refusal, spaces/Unicode/leading dashes, missing parents, and traversal/link escape checks passed. Both symlink types were available; no permission denial was observed. Windows directory-rooted operations refused existing directories with `EISDIR`, and tests verified preservation after that refusal.

The Go 1.27.1 `CGO_ENABLED=0` executable is 4,207,104 bytes, with SHA-256 `8850624e20a07a8f983b851fd0427f41a0d0e896b1c07b857ff3993afd5a909a`. LLVM 20.1.8 identified an AMD64 PE/COFF image with `kernel32.dll` in its static import table. Native execution with an empty PATH passed, but static imports do not enumerate dynamic/transitive Windows DLL dependencies. Relocated rebuild and check/benchmark binaries matched byte-for-byte.

These results apply to this hosted runner and its disposable NTFS fixtures. Developer Mode, registry, elevation, and security policy were not changed by verification. A machine that denies links is not represented by this success: refusal classification is separately regression-tested with mocked errors 5, 50, and 1314. Windows ACL-denied logos, UNC/network paths, junctions, long-path policy, cross-volume behavior, and ordinary unelevated desktop policy variations remain untested. Native Windows known-folder resolution remains unimplemented; `doctor` reports capabilities as `not_probed`. See the [focused results](../plans/phase-1-portability.md#bounded-native-windows-follow-up) for startup and artifact provenance.

### Experimental Read-Only File Opening

Help uses a platform adapter for read-only file opening. Unix builds, including Termux and Linux/WSL, use `O_NONBLOCK` so opening a logo replaced with a FIFO does not wait for a writer. The CLI validates the actual opened handle before reading and omits non-regular, empty, or oversized objects. Valid symlinks to regular logo files remain supported. Non-Unix builds retain native `os.Open` semantics and use the same handle validation; this does not provide a Unix FIFO guarantee on Windows or a general filesystem I/O deadline.

The deterministic replacement tests passed natively on Termux and Linux CI. Windows execution is recorded separately; Unix FIFO behavior is unavailable on Windows, Windows ACL-denied logos are untested, and shared-storage behavior remains unverified.

### Experimental Detector and Paths

The collector reads only `HOME`, `PREFIX`, `TERMUX_VERSION`, `DOTS`, the four XDG home variables, `TMPDIR`, `WSL_INTEROP`, and `WSL_DISTRO_NAME`. It also observes Go runtime/executable identity; on Android/Linux it checks the prefix's `bin` directory and Android linker metadata; on Linux it reads at most 4096 bytes of `/proc/sys/kernel/osrelease`. It does not read dotfile contents, enumerate the full environment, query packages, or invoke a shell. Environment evidence reports marker presence rather than arbitrary values.

Native Windows runtime identity takes precedence. Termux classification requires Android evidence (the Android Go runtime or an Android linker), a nonempty Termux version marker, and an absolute prefix ending in `usr` with an existing `bin` directory. Android without sufficient Termux evidence reports `unknown`. A conventional Linux runtime checks WSL environment or case-insensitive Microsoft kernel markers before reporting `linux`. These markers are heuristic observations, not authentication; manually forged environments can mislead classification. There is no public override flag in the spike; unit tests inject inputs directly.

For Termux/Linux/WSL, diagnostics reports the Unix path candidates in the table below. Relative environment paths are rejected with a warning and use a valid default candidate where available. Missing/invalid `HOME` does not trigger account-database lookup or invent home-relative candidates. The repository candidate uses `$DOTS` or `<home>/dots`; `temp` uses an absolute `$TMPDIR`, otherwise `<prefix>/tmp` on Termux or `/tmp` on Linux/WSL. These are candidates, not a claim that directories exist, are owned, or are writable. `executable` is the observed binary path; it is not an installation recommendation.

Windows and unknown platforms report runtime identity, executable path when available, and a warning that path resolution is unimplemented. Native Windows known-folder resolution remains proposed. No platform has a live capability probe in `doctor`: `file_symlink`, `directory_symlink`, and `copy` always report `not_probed`.

### Experimental Distribution Validation

The harness implements native experimental `.tar.gz` bundles for Termux Android/ARM64 and Linux/AMD64, and `.zip` bundles for Windows/AMD64. Native distribution validation passed on Termux and in [Linux and Windows run 34423939448](https://github.com/5nik7/dots/actions/runs/34423939448) at `613e64c7de8fd16a858554fd26f3a451f316e764`. All three targets rejected a corrupt archive before extraction/execution and ran help with the bundled logo, version, and JSON diagnostics from fresh paths containing spaces and Unicode. Runtime snapshots were unchanged; Unix modes and identical extracted executable bytes were verified. Windows POSIX execute bits are not applicable. Each bundle uses executable-relative logo discovery and contains the committed public logo, never the owner’s unrelated working-tree edit. The extracted binary is checked against the build, then executed with empty PATH and isolated roots after the original copied build inputs are removed. Unix execute permissions are verified; Windows proves process execution without assigning POSIX permission semantics. Format regressions cover both archive types on each host; they do not establish foreign-target execution. See [testing.md](testing.md#experimental-distribution-check) for layout, checksum/path guarantees, and bounded-extractor limitations. Permanent releases, publisher authentication/signing, authenticated download transport, and installation remain undecided or untested.

## Terminology

- Platform identifies the execution environment.
- Distribution identifies a Linux-family package and system environment where relevant.
- Architecture identifies the release artifact and binary behavior.
- Capability describes what can actually be done at a particular destination.
- Profile selects desired modules independently of platform.

## Initial Platform IDs

The [accepted Phase 1 adoption decision](decisions/0002-phase-1-go-adoption.md#initial-targets-and-toolchain) defines initial development targets and distinguishes observed environments from production OS floors. Its [gap classifications](decisions/0002-phase-1-go-adoption.md#remaining-gaps-and-gates) are accepted; this support matrix is not upgraded by language adoption.

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
| File symbolic link | Verified in disposable f2fs fixtures only | Verified in disposable Linux CI fixtures only | Expected inside distribution | Verified in disposable NTFS CI fixtures only; other policies untested |
| Directory symbolic link | Verified in disposable f2fs fixtures only | Verified in disposable Linux CI fixtures only | Expected inside distribution | Verified in disposable NTFS CI fixtures only; other policies untested |
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
| Core starts | Experimental: native Android/ARM64 | Experimental: native AMD64 on Ubuntu CI | Not run | Experimental: native AMD64 on Windows CI |
| Platform diagnostics | Experimental: native evidence and candidate paths | Experimental: native Linux identity with owned path fixtures | Detector fixtures only | Experimental: native Windows identity; known-folder paths deferred |
| Spec resolution | Planned | Planned | Planned | Planned |
| Read-only plan | Planned MVP | Planned | Planned | Planned |
| Link/copy apply | Planned MVP | Planned | Planned | Planned |
| Backup/rollback/undo | Planned MVP | Planned | Planned | Planned |
| Package install | Planned after file MVP | Planned | Planned | Planned |
| Bootstrap | Planned after file MVP | Planned | Planned | Planned |
| Shell integration | Planned Zsh/Bash | Planned | Planned | Planned PowerShell |
| Hosted CI | To decide | Experimental: native Phase 1 check and bench | To decide | Experimental: native Phase 1 check and bench |

`Planned` is not a support claim. Replace it with explicit experimental or supported labels only after acceptance criteria and tests are documented.
