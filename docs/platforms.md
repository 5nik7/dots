# Platform Model

**Status: Live platform adapters; native evidence and pending acceptance recorded by subsystem**

## Personal fonts

Installed discovery uses optional fontconfig on Termux/Linux/WSL and HKCU/HKLM font registrations on Windows. Migration is limited to supported user-owned roots; system fonts are copy-only. App choices retain files in the active profile and save `fonts.json`, with explicit Restore on every shared frontend. Mocked Windows migration/registration fixtures do not establish native font visibility or file-lock behavior.

Termux/Linux/WSL user-font links use `${XDG_DATA_HOME:-~/.local/share}/fonts/dots`
with optional fontconfig refresh. Termux Set copies a TTF to that home's
`.termux/font.ttf`, never Android fonts. Windows copies to
`%LOCALAPPDATA%/Microsoft/Windows/Fonts`, journals HKCU registration and attempts
a session notification without administrator access. Locked native files cause
guarded failure. Windows Terminal settings require native Windows; Kitty has no
native Windows target. Other desktop targets use managed mappings or explicit
config files. WSL never translates host paths. Literal insertion needs verified
POSIX tmux context; Windows offers copy/print and terminal FZF. See
[fonts](fonts.md) and [native evidence limits](../plans/fonts.md#evidence).

Directory mode stores versioned payloads under `DOTFONTS` or a backend profile `*FONTS` path without OS registration. The same shared controller resolves literal directory names on every platform; choosing another platform's profile directory does not change the execution platform. Explicit Use/Set copies into the current platform's personal library before activating through its existing adapter. Native Windows and WSL inventories remain separate. Directory, registration and application fixtures run in owned roots; actual native Windows/PowerShell and visible desktop activation remain pending.

`dots` targets Termux, conventional Linux, WSL, and native Windows. Platform support is capability-based and tracked by subsystem rather than treated as a single yes/no label.

The managed `dots:less` configuration targets `${CONFIG}/lesskey` on Termux/Linux/WSL and `${HOME}/_lesskey` on native Windows. Less 702+ reads its persistent mouse settings directly, without Bash or a theme connector. Termux less 710 mouse behavior is verified in private terminals; Linux/WSL and native Windows runtime acceptance remains pending. See [less mouse support](shell-environment.md#global-less-mouse-support) for overrides and older-version fallback.

## Bash Framework Coverage

The live Bash dispatcher requires Bash 4.4+ and a POSIX-like executable environment.
Termux has native dispatch and Bash/Zsh/Fish completion tests, including interactive
Tab acceptance. Linux/WSL and MSYS are design targets, not newly verified platforms.
This Bash dispatcher does not provide general native Windows execution. A separate native PowerShell frontend dispatches file, Git, environment, theme and Anodize commands; see [native PowerShell](powershell.md) for implementation limits and pending Windows acceptance; no Windows/WSL path translation occurs. Ordinary unsymlinked invocation, help, and routing use Bash
builtins; resolving a symlinked launcher additionally requires `readlink`.

Personal Bash/Zsh/Fish startup uses [user-local completion directories](shell-init.md#user-local-completion-directories) with XDG-aware paths and priority over repository providers. Native discovery checks run in isolated Termux roots; Linux/WSL remain pending native acceptance for this change. PowerShell, Nushell and Xonsh retain their existing integrations. There is no native Windows equivalent of Zsh fpath registration, and Windows app destinations are unchanged; Windows PowerShell 5.1/7 startup acceptance remains pending.

The [tmux keybinding reference](commands.md#tmux-keybinding-reference) uses the shared `dots keys tmux` controller and an existing tmux server with formatted key listing (`list-keys -F` with `q|a` quoting). Optional FZF provides browsing; missing FZF falls back to printed output. Native Termux checks use private servers and disposable FZF popups. Linux/WSL and native Windows terminal acceptance remain separate; tmux is an optional capability on Windows. No paths are translated or dependencies installed.

The tmux system status row is enabled only for a server inheriting `TERMUX_VERSION`; other environments retain their normal tmux row. Termux tab numbers appear after the clock, while the lower row contains only the current tmux session and its windows. Codex activity/attention can decorate other tab numbers, with a separate badge for alerting sessions displayed by no live tab. Matching uses attached client TTYs and validated tab PID/start time. Stock Termux 0.119.0-beta.3 does not implement DECSET 1004 focus reporting: conservative delivery never trusts its default client focus flags, and Prefix a explicitly acknowledges the current pane. Linux/WSL retain terminal-focus handling. Native Windows/PowerShell have no tmux/Android consumer or changed application destination. Real Android/Codex delivery and Linux/WSL visual acceptance remain separate from private Termux fixtures. See [tmux themes](themes.md#tmux).

The upper-row Android cluster requires Python 3 and the Androidots Wi-Fi/cellular scripts with their sibling `lib/termux_status` package. It invokes normal JSON reads, so the existing cache handles refresh work and permission gates. Connected Wi-Fi appears first; cellular appears only with explicitly disconnected Wi-Fi and enabled, connected mobile data. Missing, failed, expired or unknown Wi-Fi shows a neutral muted `?`, as does disconnected Wi-Fi with unavailable cellular activity. Only fresh disconnected Wi-Fi plus fresh confirmed inactive telephony data hides the segment. Retained stale connections keep `~`; uncertain decisions involving stale evidence show `?~`. Registered-cell signal alone does not establish active data or internet access. Notification, volume and location are not polled. Cellular polling needs a successful explicit interactive refresh, and provider failure suspends further automatic requests. No status job requests explicit refresh or changes permissions. Native tmux tests use mocked scripts/providers at 40/80/120 columns; they establish terminal layout, not live API access, signal accuracy or font rendering. See [activation](themes.md#tmux) and the [Androidots contract](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-status.md).

## Shell initialization coverage

Termux Bash/Zsh startup can automatically attach a default tmux session through `profiles/termux/bin/termux-bar`. This adapter requires Python 3, tmux, readable procfs, the sibling session-discovery script and a validated `TERMUX_APP__PID` parent/session-leader relationship. It uses root PID/start time for per-tab identity. Automatic attachments exit the outer shell when the final pane exits; deliberate detach and unexpected server loss retain the plain shell. Other platforms, Fish, SSH and child shells skip automatic entry; `DOTS_TERMUX_AUTOSTART=0` opts out. Native Bash/Zsh/tmux PTY tests use simulated app identity, so actual Android new-tab startup remains a manual gate. See [lifecycle and fallbacks](shell-init.md#termux-tmux-startup).

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

`files repair` uses the detected platform's catalog and native application destination resolver on both Bash and PowerShell. The issue helper shares terminal FZF/Gum and numbered fallbacks; selection and confirmation require no Bash on native Windows. It never applies a foreign platform mapping or translates Windows/WSL paths. Native link-capability refusal is explicit, with no elevation or copy fallback. Termux fixture checks cover portable repair logic; Windows PowerShell 5.1/7 link, recovery and terminal acceptance remain pending until run natively.

File catalog commands use shared Python 3.9+ controllers and native POSIX/Windows
filesystem adapters, with read-only platform overrides for inventory. Termux and
Windows combine universal resources with their bundled profile catalogs. Windows
app-specific destinations are mapped explicitly; ambiguous destinations remain
unmapped. Discovery does not initialize submodules. `config/` remains canonical
in the universal and platform trees.

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
Termux-owned discovery rules live in `profiles/termux`. See [Git](git.md),
[files](files.md), [native PowerShell](powershell.md) and
[verification](testing.md#git-and-managed-file-operations).

## Anodize scope

Anodize default branding uses exact UTF-8 LOGO1/LOGO2 on every platform, including pipes, disabled icons and dumb terminals; it is independent of graphics capability. Explicit Kitty/Chafa choices retain capability checks and fall back to the supplied text artwork. See the [authoritative logo contract](anodize.md#terminal-logo). Native Termux PTY/text/Chafa and shared native-controller fixtures do not establish Linux/WSL, native Kitty or Windows rendering acceptance.

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

The library-owned Dots environment has Bash, Zsh, Fish, Nushell, Xonsh and native PowerShell adapters. Native PowerShell initialization uses no Bash; Python prepares its profile environment on a cold load and the native adapter handles warm loads. Theme publication uses the shared native controller. Windows defaults use APPDATA for settings and LOCALAPPDATA for state. No WSL path translation is introduced. See [shell environment](shell-environment.md) for native variable forms and validation limits.

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

The shared Python 3.11+ weather controller has Bash and native PowerShell entries for standalone `wttr` and `dots wttr`. Explicit `browse` routes use exact-client tmux popups on supported POSIX hosts and native terminal selection elsewhere, falling back to the ordinary report without FZF/terminal support. Unix config/cache use XDG defaults; Windows configuration uses APPDATA/wttr and cache uses LOCALAPPDATA/cache/wttr unless XDG overrides are explicit. The catalog Windows app destination is `${APP_CONFIG:wttr}`. Manual/default weather is portable. Stock wttr.in requests require native `curl` on Unix or `curl.exe` on Windows; JSON-backed views retain their Python standard-library transport. Android acquisition and tmux daylight styling are Termux-only; there is no native Windows location provider in this slice. Native Windows PowerShell 5.1/7, Windows locks/ACLs and completion runtime acceptance remain pending on this Termux host. See [weather behavior and verification limits](wttr.md).

The Television connector is implemented in both publishers. Its [destination rules](themes.md#television) match Television 0.15.9, including native Windows LOCALAPPDATA and explicit overrides. An existing app directory is required; its missing `themes` child is journaled. Native Windows PowerShell 5.1/7, Linux and WSL acceptance remains pending; Termux and fixture evidence is recorded in [testing](testing.md#television-theme).

Leaf UI and syntax connectors use both publishers and the shared [destination rules](themes.md#leaf). Native Windows uses APPDATA/leaf and the existing link adapter; a missing APPDATA leaves it unmapped. Leaf external syntax support is a separate portable Rust patch. Termux native evidence does not establish Windows PowerShell 5.1/7, Linux or WSL runtime/visual acceptance; those remain pending.

## Profiles and distro facts

The profile resolver distinguishes execution platform from distro and shell
runtime. WSL inherits Linux profile layers but retains separate native paths and
state. Termux and Windows have independent layers. Distro directories are added
only for actual overrides. See [profile detection](profiles.md). Native Linux,
WSL and Windows PowerShell 5.1/7 startup acceptance remains pending where only
Termux and injected-platform fixtures have been run.

Profile/debug routes share controllers across Bash and native PowerShell. Startup
measurement uses native adapters: Zsh additionally provides filename-only source
entry discovery; Bash/PowerShell cover instrumented Dots phases and modules.
PowerShell rejects POSIX `--login`. Native Windows uses Job Objects for child
ownership and requires separate PowerShell 5.1/7 acceptance; no Bash dependency
is introduced. See [debugging](debug.md).

File catalog identities now match their platform names: `termux` and `windows`. This rename does not change Windows application destinations or combine Windows/WSL state. All native shell adapters clear retired Dots Ruby exports and completion PATH entries; native Windows PowerShell 5.1/7 and Xonsh execution remain pending on this Termux host. See [retired environment](shell-environment.md#retired-ruby-environment).

The wiki uses shared Python controllers for Bash and native PowerShell. Native Windows has its own checkout path via HOME/USERPROFILE or `DOTS_WIKI_DIR`; no WSL path translation is performed. Atomic acquisition uses Windows no-replace rename or Linux/Termux renameat2. Unsupported acquisition platforms refuse publication of the clone; read/generate operations remain portable. Native Windows PowerShell 5.1/7 and hosted wiki rendering remain separate acceptance gates.


Detailed debug views share a controller across Bash/Zsh and PowerShell. Bash/Zsh use native debug hooks with observation-interval attribution. PowerShell uses supported global primitive/environment snapshots, preferences and non-stopping breakpoints for registered script files; opaque objects, local scopes and arbitrary dynamic sources are outside its claimed coverage. Actual Windows PowerShell 5.1/7 acceptance remains pending where unavailable.

The keybinding browser uses native shell capture and a shared controller. Zsh/Bash maps are available through the interactive adapter; native Windows uses PSReadLine and PowerShell rather than Bash. Application config roots honor native/XDG paths; live tmux requires an existing server. Yazi and Codex include bundled versioned default references and require neither application installation nor network access for those rows. Yazi keeps its selected native/XDG config location, including `%APPDATA%/yazi/config` on Windows. Codex reads `CODEX_HOME/config.toml` or the native user home’s `.codex/config.toml` on every platform; it does not use XDG or APPDATA. Providers report version and dynamic coverage limits explicitly. See [keybindings](keys.md).

The tmux shortcut can request live Zsh maps from its originating pane through a
private Unix socket on Termux/Linux/WSL. It requires Zsh's socket, filesystem and
stat modules plus Python 3; missing capabilities use explicitly labeled configured
coverage. Native Windows does not install this ZLE transport or translate WSL
paths; its existing PSReadLine caller capture remains the native route. Termux
PTY/controller checks do not establish native Linux/WSL or Windows acceptance.

The shared menu library supports ordinary terminal selection and literal frontend dispatch on both POSIX and native Windows. Tmux context capture and terminal popups are POSIX-only and never invoke WSL implicitly. The shared output reader uses optional native less or a read-only native FZF fallback, with the same menu navigation and command-status contract. The Git family and its preview/confirmation gate use the shared controller on both frontends. Fitted reader popups apply only to tmux; native Windows retains the ordinary terminal reader and existing Git controller. No Bash pager pipeline is required. No Windows app destination changes are introduced. `dots menu tmux sessions` is implemented on both dispatchers but reports unavailability on native Windows, without probing tmux or launching WSL. `dots menu` uses ordinary terminal FZF on native Windows and keeps the unavailable tmux entry visible. Termux private-server and portable native-shell argument tests do not establish Windows PowerShell 5.1/7, Linux or WSL terminal acceptance. See [shared menu support](architecture.md#shared-menu-support).


The tmux session browser's project and create/rename/delete actions share the
POSIX controller on Termux, Linux and WSL. Only shared platform detection of
Termux exposes New Termux (a terminal tab in the existing app, not a separate
Android window). It probes `termux-am` and falls back to the Termux-installed
legacy `am` when the socket adapter is unavailable. Working app access is still
required; Dots does not change settings or permissions. A fixed Python helper
attaches without shell startup or client detachment. Automated suites mock the
Android boundary; separate device evidence is recorded in the
[popup-menu plan](../plans/popup-menus.md). Windows retains status-2 tmux refusal,
without WSL bridging or destination changes.

### Less terminal colors

[Global less styling](shell-environment.md#global-less-colors) uses termcap RGB overrides on Termux, Linux and WSL. Native Windows less has no equivalent termcap RGB rendering path and retains stock colors; this is an explicit platform exception, not a WSL fallback. Native shell adapters preserve the same override/ownership rules, with the PowerShell POSIX path supported in code. Native Windows PowerShell 5.1/7 and non-Termux visual acceptance require their own checks.

## Bundled application platforms

[Blastoff and pkgs](bundled-applications.md) ship with both Bash and native PowerShell routes. Blastoff invokes its Python 3.11+ core on all Dots platforms and retains `STARSHIP_CONFIG` / `BLASTOFF_HOME` with their existing home-relative defaults. pkgs retains Python 3.9+ POSIX package backends on Termux/Linux/WSL. Native Windows supports pkgs help/version and static discovery; commands other than help/version refuse with status 3 before importing POSIX-only modules. WSL remains a separate installation.

Standalone native launchers use `~/.local/bin/*.ps1`, with no registry or system PATH changes. Native Windows PowerShell 5.1/7 and WSL runtime acceptance for absorption remains pending; injected adapter tests do not establish it.

Application plugins share native launchers and the combined installer. Legacy receipt migration supports known POSIX user-local and Termux layouts; former native PowerShell modules/profile edits require manual reconciliation. Native Windows pkgs remains limited to help/version. Relocation and popup changes require separate native Windows/WSL acceptance. See [plugins](plugins.md).

### Codex attention notifications

The optional [Codex attention bridge](themes.md#codex-attention-notifications) uses the same Python implementation with Bash/Zsh/Fish-launched tmux on Termux, Linux and WSL. It requires Python 3.11+, tmux and same-user procfs observation; setup additionally capability-checks tomlkit. Android toast/vibration is enabled only in Termux and each executable is checked independently. Native Windows has neither a tmux destination nor a Termux API adapter: the setup helper explicitly refuses there, while pure event/configuration tests remain portable to PowerShell's Python invocation. Native Termux fixture results do not establish Linux/WSL visuals, terminal-emulator focus reporting, real Android delivery or Codex hook trust/reload behavior.

## Todo goals

Both `dots todo` and standalone `todo` use the shared Python controller on Termux, Linux, WSL and native Windows. The native `todo.ps1` entry uses the existing literal argument bridge. Global data uses the native Dots state root; project registrations use the native configuration root. Project files live in the selected checkout without Windows/WSL translation. Setup includes a native standalone command adapter. The three Todo skill resources target their respective directories under the user's `.codex/skills`; custom skill destinations require an explicit managed override. They share directory-link, backup and recovery behavior across the four platform profiles; native Windows link privileges still require separate runtime verification.

Tmux popups apply only on POSIX; Windows uses terminal FZF with native PowerShell preview syntax and optional native Gum/plain input. No application configuration destinations change. Actual Linux/WSL and Windows PowerShell 5.1/7 terminal, completion and link-privilege acceptance remains pending where those hosts are unavailable. See [todo](todo.md).

Dots configuration is checkout-local under the resolved platform profile: `profiles/termux`, `profiles/linux`, `profiles/wsl`, or `profiles/windows`, including inherited distro definitions. User themes and runtime state keep their platform user-directory locations. The explicit legacy migration uses the native config-root adapter and never translates Windows/WSL paths. Windows app destination tokens are unchanged. Native PowerShell 5.1/7 and native Linux/WSL acceptance of profile configuration remains separate from Termux and portable fixture evidence. See [profile configuration](profiles.md#profile-configuration).

Todo planning shares `todo plan ID [--new] [--dry-run]`, brief export, completion and popup actions across Bash and native PowerShell. Termux uses the existing codex-termux runit connection; native Linux/WSL/Windows use native Codex daemon/proxy capabilities, with runtime acceptance pending outside the isolated Termux fixture. Windows uses the current terminal and native Set-Clipboard, with no tmux or WSL translation; app installation destinations are unchanged. See [Todo planning](todo.md#plan-a-goal-in-codex).

Profile implementations use one target per profile. The permanent core registry owns platform eligibility; Windows app tokens remain native Windows destinations. Generated namespaces include inactive profiles without putting them on PATH or translating paths across Windows/WSL. Shell representations and the protected PowerShell `$PROFILE` are specified in [profiles](profiles.md#generated-profile-paths). Native Windows PowerShell 5.1/7 acceptance for generated maps remains pending on this Termux host.

Core config/file-ID and singular command-family updates use shared Bash/native
PowerShell controllers and existing destination adapters. ID renames update
checkout profiles but never open another platform's state store. Native Windows
PowerShell 5.1/7 and native Linux/WSL runtime/visual checks remain named pending
acceptance; see [core updates](../plans/core-updates.md).


Visual config commands share the Python resolver/refresher between Bash and native PowerShell. Windows retains native state/config destinations and does not invoke WSL or tmux; unavailable consumers are reported. Bash/Zsh, Fish, Nushell, PowerShell and Xonsh follow generated literal visual data through their existing generation checks. Native Windows PowerShell 5.1/7 and Linux/WSL desktop acceptance remain separate from Termux fixtures.
