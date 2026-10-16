# Shell initialization

**Implemented.** `dots init [bash|zsh|fish|powershell|nu|xonsh]` prints native shell code. It initializes only Dots settings, paths, colors, completions and refresh hooks; it does not install files or packages. The live Bash dispatcher requires Bash 4.4 or newer. Native PowerShell initialization has a separate adapter.

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

Set `$env:DOTS` first when invoking that explicit path. The repository profile instead discovers its checkout from the resolved profile file, including symlinked parent directories and Windows junctions. After the repository's `bin` is on PATH, `dots.ps1 init powershell` is the explicit native spelling; `dots init powershell` also works when command lookup selects that adapter or the Bash executable. The native adapter only implements initialization and help. It does not make the rest of the Bash CLI available on native Windows.

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

## Environment and execution

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
