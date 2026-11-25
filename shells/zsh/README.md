# Zsh Configuration

The shared configuration supports the existing Termux workflow with explicit startup stages. Fixtures exercise WSL/Linux detection and path policy. MSYS2 uses the Windows platform and its own runtime identifier. Native WSL/Linux and MSYS2 interactive verification remains pending.

## Startup Order

`zshenv` resolves its source file through symlinks and exports the checkout root. Ordinary nonlogin interactive startup delegates settings, paths and platform detection to the known Dots rc. Login, noninteractive and independent rc files use the early section of the same prepared bundle. It exposes `dotstro`, `is_termux` and `is_wsl`. A login rc applies environment or settings-file overrides made by `.zprofile`.

`zshrc` resolves its checkout and enters the prepared backend. The public `init.zsh` links to this rc. After early profile hooks, the interactive sequence is:

1. `core/environment.zsh`: XDG defaults, shared utilities, environment modules, editor selection, and paths.
2. `core/cache.zsh`, shared functions/options, early `keys.zsh` preferences, FZF settings, and the selected theme.
3. Installed completion providers, followed by `core/completion.zsh` and one `compinit` with its normal ownership checks.
4. The backend's `lib/dots/shell/tools.zsh` activates available runtime managers, directory hooks, history integration and Starship, and registers first-use tool completions. Shared aliases follow.
5. The active Termux or WSL profile defaults, then an independent `~/.zshrc.local`, FZF shell bindings, fzf-tab, widget plugins and final personal keybindings. A home link to the selected profile file is sourced once. The generic `$PROFILE/shells/local.zsh` hook follows this sequence.

User-facing functions and aliases are maintained in the [shared shell resources](../../docs/shared-shells.md). `rl` reapplies preferences and the theme. FZF and each registered plugin are marked ready after successful initialization. Reload keeps working widgets, retries unavailable providers and preserves shared history and the caller's `LOCAL_OPTIONS` setting.

Installed Zinit plugins load in their normal order. When the manager or a configured plugin is missing, the first Tab still uses native completion and queues the missing completion plugins. A native history key can queue the history-search plugin. The first accepted interactive command queues remaining configured plugins, including the Termux vi-mode and clipboard integrations. An installed custom Zinit plugin can still load through a local hook. Only the shipped public plugin choices are eligible for automatic downloads. A detached worker downloads those GitHub repositories into private staging directories and publishes into unoccupied Zinit destinations. Foreground editing continues immediately. The next prompt after the worker finishes activates the available plugins and restores personal binding priority. A shell script, the initial prompt, another keypress or an ordinary reload never starts a duplicate download.

Automatic downloads require `python3` and `timeout` on PATH. Repository downloads also require `git`. The Linux/WSL Deja executable uses `curl`. Zsh skips each download whose prerequisites are missing. If none can run, native editing continues without starting a worker or writing a receipt.

Run `dots-zsh-plugins setup` in an integrated interactive Zsh to prepare missing plugins immediately. `dots-zsh-plugins retry` retries failed attempts and reports individual errors. Per-destination locks and receipts under `${XDG_STATE_HOME:-~/.local/state}/dots/zsh/plugins` coordinate concurrent shells and suppress automatic retries after failure. Git prompts and recursive submodules are disabled. The platform's `timeout` utility bounds each transport to 30 seconds within a 90-second batch deadline, including after an acquiring shell closes. A killed worker leaves a preparing receipt. An explicit retry starts with a fresh staging directory. A hard kill can leave a private `.dots-plugin-*` staging directory beside its target. Existing installations and occupied destinations are preserved for inspection. Bash, Fish, Nushell, Xonsh and native PowerShell use their own integrations.

## Personal keybindings and history search

[`keys.zsh`](keys.zsh) owns personal ZLE settings and bindings. It selects vi editing once per shell, retains `KEYTIMEOUT=1`, and keeps beam/block cursor handling with the vi-mode plugin or additive native ZLE hooks. History storage options remain in `options.zsh`; the Termux local hook owns platform clipboard/open commands and plugin loading.

