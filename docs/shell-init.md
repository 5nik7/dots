# Shell initialization

**Implemented.** `dots init [bash|zsh|fish|powershell|nu|xonsh]` prints native shell code. It initializes only Dots settings, paths, colors, completions and refresh hooks; it does not install files or packages. The separate explicit `dots init --setup` mode delegates to [checkout installation](installation.md); ordinary hook generation/evaluation remains unchanged. The live Bash dispatcher requires Bash 4.4 or newer. Native PowerShell initialization has a separate adapter.

## Using the hook

For Bash and Zsh, put this in the interactive startup file once `dots` is on PATH:

```sh
eval "$(dots init)"
```

The generated default hook selects Bash or Zsh in the receiving shell. It does not use `$SHELL`, which can name a different login shell. Explicit `dots init bash` and `dots init zsh` forms are also available. The repository startup files resolve their own symlinks and source the adjacent native loader directly; `dots` need not be on PATH. Link or source the startup file from the checkout you want to use. Inherited `DOTS` values do not select another checkout during native startup.

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

## Linked startup files and relocation

Keep the complete checkout layout, including `shells/<shell>`, `lib/dots/shell`, `bin`, and the existing shared modules. The checkout may have any name and live outside the home directory. Link the shell's normal startup file to its repository entry: Bash `.bashrc`, Zsh `zshenv`/`zshrc`, Fish `config.fish`, Nushell `config.nu`, Xonsh `.xonshrc`, or PowerShell `Microsoft.PowerShell_profile.ps1`. Linking the containing configuration directory is also supported. Existing `ZDOTDIR` and shell-specific configuration-directory settings retain their normal shell meaning.

Startup resolves absolute and relative links, chained links, and symlinked parent directories before deriving paths. Relative link targets are relative to the link's directory. The caller's working directory is preserved. Bash requires `readlink` only for file symlinks; GNU `readlink -f` is not required. The other adapters use native path facilities. Missing checkout files and resolution failures report errors without falling back to another checkout. If a broken or cyclic rc link prevents the shell from reading the file at all, the shell handles that failure before Dots code runs.

After moving the checkout, update links that still name its old location. No config-file edits are needed. Explicit generated hooks contain a fixed loader path and must be regenerated if that path changes. An individually copied rc file outside the checkout cannot discover its former location; use a symlink or an explicit hook instead. The shared profile, `shells/profile` (linked as `~/.profile`), consumes `DOTS` when available and does not independently discover a checkout.

## PowerShell profile

The personal PowerShell entry is `shells/powershell/profile.ps1`; `Microsoft.PowerShell_profile.ps1` remains a compatibility entry for existing installer links. Both discover the linked checkout. Link each engine's `$PROFILE.CurrentUserAllHosts` to the shared entry to use it in Core and Desktop. Dots settings, published colors and completion load once; only interactive sessions load personal helpers. Re-sourcing preserves the prompt chain and avoids duplicate personal setup.

Interactive Core and Desktop sessions initialize Starship automatically, using the existing `STARSHIP_CONFIG` or Starship default. Missing or failed Starship initialization leaves a plain directory prompt. After Starship and Dots refresh setup, startup sources `shell-integration_v7.ps1` beside that engine's `$PROFILE.CurrentUserAllHosts` when present. Existing host-specific integration hooks remain safe because the vendor wrapper is idempotent; the vendor files are not rewritten. Console sessions use PSReadLine Vi mode, native Tab completion and **Alt+F** for fuzzy completion. Alt+F imports PSFzf on demand; absent FZF or PSFzf falls back to native completion. Redirected input skips line-editor setup. The `ls` helper uses eza without Git-status scans when available, otherwise `Get-ChildItem`. Editor selection is deferred until `edit`/`e`/`ep` is used and respects an existing `EDITOR`; otherwise it prefers nvim, code, vim, vi, then notepad. `ep` edits the repository profile source.

Other integrations remain disabled by default. Dot-source the optional loader in the current session, for example:

