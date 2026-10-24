# Platform Model

**Status: Live platform adapters; native evidence and pending acceptance recorded by subsystem**

`dots` targets Termux, conventional Linux, WSL, and native Windows. Platform support is capability-based and tracked by subsystem rather than treated as a single yes/no label.

## Bash Framework Coverage

The live Bash dispatcher requires Bash 4.4+ and a POSIX-like executable environment.
Termux has native dispatch and Bash/Zsh/Fish completion tests, including interactive
Tab acceptance. Linux/WSL and MSYS are design targets, not newly verified platforms.
This Bash dispatcher does not provide general native Windows execution. A separate native PowerShell frontend dispatches file, Git, environment, theme and Anodize commands; see [native PowerShell](powershell.md) for implementation limits and pending Windows acceptance; no Windows/WSL path translation occurs. Ordinary unsymlinked invocation, help, and routing use Bash
builtins; resolving a symlinked launcher additionally requires `readlink`.

Personal Bash/Zsh/Fish startup uses [user-local completion directories](shell-init.md#user-local-completion-directories) with XDG-aware paths and priority over repository providers. Native discovery checks run in isolated Termux roots; Linux/WSL remain pending native acceptance for this change. PowerShell, Nushell and Xonsh retain their existing integrations. There is no native Windows equivalent of Zsh fpath registration, and Windows app destinations are unchanged; Windows PowerShell 5.1/7 startup acceptance remains pending.

The [tmux keybinding reference](commands.md#tmux-keybinding-reference) requires Bash 4.4+ and tmux's formatted key listing (`list-keys -F` with `q|a` quoting). Optional less provides paging; missing less falls back to printed output. Native Termux checks use tmux 3.7c, a disposable popup, and controlling-terminal less tests. Linux/WSL remain compatible design targets without new native evidence; native Windows is not supported by this Bash/tmux command. No paths are translated or dependencies installed.

The tmux system status row is enabled only when the tmux server inherits a nonempty `TERMUX_VERSION`; other environments show the tmux session/window row alone. Termux numbers remain ordered on the lower row; the current number and optional tmux name share one ` number:project ` badge, followed by windows before later numbers. Window labels omit names exactly matching the full tmux session name. Each badge/window has one space at each end. Numbering requires Python 3, the optional Androidots `termux-sessions` script, readable procfs and inherited `TERMUX_APP__PID`. The adapter locates that script through the repository's directory-linked tmux configuration. It matches each client's terminal ID rather than the server's launch ancestry; unmatched clients have no highlighted Termux entry. Missing discovery dependencies clear the segment without affecting the clock or tmux row. Native tmux 3.8 terminal rendering is verified in isolated Termux fixtures; the non-Termux branch is simulated there, not new Linux/WSL or Windows certification. See [tmux themes](themes.md#tmux).

The upper-row Android cluster requires Python 3 and the Androidots Wi-Fi/cellular scripts with their sibling `lib/termux_status` package. It invokes normal JSON reads, so the existing cache handles refresh work and permission gates. Connected Wi-Fi appears first; cellular appears only with explicitly disconnected Wi-Fi and enabled, connected mobile data. Missing, failed, expired or unknown Wi-Fi shows a neutral muted `?`, as does disconnected Wi-Fi with unavailable cellular activity. Only fresh disconnected Wi-Fi plus fresh confirmed inactive telephony data hides the segment. Retained stale connections keep `~`; uncertain decisions involving stale evidence show `?~`. Registered-cell signal alone does not establish active data or internet access. Notification, volume and location are not polled. Cellular polling needs a successful explicit interactive refresh, and provider failure suspends further automatic requests. No status job requests explicit refresh or changes permissions. Native tmux tests use mocked scripts/providers at 40/80/120 columns; they establish terminal layout, not live API access, signal accuracy or font rendering. See [activation](themes.md#tmux) and the [Androidots contract](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-status.md).

## Shell initialization coverage

Termux Bash/Zsh startup can automatically attach a default tmux session through `androidots/bin/termux-bar`. This adapter requires Python 3, tmux, readable procfs, the sibling session-discovery script and a validated `TERMUX_APP__PID` parent/session-leader relationship. It uses root PID/start time for per-tab identity. Automatic attachments exit the outer shell when the final pane exits; deliberate detach and unexpected server loss retain the plain shell. Other platforms, Fish, SSH and child shells skip automatic entry; `DOTS_TERMUX_AUTOSTART=0` opts out. Native Bash/Zsh/tmux PTY tests use simulated app identity, so actual Android new-tab startup remains a manual gate. See [lifecycle and fallbacks](shell-init.md#termux-tmux-startup).

The [initialization hook](shell-init.md) has native adapters for Bash, Zsh, Fish, Nushell, Xonsh, and PowerShell. Local Termux verification covers the first five installed interpreters; the Xonsh interactive fixture uses readline with a PTY. PowerShell is unavailable locally, so its native runtime tests are skipped and Windows startup remains unverified. The PowerShell adapter requires no Bash and does not translate Windows/WSL paths. Native startup files derive checkout paths through file and directory symlinks; PowerShell also resolves directory junctions. Native Windows link behavior remains unverified locally. Bash file-link resolution uses `readlink` without GNU-only options; Nushell uses parse-time `path self` with strict `path expand`. The separate native CLI adapters are described in [native PowerShell](powershell.md); their Windows runtime acceptance remains pending.

## Existing Zsh Configuration

The [existing shell configuration](../shells/zsh/README.md) has Termux-native checks and isolated Linux/WSL/MSYS detection fixtures. WSL uses Linux paths; MSYS has its own adapter boundary. Native Linux/WSL/MSYS interactive behavior remains unverified.

The default [Deja integration](../shells/zsh/README.md#deja-suggestions) has native Termux Android/ARM64 build and isolated daemon/Zsh PTY acceptance. It needs a native CGO/Clang source build, not upstream's Linux release binaries. Its data is under `$HOME/.local/share/deja` regardless of XDG settings. Linux/WSL x86-64 and ARM64 now have automatic GitHub release installation through Zinit, with executable validation and fallback to autosuggestions. Architecture selection, download failures and cached loading are tested in isolated fixtures, including real Zinit with synthetic release downloads. This is not native Linux/WSL executable or interactive acceptance. Termux and other platforms never receive Linux binaries automatically; no other native platform is verified for this integration.

## Terminology

- Platform identifies the execution environment.
- Distribution identifies a Linux-family package and system environment where relevant.
- Architecture identifies the release artifact and binary behavior.
- Capability describes what can actually be done at a particular destination.

## Standard Paths

| Purpose | Termux/Linux/WSL | Native Windows |
| --- | --- | --- |
| Home | Adapter-resolved user home | Known user profile folder |
| Repository default | `~/dots` initially | `%USERPROFILE%\dots` initially |
| Config | `$XDG_CONFIG_HOME/dots` or `~/.config/dots` | `%APPDATA%\dots` |
| Data | `$XDG_DATA_HOME/dots` or `~/.local/share/dots` | `%LOCALAPPDATA%\dots\data` |
| State | `$XDG_STATE_HOME/dots` or `~/.local/state/dots` | `%LOCALAPPDATA%\dots` (existing live state root) |
| Cache | `$XDG_CACHE_HOME/dots` or `~/.cache/dots` | `%LOCALAPPDATA%\dots\cache` |
| User executable | Adapter-selected path on `PATH` | User-owned application/bin path on `PATH` |

The repository path is configurable. Runtime state must not depend on the repository remaining at its default path.

## Privilege

- Termux does not use `sudo` for its ordinary userland package and configuration paths.
- Linux and WSL may or may not provide `sudo`; query the required operation and available mechanism.
- Native Windows elevation is distinct from Developer Mode and link capability.
- User-owned dotfile operations should not request elevation merely for convenience.
- A future privileged/system mode requires a separate safety design and is outside the current managed operations.

## Shell Integration

| Shell | Termux/Linux/WSL | Native Windows |
| --- | --- | --- |
| Bash | Supported target | Only when explicitly installed; not a native requirement |
| Zsh | Supported target | Only when explicitly installed in a compatible environment |
| Fish | Supported target | Only when explicitly installed |
| PowerShell | Optional where installed | Primary native shell integration |

Environment data should generate correctly quoted shell-specific files. Shell startup should source generated static content instead of performing full CLI resolution every time.

## Windows and WSL Boundary

Native Windows and WSL may share the same remote Git repository and source configuration, but they must use:

- Separate machine configuration.
- Separate transaction journals and backups.
- Platform-native canonical paths.
- Separate capability results.
- Explicit interop operations if one side needs to reference the other.

Do not place the WSL state database on a mounted Windows path by default. Do not assume a symlink created on one side has safe or equivalent behavior on the other.

## Bash Theme Integration

The palette engine and Zsh/Neovim adapters are natively tested on Termux, including
the additional fixed theme families and pywal16 snapshot import. Pywal16 input uses
explicit/cache paths without requiring a wallpaper tool at shell/editor startup. They use
XDG state/cache roots with HOME fallbacks and no path translation. Switching
requires `flock`, `sync -f`, `sha256sum`, AWK and standard file utilities; unsupported
capabilities fail at the operation boundary. Paths with spaces and Unicode are
covered in fixtures. WSL/Linux/MSYS execution remains unverified; native Windows
Bash execution and filesystem durability are not claimed. Native Windows and WSL
must retain separate state stores. Other applications and automatic Bash/Fish
prompt theming are outside this version. See [Shared themes](themes.md).

## Implemented Files and Theme Adapters

File catalog
commands use Python 3.9+ and POSIX flock, with read-only platform overrides for
inventory. Termux combines common and Androidots catalogs; Windots remains
inventory-only without a native Windows destination adapter. Discovery uses Git
and does not initialize submodules. `config/` is canonical in all three repositories.

Themes honor XDG config/state/cache roots. Fixed application connectors include
Termux colors; TERMUX_VERSION plus the Termux PREFIX boundary enables its reload and
explicit `termux-wallpaper` adapter. Linux wallpaper uses swww on Wayland or feh on
X11. WSL and native Windows wallpaper are unsupported. Termux:API, fzf, bat, tmux,
Kitty remote control and wallpaper tools are checked only when needed. Native
Termux fixture checks are recorded in [testing](testing.md); Linux adapter calls are
simulated, and native desktop rendering remains unverified.

The Pi connector uses `${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/themes/dots.json`,
not XDG config. An existing themes directory is required; absolute agent paths
and leading `~/` are supported, while relative paths and dot components are refused.
It uses the existing POSIX symlink journal. Pi 0.99.1 theme loading and directory-watch
reload have isolated native Termux coverage; desktop/WSL rendering and native Windows
connectors are not verified. See [Pi setup](themes.md#pi).

The Codex connector uses `${CODEX_HOME:-$HOME/.codex}/themes/dots.tmTheme`,
independently of XDG config roots. An existing themes directory and an absolute
home without control characters or dot components are required. Codex-Termux
uses the same home. The connector uses the existing POSIX symlink journal;
there is no native Windows connector or silent copy fallback. Native desktop/WSL
appearance remains unverified. See [Codex setup](themes.md#codex-and-codex-termux).

The eza connector is implemented in both the Bash and native Python publishers. The [eza destination rules](themes.md#eza) use XDG on Termux/Linux/WSL and APPDATA on Windows, with shared explicit overrides and no cross-platform path translation. Normal refresh requires an existing app directory. Native Termux eza is tested; Windows PowerShell 5.1/7, Linux and WSL runtime/visual acceptance remain pending.

## Bounded Git and file operations

The Bash Git engine requires Bash 5, Git, POSIX utilities and (for publish)
sha256sum; it rejects native Windows shell environments. New info/submodule views
and Bash submodule selection also require Python 3.9+. Native PowerShell invokes
Python and native Git directly, including scoped submodule publication, without
Bash. Linux/WSL and Windows native runtime/terminal acceptance are reported
separately from Termux/controller fixtures. File operations use the shared Python
engine with POSIX and native Windows adapters; Windows acceptance remains pending.
There is no privilege elevation, silent link-to-copy fallback or cross-Windows/WSL
translation. Windows app destinations are unchanged by the Git extensions.
Termux-owned discovery rules live in Androidots. See [Git](git.md),
[files](files.md), [native PowerShell](powershell.md) and
[verification](testing.md#git-and-managed-file-operations).

## Anodize scope

Terminal branding is capability-based, not platform-name based. Bundled braille text is the default on Unicode terminals, with portable ASCII for explicit ASCII mode, dumb terminals and redirected output. Optional Kitty rendering uses conservative environment hints and excludes unknown multiplexer passthrough; optional Chafa uses foreground-only braille output without probing. The [logo contract](anodize.md#terminal-logo) documents fallbacks and sizing assumptions. Native Termux PTY/text/Chafa checks and simulated Kitty protocol checks do not establish native Kitty, Linux/WSL graphics, or Windows support.

The pure Go Anodize library accepts bytes/data without platform paths. The CLI requires Python 3.11+ and a built engine, with Bash on POSIX hosts or native PowerShell on Windows. Publication uses shared file transactions and the platform theme adapters. Native Termux is verified; Linux/WSL integration and native Windows authoring are not newly verified. Wallpaper actions retain the existing fixed adapter support, including WSL refusal. No APK, Android language binding or TUI is shipped. See [Anodize](anodize.md).

## Theme plugin boundary

The [local theme plugin manager](theme-plugins.md) follows the existing Bash/Python
POSIX theme architecture. Execution supports Linux, WSL and Termux capability
boundaries; unsupported POSIX platforms report skipped execution. GTK 3 requires
`gtk-launch` plus an existing GTK 3 config directory; Qt6ct requires `qt6ct` plus
its config directory. Missing optional apps skip without installing anything.
Native Windows plugin execution is deferred. Native Termux fixture tests with
stub apps do not establish live GTK/Qt appearance or desktop reload behavior.

## Shared Bash/Zsh interactive adapters

The [shared shell configuration](shared-shells.md) uses builtin-only Termux/Linux/WSL/MSYS detection and native shell adapters. Bash retains the existing Bash 4.4+ requirement; cursor indicators are capability-gated by its bundled Readline version. Installed tools are optional, shell histories remain separate, and no paths are translated between Windows and WSL. Native interactive evidence is Termux-only; desktop and Windows support is not established by fixture detection checks.

Generated theme commands use Bash/POSIX wrappers and atomic symlink publication
under XDG state. Bash/Zsh startup and Bash/Zsh/Fish completion share Dots metadata.
Native Termux verification does not establish native Windows execution or desktop
appearance; no PowerShell wrapper or link-to-copy fallback is added. See
[theme commands](themes.md#unified-commands-and-family-shortcuts).

## Dots shell environment

The library-owned Dots environment has Bash, Zsh, Fish, Nushell, Xonsh and native PowerShell adapters. Native PowerShell initialization uses no Bash/Python; theme publication still uses the Bash CLI. Windows defaults use APPDATA for settings and LOCALAPPDATA for state. No WSL path translation is introduced. See [shell environment](shell-environment.md) for native variable forms and validation limits.

Theme file-style publication and `theme colors` require Python 3.11+ (`tomllib`);
Vivid is optional. Published JSON/Lua/LS_COLORS data remain platform-neutral. Native
Termux Bash/Zsh/Fish/Nushell and Yazi checks cover this change; PowerShell and
Xonsh adapter edits have no new native-runtime certification.

## Bounded checkout installation

The [checkout installer](installation.md) has POSIX shell and native PowerShell entry points sharing Python 3.9+ planning, receipt and transaction logic. Termux/Linux/WSL use their own HOME/XDG roots. Native Windows uses LOCALAPPDATA for state (unless XDG_STATE_HOME is explicit), PowerShell's current-host profile, Neovim's native configuration root and APPDATA/Code/User/settings.json. The [native PowerShell implementation](powershell.md) adds app-specific root/Windots destinations and native theme preparation/publication; Windows runtime and desktop acceptance remain pending. Full theme setup requires Python 3.11+. No WSL path translation, package provisioning, elevation or link-to-copy fallback occurs.

Native Windows locking uses msvcrt; directory flushing has no POSIX-equivalent guarantee. Symlink capability is tested by approved staging before target replacement. Reparse-point ancestors are refused. Linux/Windows installation CI is defined; local Termux tests do not establish native Windows or WSL results.

The managed Starship config destination is home-relative `.config/starship.toml`
on POSIX and native Windows, independently of XDG_CONFIG_HOME. Personal startup
clears recognized old Dots overrides without setting STARSHIP_CONFIG. Native
Bash/Zsh/Fish/Nushell checks cover Termux; PowerShell/Clink Windows runtime and
Xonsh startup acceptance remain pending.

The optional Starship/Blastoff theme adapter follows the existing POSIX theme-plugin boundary (Termux, Linux and WSL; native Windows unavailable). It uses `STARSHIP_CONFIG`/`BLASTOFF_HOME` or those apps' standard home-relative paths, preserves configured symlinks through guarded physical targets, and does not translate Windows paths. Native verification currently covers Termux with Starship 1.26.0.

The consolidated Git directory resource is mapped for Termux, Linux, WSL and
native Windows installation. Its selector chooses the matching regular overlay;
plain Linux has an empty override. Native Windows still requires link capability
and does not gain POSIX managed-operation commands or theme publication. Git/Delta
colors and selector lifecycle have native Termux tests and platform-selection
fixtures; native Windows/WSL consumer execution is not established.

Anodize user saves use the existing platform configuration adapter: XDG when
explicit, otherwise `~/.config/dots/themes` on POSIX and `%APPDATA%/dots/themes`
on Windows. `--builtin` and `promote` target the selected native checkout. Both
frontends share the authoring/picker controller and journal; Windows application
connector destinations are unchanged. Native PowerShell 5.1/7 FZF keyboard,
preview and interruption acceptance remains pending where engines are unavailable.

## Androidots location adapter exception

`termux-geo` device acquisition requires Android/Termux and Termux:API. There is no corresponding native Windows PowerShell 5.1/7, Linux, or WSL acquisition adapter in this scope, and no Windows app destination changes. Personal Androidots completion paths are added only for interactive Termux shells; other platform paths remain unchanged. Mock-provider tests and native Termux Bash/Zsh/Fish completion checks do not establish native GPS/network-provider, Android permission, or service-cancellation acceptance. See [location requirements and limits](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-geo.md#verification-and-platform-limits).

Separate owner-device checks verified network acquisition and cache reuse after removing an incompatible file-size resource limit from the API wrapper. GPS, permission denial/recovery and Android service cancellation remain pending; see the [native repair evidence](../plans/termux-geo.md#native-timeout-repair).

## wttr weather

The shared Python 3.11+ weather controller has Bash and native PowerShell entries. Unix config/cache use XDG defaults; Windows configuration uses APPDATA/wttr and cache uses LOCALAPPDATA/cache/wttr unless XDG overrides are explicit. The catalog Windows app destination is `${APP_CONFIG:wttr}`. Manual/default weather is portable. Stock wttr.in requests require native `curl` on Unix or `curl.exe` on Windows; JSON-backed views retain their Python standard-library transport. Android acquisition and tmux daylight styling are Termux-only; there is no native Windows location provider in this slice. Native Windows PowerShell 5.1/7, Windows locks/ACLs and completion runtime acceptance remain pending on this Termux host. See [weather behavior and verification limits](wttr.md).

The Television connector is implemented in both publishers. Its [destination rules](themes.md#television) match Television 0.15.9, including native Windows LOCALAPPDATA and explicit overrides. An existing app directory is required; its missing `themes` child is journaled. Native Windows PowerShell 5.1/7, Linux and WSL acceptance remains pending; Termux and fixture evidence is recorded in [testing](testing.md#television-theme).

Leaf UI and syntax connectors use both publishers and the shared [destination rules](themes.md#leaf). Native Windows uses APPDATA/leaf and the existing link adapter; a missing APPDATA leaves it unmapped. Leaf external syntax support is a separate portable Rust patch. Termux native evidence does not establish Windows PowerShell 5.1/7, Linux or WSL runtime/visual acceptance; those remain pending.