Up/Down search command history in insert and normal mode; normal-mode `k`/`j` search backward/forward. Both ordinary and application-mode arrow sequences and available terminfo sequences are supported. Searches match a contiguous substring anywhere in the command, ignore case, and return unique results. `HISTORY_SUBSTRING_SEARCH_GLOBBING_FLAGS='i'` and `HISTORY_SUBSTRING_SEARCH_ENSURE_UNIQUE=1` select these preferences; `HISTORY_SUBSTRING_SEARCH_FUZZY=''` and `HISTORY_SUBSTRING_SEARCH_PREFIXED=''` disable fuzzy/prefix-only matching. These switches treat any nonempty value as enabled, including `0`. The highlight timeout remains one second. Empty queries browse history; multiline results retain the plugin's within-command navigation.

Matches use the current Dots selection foreground/background; unsuccessful searches use its error foreground. A builtin-only prompt hook reads refreshed palette arrays after the existing theme hook, with standout/red fallbacks when no palette is loaded. No theme publication or plugin update is needed. Edit the settings and theme helper in `keys.zsh` to change these preferences; later local-hook assignments can override ordinary search settings.

Both Ctrl-H and DEL delete backward in insert mode. When clipboard widgets are installed, normal-mode `Y` retains yank-to-end and insert-mode Ctrl-V pastes from the system clipboard. FZF Ctrl-R retains priority, and Tab remains owned by FZF-tab. Plugin-specific bindings are installed only when their widgets exist; without optional plugins, native editing remains usable.