```powershell
. "$env:PWSH/optional.ps1" starship
. "$env:PWSH/optional.ps1" completions
. "$env:PWSH/optional.ps1" mise
```

Available feature names are `starship`, `blastoff`, `icons`, `catppuccin`, `pscompletions`, `fzf`, `completions`, `zoxide`, `mise`, `vfox`, `chocolatey`, `command-not-found`, `terminal` and `coreutils`. Each successful opt-in runs once per session; failed loads remain retryable. Choose the runtime manager you actually use. The loader uses installed tools only, checks generated-code exit status, and restores Dots refresh hooks after Starship activation. The coreutils vendor block is preserved in a separate opt-in file. Default startup runs Starship initialization, its continuation prompt, and the configured terminal integration; unrelated completion generators, module inventory, runtime managers and theme publication stay off. Starship prompt cost depends on the active configuration. Blastoff defaults `BLASTOFF_HOME` to the resolved checkout's `config/blastoff`, preserving an explicit override. Blastoff is available through installed-module autoloading in Core only (7+); the optional loader refuses it on Desktop. WinGet CommandNotFound requires Core 7.4+. Neither module is eagerly imported by the profile.

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

At the end of Dots Bash/Zsh interactive initialization, `shells/shared/termux-tmux.sh` invokes `androidots/bin/termux-bar --auto` once per outer shell. The hook requires the Termux platform, inherited `TERMUX_APP__PID`, terminal stdin/stdout, and no tmux or SSH context. The launcher verifies that its calling shell is the terminal session leader directly beneath the Termux app process; child shells do not attach. Scripts, redirected shells, Fish and other platforms are unaffected. Reloading configuration after detaching does not reattach.

Each tab gets a session named internally as `termux-<root-pid>-<start-ticks>`, starting in the caller's directory. A fresh `termux-sessions --get pid --pid ...` query identifies the tab; procfs start time prevents PID reuse from attaching a later tab to an older session. Existing marked sessions are reused without changing their directory or windows. An unmarked name collision is refused. No registry, cache or automatic session cleanup is added.

The launcher uses the existing default tmux server. The session-local `@dots-termux-default=1` option suppresses only the status name badge; the clock/network/battery row and lower-row Termux numbers, windows and mode indicators remain. Other sessions, including projects selected through `t`, keep their names. The internal default name remains visible in tmux's session chooser. Existing session-navigation bindings can return from a project to a default session.

Detaching resumes the outer shell; its bar disappears until reattachment. Run `~/dots/androidots/bin/termux-bar` (or `termux-bar` when androidots/bin is on PATH) to reattach this tab's default session manually. Manual invocation also works in a child shell outside tmux. During automatic attachment, `exit` (including the `q` alias) closes only the current pane until the final pane/window exits. Closing that session then exits the outer shell, even after switching into a project. Termux enables `detach-on-destroy on`, so the client does not switch to another session. Manual `termux-bar` invocation returns to its caller. The launcher captures tmux completion output separately from terminal rendering: only a successful exact `[exited]` response produces internal exit status 20, consumed by the startup hook. Deliberate detach, unknown responses and server failure retain the shell. Detached sessions and their processes are retained, even after a Termux tab closes.

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

Interactive personal Bash/Zsh/Fish startup registers Androidots-local completion directories when the Androidots checkout exists. Zsh adds `$DOTS/androidots/shells/zsh/completions` before its single compinit, with the user-local site-functions directory taking priority. Bash appends the `$DOTS/androidots/shells/bash` base after user bases in `BASH_COMPLETION_USER_DIR` before loading bash-completion. Fish places `$DOTS/androidots/shells/fish/completions` after user-local directories and before repository completions. Repeated startup does not duplicate these entries.

These fixed-path additions neither scan/generate completions nor create directories, execute Android APIs, or install packages. Other platforms and noninteractive startup do not add them. Generic `dots init` hooks retain their integration-only contract. `termux-geo completion --all --install` explicitly creates its files at these locations; see [installation and shell activation](../androidots/docs/termux-geo.md#shell-completions). Existing other-command completions remain in place.
