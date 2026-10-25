# Native PowerShell

**Implementation available; native Windows runtime and desktop acceptance pending.**

`bin/dots.ps1` is the native entry point for Windows PowerShell 5.1 and PowerShell 7. It invokes Python directly; it does not route commands through Bash, Git Bash, MSYS or WSL. Basic help and shell startup do not require Python. Use Python 3.11+ for the complete CLI, including theme rendering and Anodize; the file-only controllers retain their Python 3.9 minimum. Git, FZF, Gum, Chafa and application executables are checked only by operations that need them. Anodize also requires the existing native `anodize-engine.exe` build or an explicit `ANODIZE_ENGINE` path.

```powershell
.\bin\dots.ps1 help files
.\bin\dots.ps1 files install --dry-run
.\bin\dots.ps1 files install --verbose
.\bin\dots.ps1 files add --pick
.\bin\dots.ps1 git status --json
.\bin\dots.ps1 theme switcher --verbose
.\bin\dots.ps1 theme refresh --verbose
.\bin\dots.ps1 completion powershell
```

Setup installs the current host's `$PROFILE.CurrentUserCurrentHost`. Run setup from each desired PowerShell host to install that host's profile; do not guess its Documents path. Redirected Documents folders and engine-specific profiles are reasons to use the host's own path. See [Microsoft's profile documentation](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_profiles).