The file loads before plugins and applies bindings after widget registration. Deduplicated vi-mode callbacks reapply them after initialization, first normal-mode lazy installation, and mode changes. It does not repeatedly reset the vi maps or wrap plugin widgets. Open a fresh Zsh session after the initial migration; subsequent `rl` reloads reapply edits without duplicating hooks. `dots keys zsh` from the integrated shell captures these effective bindings, including Zsh's abbreviated `bindkey -a` normal-mode declarations. The tmux shortcut can request the source pane's live maps while Zsh is at its prompt; unavailable capture is labeled configuration only. See [live Zsh capture](../../docs/keys.md#live-zsh-bindings-from-the-tmux-shortcut) for targeted activation in an existing session.

These preferences are specific to personal Zsh startup on Termux/Linux/WSL; the integration-only `dots init` hook does not load them. Bash and native PowerShell keyboard settings and Windows destinations are unchanged. Native Termux tests are distinct from other-platform fixtures and actual keyboard acceptance.

## Deja suggestions

Deja is the default. On Linux/WSL x86-64 and ARM64, the first accepted interactive command can queue a missing executable after Deja is selected. Open a fresh shell to use it; an unset or empty `DOTS_ZSH_SUGGESTIONS` selects Deja. To use the optional `zsh-autosuggestions` engine instead:

```zsh
DOTS_ZSH_SUGGESTIONS=autosuggestions zsh
```

Exit that shell to return to the previous session. For persistent selection, export `DOTS_ZSH_SUGGESTIONS=autosuggestions` in your existing local configuration hook (before widget plugins load), then open a fresh shell. Remove that export or set it to `deja` to restore the default in a new shell. `rl` deliberately does not switch engines: stacking their widget wrappers is unsafe. Failed installation, an unusable release, unsupported platforms/architectures or invalid selector values warn and fall back to autosuggestions for that shell. Explicit `autosuggestions` and `none` selections never install Deja.

Zinit loads `Giammarco-Ferranti/deja` synchronously with `lucid depth=1 pick'deja.plugin.zsh'`, using the existing load-once wrapper. No `wait` ice is used. Before loading the plugin, Dots reuses an executable already on PATH. Otherwise, on Linux/WSL, the first-use worker retrieves matching upstream release metadata and a size-limited archive using HTTPS and curl. It stages the single regular `deja` executable under the existing `dots-deja-binary` identity, selecting `amd64` or `arm64` explicitly. Zinit activates this cached executable. Its directory is managed by Zinit and added to the current shell's PATH; the executable is checked with `--version` before activation. Subsequent shells reuse the cached release without remote version checks. Do not also source `deja init zsh` elsewhere or load either engine through another plugin list.

Updates are explicit: use `zinit update dots-deja-binary` for the managed executable and `zinit update Giammarco-Ferranti/deja` for the integration, then open a fresh shell. An executable supplied elsewhere on PATH remains your responsibility and takes precedence. Run `dots-zsh-plugins retry` after a failed download. Open a fresh shell if an alternative suggestion engine has already been activated. No system packages, history import or startup-file edits are performed by this integration.

Deja's default Tab binding is disabled so FZF-tab retains completion. To cycle alternatives, set `DEJA_CYCLE_KEY` to a spare key before startup; explicit values, including empty strings, are preserved. Right arrow accepts a suggestion. `DEJA_HIGHLIGHT_STYLE` initially inherits `ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE` (or `fg=8`) unless explicitly set. This is a startup snapshot, not live palette synchronization; restart after a theme change or supply an explicit style.

Deja starts a per-user background daemon and stores plaintext command history, generated integration, and its socket under `~/.local/share/deja`, independent of XDG overrides. It can learn secrets in ordinary commands; review upstream history exclusion guidance. No history import occurs at startup. Upstream's optional `deja import` reads `~/.zsh_history` specifically, not an arbitrary `$HISTFILE`; inspect your history location before choosing to import. Leaving the trial does not erase its database or stop its persistent daemon. Do not use broad process-name kills or delete the database as part of switching engines.

Automatic Linux downloads are disabled on Termux and other platforms. On Termux, use a native source build with Go >=1.25.2, CGO enabled, and Clang; upstream Linux release binaries are not Android builds. The tested source revision and native acceptance are recorded in the [trial plan](../../plans/deja-trial.md). The curl installer is not used: it would edit startup configuration independently of Dots. Other native platforms remain unverified here. The original trial measured slower Deja initialization than autosuggestions; this tradeoff was accepted when promoting it to the default.

## Environment Modules

The explicit compatibility list replaces the recursive repository scan:

```text
androidots/termux.env
ruby/ruby.env
secrets/secrets.env
windots/win.env
```

Readable files are sourced in this order, including existing platform-specific files for compatibility. Missing optional sources are skipped; no submodule is initialized. The list does not inspect or expose private values. Register additional absolute paths in a Zsh array before the loader runs, for example in a local startup wrapper:

```zsh
DOTS_ZSH_EXTRA_ENV=("$HOME/my-shell/environment.zsh")
source "$DOTS/shells/zsh/zshrc"
```

The existing `secrets.sh` and `zsh[local]` hooks remain supported and reapply on reload. Platform adapters centralize new environment-specific behavior; compatibility modules retain their existing contents.

## Paths and Platforms

Zsh path insertion uses literal array membership and preserves existing precedence. Existing directories are retained in place; missing directories are not added. `fixpath` removes duplicate entries without sorting executable precedence. Bash and Zsh source `bin/lib/common.sh` for shared utilities; startup leaves its legacy 256-color arrays unallocated. The explicit utility functions remain available to build `COLOR`/`FG`/`BG` on request. Named theme color arrays come from the theme initializer.

Termux derives site-functions from its prefix. Linux and WSL retain the installed shell's native completion paths. WSL detection accepts its environment markers or a Microsoft kernel release. MSYS/Cygwin detection selects the Windows platform with the detected runtime. These adapters preserve native paths.

For WSL performance, prefer keeping the checkout, plugins, and cache on its Linux filesystem. MSYS2's native behavior still requires verification.

## Generated Data and Reloads

When `pip` is installed, its Zsh completion is generated directly with `pip completion --zsh` after `compinit` on startup and again through `rl` or `rlcs`. This completion is not cached.

Generated `uv`, `uvx`, and Starship completions live beneath `$XDG_CACHE_HOME/dots/zsh/<platform>-<zsh-version>/`. Cache signatures include the resolved executable's path and file metadata and generator arguments. Generation is synchronous on a miss, validated as Zsh syntax, and published through a temporary file and rename. Failed generation is never evaluated. If storage is unavailable, successful validated output can still be used for the current shell.

Metadata-preserving in-place executable edits can require an explicit refresh. `rlcs` deletes these generated completion entries and the configured completion dump, rebuilds completion, and reconnects FZF-tab. `rlc command ...` reloads selected autoloadable completion functions. Existing `ZSH_COMPDUMP` overrides are honored; otherwise the dump uses the platform/version cache directory. No `compinit -C` shortcut disables ownership checks.

Completion dumps are normalized before loading and after generation so autoload declarations treat names such as Termux's `_uu-[` literally. Existing affected dumps are repaired automatically, with stale compiled copies invalidated. If an affected dump cannot be rewritten, completion initializes in memory without loading it. Normal shell globbing remains enabled; only the dump's autoload declarations use [Zsh's `noglob` modifier](https://zsh.sourceforge.io/Doc/Release/Shell-Grammar.html#Precommand-Modifiers).

Vivid's `LS_COLORS` output is cached as data using the selected theme (including the resolved published Dots file), executable, and metadata for [Vivid's documented custom theme/database locations](https://github.com/sharkdp/vivid#customization). Theme changes and changed inputs invalidate it. Catppuccin keeps its existing generated-palette cache. Theme application replaces FZF color options instead of appending duplicates. The completion `list-colors` style evaluates the current `LS_COLORS` on demand, so fzf-tab file colors follow prompt-driven theme switches without reloading completion.

Session-dependent activation remains immediate. Prompt modules, display formatting, and timeout settings are preserved. The Git-host icon uses a shell pattern instead of a separate grep process. The malformed `NVM_DIR` default and `ll` alias are corrected; an existing NVM installation can therefore initialize where the old typo prevented it.

Published Dots themes also supply Fast Syntax Highlighting colors. The adapter runs
after plugin loading and on published generation changes, reuses native-loader data
in the Dots cache, and preserves explicit FSH overlays. It also saves the last good
Dots theme to `$FAST_WORK_DIR/current_theme.zsh` for native plugin startup; both
`fast-theme --show` lines report `dots`. Non-Dots selections are backed up before
replacement, and stale compiled startup code is invalidated. Reload once after updating
adapter code. See [Vivid and FSH](../../docs/themes.md#vivid-and-fast-syntax-highlighting)
for palette mappings and fallback behavior.

Dots route words on the command line use FSH's native `subcommand` theme role.
The callback also loads without published theme data or with `DOTS_INIT_THEME=0`;
it preserves existing user chroma entries. Completion menus have separate
[appearance preferences](../../docs/shell-environment.md#completion-appearance).

Missing generated FSH data and loader/cache failures report the affected path
and a repair step once per generation/failure in a shell. Use `dots init --setup`
for missing installation links, or `dots theme refresh` for missing generated
outputs. Open a new shell after repair. Startup never publishes themes itself;
saved colors and explicit session-only selections retain their fallback behavior.

## Verification

Run from the repository root:

```bash
python3 -B tools/test_zsh.py
python3 -B tools/zsh_fixture.py --samples 10
python3 -B tools/zsh_interactive.py --samples 5
python3 -B tools/verify_docs.py
git diff --check
```

The unit suite owns disposable roots and needs installed Zsh plus basic host tools. The timing and PTY tools explicitly select autosuggestions to avoid requiring a Deja binary, and require the existing public Zinit installation and five configured plugins; they copy them without Git history. They copy only selected public configuration and use synthetic private/platform modules. Their Git wrapper refuses remote operations. They do not install dependencies or source the developer's startup files.

Timing fixtures use fresh HOME, configuration, state, cache, history, and repository roots. Termux interpreter support is retained. The non-PTY startup test can emit ZLE warnings from installed integrations; real interaction is checked separately using a controlling pseudo-terminal. Use `tools/zsh_compare.py <baseline-source-directory>` for a public-interface comparison. The PTY runner accepts `--baseline` to report historical reload differences without failing its equality check. Fixtures and logs remain in the reported temporary directory for inspection. Logs contain fixture state only.

For native default-engine acceptance, supply a previously built binary and the reviewed upstream plugin file (no downloads):

```bash
python3 -B tools/test_deja.py --binary /path/to/deja --plugin /path/to/deja.plugin.zsh
```

This opt-in runner copies both into the public fixture, leaves the selector unset to exercise default Deja activation, uses synthetic history, owns and stops its daemon, exercises real PTY acceptance/vi/Tab/reload behavior, and compares warm startup for both engines. Retained logs contain fixture data only. The ordinary Zsh suite also checks selection/fallback/override behavior without requiring Deja.

`ZSH_DEBUGRC=1` retains function profiling. Use the disposable fixture for profiling, especially when private/local modules could have side effects. Measurements and limitations belong in the [focused plan](../../plans/zsh-startup.md).

## Shared theme selection

The [theme engine](../../docs/themes.md#shell-and-neovim-behavior) supplies current-theme arrays such as `${blue[hex]}` and `${hint[esc]}`, preserving fixed Catppuccin flavor arrays for compatibility. `dots theme set ID` publishes a shared selection; the next
prompt loads its initialization once. The unchanged prompt path uses builtins only
and preserves command status. `set_theme ID` remains session-only; `change_theme ID`
persists through the shared publisher.

## Unified initialization

Bash and Zsh can use `eval "$(dots init)"`; the repository wrapper bootstraps through the executable under `DOTS`. See the [shared hook contract](../../docs/shell-init.md). Noninteractive `zshenv` remains independent of the CLI.

### Unified theme startup

Startup sources `lib/dots/shell/init.zsh`, which owns the theme adapter and loads the published Dots
generation. `theme` now runs the same CLI as `dots theme`; it is not the startup
loader. Generated family commands and completions become available after
`dots theme refresh` (or `--commands-only`). `catppuccin mocha` previews; append
`set` to activate. The prompt hook reloads both palette data and generated command
registrations when their generations change. Legacy Catppuccin startup snippets
are replaced by Dots integrations.

Dots settings and variables are documented in [the environment contract](../../docs/shell-environment.md).

Interactive startup puts the existing `${XDG_DATA_HOME:-$HOME/.local/share}/zsh/site-functions` directory first in `fpath` after plugin setup, before compinit, and exports `FPATH`. Termux also registers `$DOTS/androidots/shells/zsh/completions` when Androidots is present. Repository, plugin and package fallbacks remain available; the repository Zsh completion directory is no longer added to executable `PATH`. Start a new shell or reload configuration after changes; `rlcs` re-registers the local directory and rebuilds discovery. See [user-local completion paths](../../docs/shell-init.md#user-local-completion-directories).

Platform modules now load only for their active profile. See [profiles](../../docs/profiles.md).

## Keybinding reference

`dots keys zsh` captures the current shell's maps through the Dots integration adapter. Use `--mode viins` or `--mode vicmd` to focus the reference. No keymap scans occur during startup. The Termux local vi-mode hook normalizes both Backspace encodings after initialization and transitions. See [keybindings](../../docs/keys.md).

## Completion appearance

Dots colors command, option, value and Git reference labels independently from
descriptions and headings, while preserving LS_COLORS for files and literal
insertion. Configure `apps.completion.enabled` and `colors.apps.completion.*` in
the existing Config browser. After loading the updated code once in a new shell
or with `rl`, preference edits refresh at the next prompt. The Dots adapter
supports the installed FZF-tab capture interface and native Zsh fallback without
editing plugin files. See [completion appearance](../../docs/shell-environment.md#completion-appearance)
and [isolated verification](../../docs/testing.md#shell-completion-colors).
