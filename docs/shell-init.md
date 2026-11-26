# Shell initialization

**Implemented.** `dots init [bash|zsh|fish|powershell|nu|xonsh]` prints native shell code. It initializes only Dots settings, paths, colors, completions and refresh hooks; it does not install files or packages. The separate explicit `dots init --setup` mode delegates to [checkout installation](installation.md); ordinary hook generation/evaluation remains unchanged. The live Bash dispatcher requires Bash 4.4 or newer. Native PowerShell initialization has a separate adapter.

Compiled Bash/Zsh settings include CLI row formatting. Adding, editing or removing a contributing shared or profile preference file invalidates the prepared settings. This includes unified `config.json`, existing split-style configurations and profile manifests. An unchanged generation loads without a Python configuration query. Ordinary Dots commands read current preferences independently. See [shared row alignment](profiles.md#shared-row-alignment).

The repository Zsh fzf-tab integration supports `COMMAND nf<Tab>` for an exact,
unquoted argument. Search the cached Nerd Fonts glyphs, mark choices with Tab,
and press Enter to replace that argument in the editor. Escape keeps the original
line. See [the icon picker](fonts.md#browser-and-icons).

## Using the hook

For Bash and Zsh, put this in the interactive startup file once `dots` is on PATH:

```sh
eval "$(dots init)"
```

The generated default hook selects Bash or Zsh in the receiving shell. It does not use `$SHELL`, which can name a different login shell. Explicit `dots init bash` and `dots init zsh` forms are also available. Installed startup files can recover a missing checkout. The direct repository startup files resolve their own symlinks and source the adjacent native loader directly; `dots` need not be on PATH. Link or source the startup file from the checkout you want to use. Inherited `DOTS` values do not select another checkout during native startup.

Fish uses native code:

```fish
dots init fish | source
```

PowerShell uses its native adapter, including on Windows without Bash:

```powershell
& "$env:DOTS/bin/dots.ps1" init powershell | Out-String | Invoke-Expression
```

Set `$env:DOTS` first when invoking that explicit path. The repository profile instead discovers its checkout from the resolved profile file, including symlinked parent directories and Windows junctions. After the repository's `bin` is on PATH, `dots.ps1 init powershell` is the explicit native spelling; `dots init powershell` also works when command lookup selects that adapter or the Bash executable. The native adapter also dispatches the first-party command families described in [native PowerShell](powershell.md). Completion uses static metadata and native readers without Bash; Windows runtime acceptance remains separate from implementation.

Xonsh executes the code in its current context:

```xonsh
execx($(dots init xonsh), 'exec', __xonsh__.ctx)
```

The repository Nushell `config.nu` resolves its own file path at parse time and loads the adjacent `init.nu`. A linked config does not require a generated hook, and an existing `dots-init.nu` will not override it. For a separate custom Nushell configuration, generate an explicit hook from a shell where `dots` is already reachable:

```nu
mkdir $nu.default-config-dir
dots init nu | save --force ($nu.default-config-dir | path join 'dots-init.nu')
```

Run generation successfully before starting a shell that sources the result. For that custom configuration, explicitly add:

```nu
source ($nu.default-config-dir | path join 'dots-init.nu')
```

The generated file pins the checkout's path. Regenerate it after moving that checkout. Ordinary edits to the referenced configuration are picked up without regenerating it. The generated file is machine-local and must not be committed. See [Nushell's configuration rules](https://www.nushell.sh/book/configuration) for parse-time source paths.

## User-local manuals

On Termux, Linux and WSL, Dots-managed Bash, Zsh, Fish, Nushell and Xonsh include `~/.local/share/man` in `MANPATH` when that directory exists. This makes installed plugin manuals available through commands such as `man git-it`. Startup preserves existing search entries and their order. An initially empty or unset `MANPATH` retains the system manual directories through the trailing colon.

## Linked startup files and relocation

Keep the complete checkout layout, including `shells/<shell>`, `lib/dots/shell`, `bin`, and the existing shared modules. The checkout may have any name and live outside the home directory. Link the shell's normal startup file to its repository entry: Bash `.bashrc`, Zsh `zshenv`/`zshrc`, Fish `config.fish`, Nushell `config.nu`, Xonsh `.xonshrc`, or PowerShell `Microsoft.PowerShell_profile.ps1`. Linking the containing configuration directory is also supported. Existing `ZDOTDIR` and shell-specific configuration-directory settings retain their normal shell meaning.

Zsh resolves its source filename through the literal source trace, preserving Unicode checkout paths even in the C locale. This keeps the checkout path used by startup and editor highlighting intact.

A login or noninteractive Zsh reads settings, paths and platform helpers before its rc. On a fresh cache, a script prepares only that early environment. The first interactive rc upgrades the same cache with its completion and interactive modules. A cold interactive login prepares both stages together. A separate personal rc receives the early environment. A nonlogin interactive shell with the Dots rc reads the generation at the rc stage. Login files can still change `DOTS_CONFIG_FILE`, environment overrides and PATH before the full rc runs.

In a Termux fixture with an installed rc, the median warm noninteractive startup was 238 ms, down from 2,063 ms. A noninteractive login took 231 ms, down from 2,256 ms. Each figure uses seven alternating before/after samples. The first script with an empty cache took 2,772 ms versus 2,330 ms over five pairs. That first run validates and publishes the reusable projection. These measurements used isolated homes on a host with other verification work running.

Startup resolves absolute and relative links, chained links, and symlinked parent directories before deriving paths. Relative link targets are relative to the link's directory. The caller's working directory is preserved. Bash requires `readlink` only for file symlinks; GNU `readlink -f` is not required. The other adapters use native path facilities. Missing checkout files and resolution failures report errors without falling back to another checkout. If a broken or cyclic rc link prevents the shell from reading the file at all, the shell handles that failure before Dots code runs.

After moving the checkout, update links that still name its old location. No config-file edits are needed. Explicit generated hooks contain a fixed loader path and must be regenerated if that path changes. Copying the underlying checkout loader directly loses its source location. Use the installer’s standalone rc, a linked checkout loader, or a generated bootstrap instead. The shared profile, `shells/profile` (linked as `~/.profile`), consumes `DOTS` when available and does not independently discover a checkout.

## Personal Zsh keyboard setup

Personal startup loads `shells/zsh/keys.zsh` before plugins, then applies widget-dependent mappings after they load. Its vi-mode lifecycle callbacks preserve bindings across delayed initialization and mode changes. History-search highlights follow the published palette through in-memory prompt refresh. See [personal keybindings](../shells/zsh/README.md#personal-keybindings-and-history-search) for settings, keys and reload behavior. This is outside the integration-only `dots init` hook and changes neither Bash nor native PowerShell editing.

The integration-only key capture adapter also supports [tmux-to-Zsh requests](keys.md#live-zsh-bindings-from-the-tmux-shortcut).
Inside tmux it registers deduplicated prompt/command/exit hooks for a private
socket, without changing editing maps or scanning them at startup or prompts.
Existing shells can source `lib/dots/shell/keys.bash` directly to install capture
without resetting personal bindings. Missing optional capabilities leave ordinary
shell integration usable.

## PowerShell profile

When theme integration is enabled, a profile-loaded PowerShell script also
selects the published bat cache if both binary assets are present. Startup
reads the generation marker and checks those assets locally. Cache compilation
runs during theme publication.

Concurrent cold starts serialize the two writes that publish the generated
environment script and its digest. Windows retries short-lived file sharing
conflicts. A shell reading a valid warm cache takes no writer lock.

The personal PowerShell entry is `shells/powershell/profile.ps1`; `Microsoft.PowerShell_profile.ps1` remains a compatibility entry for existing installer links. Both discover the linked checkout. The installer copies a standalone rc to each supported engine’s `$PROFILE.CurrentUserAllHosts`. A manual installation can link that path to the shared entry. Dots settings, published colors and completion load once; only interactive sessions load personal helpers. Re-sourcing preserves the prompt chain and avoids duplicate personal setup.

Interactive Core and Desktop sessions preserve a profile-supplied prompt. With the default prompt, they initialize Starship using the existing `STARSHIP_CONFIG` or Starship default. Missing or failed Starship initialization leaves a plain directory prompt. After Starship and Dots refresh setup, startup sources `shell-integration_v7.ps1` beside that engine's `$PROFILE.CurrentUserAllHosts` when present. Existing host-specific integration hooks remain safe because the vendor wrapper is idempotent; the vendor files are not rewritten. In console sessions, press **Tab** or **Alt+F** in Vi insert mode to complete the current input. PowerShell supplies the candidates. A single match completes immediately. With multiple matches, type to narrow the fzf list, press Enter to insert a match, or press Escape to keep editing the original line. PowerShell 7 loads PSFzf on first use. Windows PowerShell 5.1 sends its completion list directly to fzf. Both engines fall back to native Tab completion when fzf is missing. PowerShell 7 also uses native completion if PSFzf cannot load. Redirected input skips line-editor setup. The `ls` helper uses eza without Git-status scans when available, otherwise `Get-ChildItem`. Editor selection is deferred until `edit`/`e`/`ep` is used and respects an existing `EDITOR`; otherwise it prefers nvim, code, vim, vi, then notepad. `ep` edits the repository profile source.

PowerShell keeps optional runtime managers, history tools and editor bindings under explicit profile control. Dot-source the loader from the current session or your profile’s `shells/local.ps1`.

```powershell
. "$env:PWSH/optional.ps1" starship
. "$env:PWSH/optional.ps1" completions
. "$env:PWSH/optional.ps1" mise
```

Available feature names are `starship`, `blastoff`, `icons`, `catppuccin`, `pscompletions`, `fzf`, `completions`, `zoxide`, `mise`, `vfox`, `chocolatey`, `command-not-found`, `terminal`, `coreutils`, `atuin`, `direnv` and `tv`. The native direnv hook needs PowerShell 7.2 or newer. Each successful opt-in runs once per session; failed loads remain retryable. Choose the runtime manager you actually use. The loader uses installed tools only, checks generated-code exit status, and restores Dots refresh hooks after Starship activation. The coreutils vendor block is preserved in a separate opt-in file. Default startup runs Starship initialization, its continuation prompt, and the configured terminal integration; unrelated completion generators, module inventory, runtime managers and theme publication stay off. Starship prompt cost depends on the active configuration. Blastoff defaults `BLASTOFF_HOME` to the resolved checkout's `config/blastoff`, preserving an explicit override. Blastoff uses the bundled Dots launcher on both Desktop 5.1 and Core 7; the optional `blastoff` loader registers a forwarding function without importing a separately installed module. WinGet CommandNotFound requires Core 7.4+ and is not eagerly imported by the profile.

Personal helpers remain explicit operations: `touch` creates or updates timestamps without truncating contents; `New-Backup` preserves literal paths, supports `-WhatIf`, uses unique destinations and defaults to moving the source (`-Copy` retains it). Yazi's `y`/`d` helper always removes its temporary cwd file. These personal helpers are separate from managed installation and its journals.

## Environment and execution

PowerShell prompt and completion generators select the first executable in PATH order. Multiple installations of the same tool do not get combined into a command name.

Personal startup also retires recognized old Dots `STARSHIP_CONFIG` values; it
leaves custom overrides intact. Starship uses its default home-relative config
link. See [Starship configuration](shell-environment.md#starship-configuration).

Each native loader establishes the same checkout-derived environment:

| Variable | Derived value |
| --- | --- |
| `DOTS` | Physical checkout containing the resolved native startup file or loader |
| `DOTBIN` | `DOTS/bin` |
| `DOTSCRIPTS` | `DOTS/scripts` |
| `DOTFILES` | `DOTS/config` |
| `DOTCONFIG` | `DOTFILES` |
| `DOTSHHHH` | `DOTS/secrets` |
| `SHELLS` | `DOTS/shells` |
| `ZSH` | `SHELLS/zsh` |
| `PWSH` | `SHELLS/powershell` |

These values replace inherited values on every initialization, including evaluation of a generated hook. Set Dots customization through config.env or explicit environment overrides before initialization. Bash retains its built-in `BASH` executable variable; its configuration directory is `SHELLS/bash`. Existing directories from `DOTBIN` and `DOTSCRIPTS` are prepended in that sequence unless already present; existing PATH entries retain their order. Native shells retain their own PATH representations. No Windows/WSL translation occurs.

Generation emits loader references only. It never sources environment files, reads private modules, captures the whole environment, scans extensions, installs plugins, publishes themes, or writes caches. Invalid arguments exit 2; unavailable loaders exit 1; both leave stdout empty. Help is human output; initialization is undecorated code even under forced color/icons. Diagnostics use stderr. As with other eval hooks, `eval "$(...)"` can obscure the generator's exit status; capture and check output first when scripting error-sensitive setup.

Evaluating the hook loads the library-owned Dots environment. It does not load
personal aliases, plugins, prompts or third-party tools. Repository startup files
separately retain that configuration under `shells/`. Settings belong in the
data-only user `config.env`; see [Dots shell environment](shell-environment.md)
for options, precedence, native variables and diagnostics.

Repeated integration evaluation reapplies Dots settings without duplicate Dots PATH entries or refresh hooks. Personal shell loaders retain their separate tool/plugin guards. Fish snippets use shell-local guards shared by native `conf.d` startup and manual initialization. Nushell FZF bindings replace their own named entries and its completer guard is scoped to the current process. Generated and third-party Fish snippet bodies retain their separate ownership. PowerShell's generated integration blocks are preserved and activated once per session.

Explicit noninteractive initialization loads only Dots settings and common paths. Zsh's `zshenv` also derives and exports the checkout paths and performs native platform detection without external commands. Native startup wrappers load their adjacent loaders without starting the CLI. Login-file behavior and existing local hooks remain in place. Repository source edits do not create or replace home-directory links.

Interactive Bash/Zsh startup also loads the published Gum environment from `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh` when it is a readable regular file. Missing artifacts are optional. The file is trusted shell configuration, including personal overrides; noninteractive initialization and hook generation do not execute it. Both Bash and Zsh reload Gum colors on published-generation changes and configuration reloads. See [theme environment loading](themes.md).

## Verification

Run `python3 -B tools/test_shell_init.py` for isolated native contracts. It owns home, config, data, state, cache, repository, and terminal fixtures; private modules are synthetic. Unavailable shells are reported as skips. The Xonsh interactive test uses readline with a test-owned PTY rather than depending on optional prompt-toolkit. Run `python3 -B tools/test_powershell_init.py` on a machine with `pwsh` for portable native PowerShell parsing, generation, environment and error checks. This separate runner does not require Bash, POSIX PTYs, symlink privileges or a live profile. It is not native Windows evidence when run on another platform.

Run the Bash dispatcher and Zsh suites for shared behavior. Startup measurements and remaining platform/regression limits are recorded in the [initialization plan](../plans/shell-init.md).

## Termux tmux startup

After full Dots Bash/Zsh initialization has finished its environment cleanup and startup tracing, `shells/shared/termux-tmux.sh` invokes `profiles/termux/bin/termux-bar --auto` once per outer shell. The hook requires the Termux platform, inherited `TERMUX_APP__PID`, terminal stdin/stdout, and no tmux or SSH context. The launcher verifies that its calling shell is the terminal session leader directly beneath the Termux app process; child shells do not attach. Scripts, redirected shells, Fish and other platforms are unaffected. Reloading configuration after detaching does not reattach. The shared loader invokes the hook outside generated bundles, including the minimal fallback after preparation fails; integration-only `dots init` never attaches.

Each tab starts with immutable identity `<root-pid>-<start-ticks>` and initial name `termux-ID` in the caller’s directory. A fresh `termux-sessions --get pid --pid ...` query identifies the tab; procfs start time prevents PID reuse. The launcher registers the origin in managed-workspace metadata and resolves it on reattachment even when the current name has changed. Existing windows/directories remain intact. Unmarked name collisions are refused; there is no automatic cleanup or persistent registry.

The launcher uses the ordinary tmux server. `lib/dots/tmux_workspaces.py` observes all live pane directories: no project gives `termux-ID`, one gives `projectname-ID`, and several distinct roots give `multi-ID`. Git repositories/worktrees anywhere and explicitly configured non-Git directories qualify; outside-project panes add nothing. The ID survives every transition. Prefix C creates a fresh ID in the invoking pane’s directory; popup New creates one in the selected project/session directory. Both switch only the originating client. Manual renaming disables automatic naming. The bar displays only the project/multi label, leaving default names hidden; the popup retains full names. Termux tab numbers are above, independent tmux session numbers below.

`shells/shared/tmux-workspaces.sh` registers an idempotent Bash prompt/Zsh precmd hook, preserving the previous command status. It queues a bounded background reconciliation only when PWD or pane identity changes; unchanged prompts do no external work. Workers stay out of the caller’s job table and re-observe the current directory under the server lock, so rapid changes converge without holding up the prompt. Lifecycle hooks cover additions, closures and manual names. Routine reconciliation targets the affected workspace and sessions sharing its windows, with a three-second operation deadline after server discovery; explicit legacy adoption has a separate 15-second deadline; each Git read is limited to one second and tmux reads to the remaining budget. Failures preserve the previous state and leave the shell usable. New Bash/Zsh panes load this automatically. For a shell already running before installation, source `"$DOTS/shells/shared/tmux-workspaces.sh"` once. No commands are injected into existing panes. Fish and the explicit `t` helper keep their existing behavior.

Detaching resumes the outer shell; its bar disappears until reattachment. Run `~/dots/profiles/termux/bin/termux-bar` (or `termux-bar` when profiles/termux/bin is on PATH) to reattach this tab's default session manually. Manual invocation also works in a child shell outside tmux. During automatic attachment, `exit` (including the `q` alias) closes only the current pane until the final pane/window exits. Closing that session then exits the outer shell, even after switching into a project. Termux enables `detach-on-destroy on`, so the client does not switch to another session. Manual `termux-bar` invocation returns to its caller. The launcher captures tmux completion output separately from terminal rendering: only a successful exact `[exited]` response produces internal exit status 20, consumed by the startup hook. Deliberate detach, unknown responses and server failure retain the shell. Detached sessions and their processes are retained, even after a Termux tab closes.

Set `DOTS_TERMUX_AUTOSTART=0` before initialization to disable automatic startup; manual `termux-bar` still works. Missing dependencies, identity errors or attachment failures leave a usable shell. Python 3, tmux, the sibling `termux-sessions` script and readable procfs are required; no dependency is installed automatically. New tabs load startup changes; existing tmux servers need their normal configuration reload for the layout and session-destruction behavior.

## User-local completion directories

Interactive personal startup gives user-local completion directories priority over repository providers. Paths follow XDG overrides, with `$HOME/.local/share` and `$HOME/.config` as the data and config fallbacks. Registration does not create directories or install completion files.

| Shell | User-local lookup |
| --- | --- |
| Zsh | Existing `$XDG_DATA_HOME/zsh/site-functions` is first in `fpath`, after plugin path setup and before compinit. The tied `FPATH` scalar is exported for child tools. |
| Bash | Caller-supplied `BASH_COMPLETION_USER_DIR` bases retain their order; the existing `$XDG_DATA_HOME/bash-completion` base is appended if absent. With no override, that base is the default even before it exists. bash-completion loads files from each base's `completions` subdirectory on demand. |
| Fish | Existing `$XDG_CONFIG_HOME/fish/completions` precedes `$XDG_DATA_HOME/fish/vendor_completions.d`, followed by Androidots, repository and remaining native paths. |

Repeated initialization deduplicates these entries. Zsh completion directories belong in `fpath`; Dots no longer adds its repository completion directory to executable `PATH`. Executable directories such as `~/.local/bin` keep their existing handling. Explicit tool-generated completion registrations retain their existing behavior; this ordering governs directory providers.

Start a new shell or reload personal configuration to pick up path changes. In Zsh, `rlcs` re-registers the local path and rebuilds discovery, retaining normal compinit ownership checks. A file must be a valid completion for its shell: directory registration neither restores backups nor establishes that a completion is installed.

Generic `dots init` hooks retain their integration-only contract, and noninteractive personal startup does not add these completion paths. PowerShell, Nushell and Xonsh retain their existing native integrations; no arbitrary-script directory loader is added. Native Windows has no equivalent Zsh fpath addition, and Windows application destinations are unchanged. Native Windows PowerShell 5.1/7 startup acceptance for this maintenance pass remains pending.

## Termux local completion directories

Interactive personal Bash/Zsh/Fish startup registers Androidots-local completion directories when the bundled Termux profile exists. Zsh adds `$DOTS/profiles/termux/shells/zsh/completions` before its single compinit, with the user-local site-functions directory taking priority. Bash appends the `$DOTS/profiles/termux/shells/bash` base after user bases in `BASH_COMPLETION_USER_DIR` before loading bash-completion. Fish places `$DOTS/profiles/termux/shells/fish/completions` after user-local directories and before repository completions. Repeated startup does not duplicate these entries.

These fixed-path additions neither scan/generate completions nor create directories, execute Android APIs, or install packages. Other platforms and noninteractive startup do not add them. Generic `dots init` hooks retain their integration-only contract. `termux-geo completion --all --install` explicitly creates its files at these locations; see [installation and shell activation](https://github.com/5nik7/androidots/blob/66bbe8bfd7a8a5c4fc7e69a837d79cd0cc256a6b/docs/termux-geo.md#shell-completions). Existing other-command completions remain in place.

## Installed startup and first use

The installer copies one interactive rc for each applicable shell. Bash’s login file forwards to the same rc and sources a user’s login profile. Dots keeps the standalone `~/.profile` for callers that source its common helpers and `~/.zshenv` for noninteractive Zsh. With the Dots login profile, an interactive Bash login loads those helpers once.

The installed rc honors an explicit `DOTS_BOOTSTRAP_DIR`. Otherwise it prefers a usable checkout reached through the installed executable, then the recorded checkout and then `~/dots`. This also selects the recorded checkout when another valid copy exists at `~/dots`. Bash and Zsh use a prepared bundle, Fish and PowerShell use prepared environment adapters, and Nushell and Xonsh resolve environment and settings together. Noninteractive sessions stay offline. Nushell can source its installed or conventional parse-time path offline. An interactive Nushell can select a different path at runtime before the first command. To distribute a checkout-independent entry yourself, use `dots init --bootstrap SHELL` for any of the six shells. [Startup preparation and first acquisition](profiles.md#missing-checkout-bootstrap)

Shared shell preferences live under `shells/<shell>/`. Each active profile layer can add `shells/init.<ext>` before the shared interactive configuration and `shells/local.<ext>` afterward. Extensions are `bash`, `zsh`, `fish`, `nu`, `xsh` and `ps1`. Parent layers run before the selected layer in each phase. For example, put a machine-specific Fish binding in `$PROFILE/shells/local.fish`. The PowerShell profile path is `$env:PROFILE`. Installed Nushell loads interactive definitions before accepting the first command.

Fish’s `conf.d` files own its autopair, command-finished notification, FZF binding and usage completion setup. Each runs once per interactive shell even when Fish’s native configuration discovery and the Dots rc both source it.

The Termux and WSL early Zsh hooks select their shipped `shells/zsh/local.zsh` defaults. Full startup applies them after shared aliases and before native FZF and final keybindings. An independent `~/.zshrc.local` runs immediately afterward, so it can override these defaults. If the home file links to the selected profile file, startup sources it once. The usual `$PROFILE/shells/local.zsh` remains the last profile override. Reloading reapplies ordinary preferences and preserves the caller's `LOCAL_OPTIONS` setting. Successful plugin and FZF activations are reused. An explicit `rl` retries unavailable providers.

The backend prepares the common tool paths and owns native tool initialization. Bash and Zsh register first-use completions for tools such as uv, uvx, pip and Starship. Configured prompts, directory hooks and editor bindings are ready at first use. Nushell keeps its existing prompt, keybindings and jump commands by default. Its selected Atuin hook also requires a readable `~/.atuin/bin/env`. PowerShell exposes tools through the explicit selections described above. [Shell settings and paths](shell-environment.md)

Fish and Xonsh retain their configured native prompt and provide zoxide jumps on demand. To enable directory tracking, runtime managers, or a replacement prompt from first input, set the shell-local `dots_shell_tools` list in the profile’s early file. Select individual tools such as `zoxide`, `direnv`, `mise`, `atuin` or `starship`, or select `all` for the installed providers. Nushell uses the same selection in `$env.dots_shell_tools`. Fish and Nushell also support `tv`. Television has no native Xonsh generator.

```fish
# $PROFILE/shells/init.fish
set -g dots_shell_tools zoxide direnv
```

```nu
# $PROFILE/shells/init.nu
$env.dots_shell_tools = ['zoxide' 'direnv']
# Use ['all'] to select every installed provider.
```

```xonsh
# $PROFILE/shells/init.xsh
dots_shell_tools = ['zoxide', 'direnv']
```

Startup now has opt-in metadata markers for [debug traces](debug.md). Normal
startup does not open a trace channel or start a tracing process. Generated
Bash/Zsh bundles preserve original module labels for instrumentation; private
hooks are observed only at source boundaries. Diagnostic traces do not enable
command xtrace or persist expanded arguments.

Interactive initialization also supplies [global less standout colors](shell-environment.md#global-less-colors). The standard environment overrides follow theme refresh, preserve explicit customization and remain available with named color shortcuts disabled. Native Windows less retains its stock rendering.


Dots command paths lead inherited/profile paths in each shell, including repeated initialization. `.ln` forwards to the shared safe-link command. Explicit STARSHIP_CONFIG values are retained; unset values use Starship defaults.

Bak completion is registered for standalone `bak`/`dots-bak` and `dots bak` in all six adapters. Zsh registration runs after compinit at the first prompt. Disabling completion removes Dots-owned Bash/Zsh/Fish Bak registrations. Preference cache inputs include separated JSON/TOML files and parent directories, so creating a previously absent profile preference file invalidates the bundle; warm startup retains the no-Python path.


### Startup bundle retention

Bash and Zsh publish immutable bundles beneath `$XDG_CACHE_HOME/dots/startup` (default `~/.cache/dots/startup`). The `current` and `previous` pointers retain two generations per shell and platform. A shell opens a bundle before checking its guard, so a concurrent rebuild can retire it while the open shell finishes its first initialization. Warm startup reads the pointer and checks only the selected inputs. The compact source map still resolves compiled lines to their original file and line. Earlier generations from installations predating retention are available for review in `dots cleanup scan --group builds`.