The personal profile now uses [shared Starship startup](shell-init.md#powershell-profile). Native PowerShell 7 and Windows PowerShell 5.1 profile checks are recorded in the [profile repair plan](../plans/powershell-profile.md); this bounded evidence does not establish full native CLI or desktop acceptance. Windows app destinations and installation targets are unchanged.

## Commands and interaction

The native dispatcher reads the same static first-party headers as Bash. Built-in metadata lives in `lib/dots/metadata/`. It forwards file commands to the existing catalog, mapping, browser, installer and transaction controllers. Git uses the native Python Git controller. Themes use a literal palette reader, renderer and guarded file transactions; Anodize uses its existing engine and a native publication bridge. Bash retains its established theme/Git frontends while native behavior is validated.

PowerShell arguments cross the Python boundary as a base64-encoded JSON array. Empty strings, quotes, Unicode and shell metacharacters remain literal; stdin remains available for confirmations. This avoids depending on the different native argument rules in [PowerShell versions](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing). Completion inspects literal AST values without evaluating expressions or executing extensions. Palette `init` and `--array` emit PowerShell syntax on Windows; scalar color values keep the same formats. Native `.ps1` and `.exe` external commands need their own native implementation; an arbitrary external Bash script is not converted.

The shared presentation and operation-event helpers own file icons, type/MIME colors, verbose links/backups and progress. JSON, scalar values, generated shell code, dry-run and redirected output retain their data contracts. `DOTS_COLOR`, `DOTS_ICONS`, `DOTS_PROGRESS` and `NO_COLOR` apply. Console encoding changes made by the adapter are restored after the command.

File pickers keep Enter to review, Esc/Ctrl-C to cancel, Tab/Shift-Tab to mark, Ctrl-A to select matches, Ctrl-D to clear, Alt-P to toggle previews, Alt-J/K to scroll and Alt-C to change preview views. FZF previews pass numeric snapshot tokens, never interpolated filenames. Native rich previews require an FZF build with `--with-shell` and an available native PowerShell. Gum or numbered prompts remain usable fallbacks. Theme selection has a separate Apply/Back/Cancel step. Native terminal rendering, key handling and cancellation still need the acceptance below.

Git info, submodule tree/status and scoped publication now have matching native
routes and static completion metadata. Shared inspection/selection uses native
Git without Bash. `--all-submodules` selects child trees; `--all` selects unstaged
files. Windows app destinations are unchanged. Native Windows PowerShell 5.1/7
runtime, confirmation/interruption, completion and 40/80/120-column light/dark
visual acceptance remain pending; portable controller tests are not that evidence.

## Windows app destinations

The catalog token `${APP_CONFIG:app}` resolves app-specific directories in `lib/dots/files/app_paths.py`. `DOTS_APP_<APP>_CONFIG` selects an absolute directory, replacing hyphens with underscores in the variable name. App-native overrides are also honored where listed in that module. Missing or ambiguous destinations remain unmapped. Overrides select locations; they do not override link or backup safety.

| App | Native default / selection |
| --- | --- |
| lsd | `~/.config/lsd` (preferred Windows location) |
| bat | `%APPDATA%/bat`; `BAT_CONFIG_DIR` override |
| Television | `%LOCALAPPDATA%/television/config`; `TELEVISION_CONFIG` or absolute `XDG_CONFIG_HOME/television` override |
| Leaf | `%APPDATA%/leaf`; unmapped without APPDATA unless explicitly overridden |
| eza | `%APPDATA%/eza`; `EZA_CONFIG_DIR` override |
| Yazi | `%APPDATA%/yazi/config`; `YAZI_CONFIG_HOME` override |
| Nushell | `%APPDATA%/nushell`, or `$XDG_CONFIG_HOME/nushell` |
| mpv | `%APPDATA%/mpv`; `MPV_HOME` override |
| VS Code | `%APPDATA%/Code/User/settings.json` only |
| Alacritty | `%APPDATA%/alacritty` |
| Clink | `%LOCALAPPDATA%/clink`; `CLINK_PROFILE` override |
| Fastfetch / WezTerm | `~/.config/fastfetch` / `~/.config/wezterm`, honoring XDG |
| GlazeWM | `~/.glzr/glazewm` |
| Komorebi | `~/komorebi.json` and `~/komorebi.bar.json`; `KOMOREBI_CONFIG_HOME` override |
| whkd | `~/.config/whkdrc`; `WHKD_CONFIG_HOME` override |
| Tacky Borders / YASB | `~/.config/tacky-borders` / `~/.config/yasb` |
| Windows Terminal / WinGet | Exactly one existing recognized packaged/unpackaged settings directory; otherwise an explicit override |
| Starship / Blastoff | `~/.config/starship.toml` / `~/.config/blastoff` |
| Windows WSL host config | `~/.wslconfig`; guest `/etc/wsl.conf` stays unmapped |
| File Pilot | Explicit `DOTS_APP_FILEPILOT_CONFIG` only |

The app rules follow upstream [lsd](https://github.com/lsd-rs/lsd#config-file-locations), [Clink](https://github.com/chrisant996/clink/blob/master/clink/app/src/utils/app_context.cpp), [bat](https://github.com/sharkdp/bat#configuration-file), [Yazi](https://yazi-rs.github.io/docs/configuration/overview/), [Nushell](https://www.nushell.sh/book/configuration.html), [mpv](https://github.com/mpv-player/mpv/blob/master/DOCS/man/mpv.rst), [WezTerm](https://wezterm.org/config/files.html), [GlazeWM](https://github.com/glzr-io/glazewm), [Komorebi](https://komorebi.lgug2z.com/common-workflows/configuration-directory/), [whkd](https://github.com/LGUG2Z/whkd), [Tacky Borders](https://github.com/luke-you/tacky-borders), [YASB](https://github.com/amnweb/yasb/wiki/Configuration), [Windows Terminal](https://learn.microsoft.com/en-us/windows/terminal/install) and [WinGet](https://github.com/microsoft/winget-cli/blob/master/doc/Settings.md) documentation. Portable distributions and app command-line flags can override these defaults; use the explicit directory override to match the installation in use.

Windots' bat entry remains unmapped because its source is absent; the root bat resource supplies the configuration. The Alacritty mapping is defined but skipped while its optional source is absent. Clink links only its settings, known Lua files and theme directory, preserving profile history and any co-located executables. Windhawk exports are not a directly consumed application config file. Unix-only app resources retain their platform restrictions. Inventory does not imply every recorded file should be installed. The Windots catalogs are a separate nested repository and must travel with the parent change.

## State, publication and recovery

Existing Windows state remains `%LOCALAPPDATA%/dots`, or `$XDG_STATE_HOME/dots` when set. There is no automatic migration to `dots/state`. Dots settings use `%APPDATA%/dots` unless XDG is explicit. Application paths are resolved independently. Native Windows and WSL must use separate checkouts/state; no Windows/WSL path translation or cross-boundary links occur.

Links remain the default. Dots does not elevate, enable Developer Mode, silently copy, traverse unknown reparse points, or replace unrelated theme pointers. Missing link privileges fail during approved preparation before live replacement. File replacement, connectors and active theme pointers use retained journals; recovery and undo use `dots files history`, `recover` and `undo`. Modified generated commands and post-apply drift require review. Native Windows flushes files/journals, without claiming POSIX directory-fsync or power-loss guarantees.

Setup prepares inactive theme payloads and publishes them in its installation transaction. It does not run reload hooks or change wallpaper. Explicit theme publication uses native command manifests and the same transaction store. It refuses unfinished legacy Bash publication journals rather than guessing how to recover a different installation. Native wallpaper uses the Windows desktop API; lock-screen changes remain Android-only. GTK/Qt hooks and tmux operations remain explicitly unavailable on native Windows. Local native `.ps1` theme hooks and the bundled Starship adapter use the plugin controls; downloaded themes remain inert data.

## Acceptance and remaining limits

The [parity plan](../plans/powershell-parity.md) records implementation and verification separately. Native Windows runtime evidence is required before upgrading support claims. In a disposable Windows account/checkout, run `python -B tools/test_native_cli.py` under both engines, and `python -B tools/test_native_git.py`. Set `DOTS_TEST_POWERSHELL=powershell` or `pwsh` to require that engine instead of allowing a skip.

Owner acceptance must exercise both real profiles, Unicode and quoted paths, denied link privileges, repeat setup/uninstall, occupied targets and retained backups, interrupted apply/recover, theme switching and undo, FZF previews/keybinds, Ctrl-C/Ctrl-Break, and 40/80/120-column light/dark terminal views. Check actual app config locations and wallpaper separately from fixtures. Linux and WSL likewise need native runtime/terminal evidence; Termux fixtures do not establish those platforms.

Native Git and theme panels share semantic/rendering primitives but have not received visual equivalence acceptance. The native publisher builds an isolated bat cache when bat is available and the PowerShell theme hook exposes it. Native Delta/bat and eza consumer acceptance is pending. The eza connector and renderer use the shared destination resolver and native transaction engine; Termux controller fixtures do not establish Windows PowerShell 5.1/7 link or rendering acceptance. Known-folder resolution relies on the host profile and app environment/default paths, not a general Windows Known Folder API. Do not describe those outstanding checks as completed parity.

Anodize user saves use the existing platform configuration adapter: XDG when
explicit, otherwise `~/.config/dots/themes` on POSIX and `%APPDATA%/dots/themes`
on Windows. `--builtin` and `promote` target the selected native checkout. Both
frontends share the authoring/picker controller and journal; Windows application
connector destinations are unchanged. Native PowerShell 5.1/7 FZF keyboard,
preview and interruption acceptance remains pending where engines are unavailable.

## Standalone weather

`bin/wttr.ps1` uses the literal native argument bridge and shared Python 3.11+ weather controller; Bash is not required. It supports the same views/flags/progress/data, case-sensitive short aliases and theme-gradient help, stock request syntax and generated PowerShell completion as the Unix entry. Temperature/icon attributes, variable temperature bands and widget style directives use the shared renderer, and completion tooltips use case-sensitive stock metadata. Stock requests execute native `curl.exe` directly, bypassing the PowerShell `curl` alias; JSON-backed views do not require curl. Configuration maps to APPDATA/wttr (XDG override supported). Manual/default locations are supported; Android acquisition and tmux have no native Windows equivalent here. Native Windows PowerShell 5.1/7 weather/completion terminal validation remains pending; shared controller/bridge fixtures do not establish it. See [wttr](wttr.md).

Named `git submodule NAME ...` navigation and `git submodules info` use the same Python parser, inspection and static completion metadata as Bash. Publication delegates to the native Git controller; no Bash is required on Windows. Native PowerShell terminal acceptance for these additions remains pending.

Leaf publishes UI and shared bat syntax through the native Python transaction engine and is included in native setup. The separate [Leaf build](leaf-build.md) requires platform-native Rust compilation. Native Windows publication, undo, symlink privilege refusal and dark/light rendering acceptance remain pending.

`theme files` now uses the shared read-only inspector for list/info/show/path/check/browse and contextual file/app completion. It honors native state/config roots and existing publisher destination adapters; no Bash execution is needed for inspection or the native selector. Current source resolution is distinct from historical provenance. Windows PowerShell 5.1/7 runtime, native link/destination behavior and browser terminal acceptance remain pending where native engines are unavailable; shared controller tests do not establish those checks.

Theme-file directory previews, optional bat highlighting, spaced listings and `check --consumers` share the same Python implementation. Native bat rendering uses literal argv and bounded pipes, with no Bash or pager dependency. The native app path adapters and inherited environment scope remain explicit; actual Windows renderer/PowerShell terminal acceptance is pending.

## Platform profiles

The native controller exposes `profile`, `profiles`, expanded `env`, and
`init --bootstrap powershell` through the same static metadata as Bash.
PowerShell prepares a native environment adapter with Python on a cold load;
warm loads validate and apply it natively. No Bash invocation or Windows/WSL path
translation is introduced. Actual Windows PowerShell 5.1/7 acceptance is pending.
See [profiles](profiles.md).

The profile inspection and debug command families use the shared Python
controllers and metadata. Native startup emits opt-in source/phase events;
normal-profile tracing requires `--live`, while `--isolated` uses owned profile
paths. Job Object ownership and PowerShell 5.1/7 terminal acceptance are pending
on Windows. See [debugging](debug.md).

Wiki routes and associated Git operations use the shared controllers, including page completion, `--json`, `--no-wiki` and selected-content publication checks. Browser/editor launching uses native processes without Bash. Native Windows PowerShell 5.1/7 terminal and acquisition acceptance remain pending where that runtime is unavailable. See [wiki](wiki.md).


Detailed debug options share the common command metadata. Native changes use in-memory comparisons; registered script breakpoints supply line observations where available. PATH recording uses explicitly dot-sourced start/stop code and native breakpoint callbacks. Existing breakpoints prevent conflicting activation. No Bash dependency is introduced. Native Windows PowerShell 5.1/7 debugger, recording cleanup and terminal checks remain pending.

## Keybinding inspection

The native controller supports all `dots keys` options and the category/app menus without Bash. Redirected, print and JSON modes retain their data/report behavior. Interactive integration adds an on-demand PSReadLine adapter that exports bound-handler names/descriptions as JSON. Existing user `dots` functions remain untouched. FZF runs in the ordinary terminal on native Windows; tmux is an explicit optional platform capability. Actual PowerShell 5.1/7 encoding, input and terminal acceptance remains pending when those engines are unavailable.
