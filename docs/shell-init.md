# Shell initialization

**Implemented.** `dots init [bash|zsh|fish|powershell|nu|xonsh]` prints native shell code. It connects a shell to the existing Dots configuration; it does not install files or packages. The live Bash dispatcher requires Bash 4.4 or newer. Native PowerShell initialization has a separate adapter.

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

Keep the complete checkout layout, including `shells/<shell>`, `bin`, and the existing shared modules. The checkout may have any name and live outside the home directory. Link the shell's normal startup file to its repository entry: Bash `.bashrc`, Zsh `zshenv`/`zshrc`, Fish `config.fish`, Nushell `config.nu`, Xonsh `.xonshrc`, or PowerShell `Microsoft.PowerShell_profile.ps1`. Linking the containing configuration directory is also supported. Existing `ZDOTDIR` and shell-specific configuration-directory settings retain their normal shell meaning.

Startup resolves absolute and relative links, chained links, and symlinked parent directories before deriving paths. Relative link targets are relative to the link's directory. The caller's working directory is preserved. Bash requires `readlink` only for file symlinks; GNU `readlink -f` is not required. The other adapters use native path facilities. Missing checkout files and resolution failures report errors without falling back to another checkout. If a broken or cyclic rc link prevents the shell from reading the file at all, the shell handles that failure before Dots code runs.

After moving the checkout, update links that still name its old location. No config-file edits are needed. Explicit generated hooks contain a fixed loader path and must be regenerated if that path changes. An individually copied rc file outside the checkout cannot discover its former location; use a symlink or an explicit hook instead. The shared POSIX profile snippets consume `DOTS` when available and do not independently discover a checkout.

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

These values replace inherited values on every initialization, including evaluation of a generated hook. Set custom overrides after initialization. Bash retains its built-in `BASH` executable variable; its configuration directory is `SHELLS/bash`. Existing directories from `DOTBIN` and `DOTSCRIPTS` are prepended in that sequence unless already present; existing PATH entries retain their order. Native shells retain their own PATH representations. No Windows/WSL translation occurs.

Generation emits loader references only. It never sources environment files, reads private modules, captures the whole environment, scans extensions, installs plugins, publishes themes, or writes caches. Invalid arguments exit 2; unavailable loaders exit 1; both leave stdout empty. Help is human output; initialization is undecorated code even under forced color/icons. Diagnostics use stderr. As with other eval hooks, `eval "$(...)"` can obscure the generator's exit status; capture and check output first when scripting error-sensitive setup.

Evaluating the hook loads common defaults, then the current shell's configuration in interactive sessions. Zsh retains its existing environment-module order, private/local hooks, themes, plugins, and tool activations. Other shells retain their existing integrations; Zsh-only modules are not interpreted or exported through foreign shells. No cross-shell feature parity is implied. Existing Zsh first-run plugin bootstrap remains part of evaluating interactive configuration, not generating the hook.

Repeated evaluation reapplies ordinary configuration without duplicate Dots PATH entries or tool/plugin activation. Fish snippets use shell-local guards shared by native `conf.d` startup and manual initialization. Nushell FZF bindings replace their own named entries and its completer guard is scoped to the current process. Generated and third-party Fish snippet bodies retain their separate ownership. PowerShell's generated integration blocks are preserved and activated once per session.

Explicit noninteractive initialization loads only common paths. Zsh's `zshenv` also derives and exports the checkout paths and performs native platform detection without external commands. Native startup wrappers load their adjacent loaders without starting the CLI. Login-file behavior and existing local hooks remain in place. Repository source edits do not create or replace home-directory links.

Interactive Bash/Zsh startup also loads the published Gum environment from `${XDG_STATE_HOME:-$HOME/.local/state}/dots/current/theme/gum_env.sh` when it is a readable regular file. Missing artifacts are optional. The file is trusted shell configuration, including personal overrides; noninteractive initialization and hook generation do not execute it. Zsh's existing published-theme hook reloads Gum colors on generation changes, while Bash reloads them with its interactive configuration. See [theme environment loading](themes.md).

## Verification

Run `python3 -B tools/test_shell_init.py` for isolated native contracts. It owns home, config, data, state, cache, repository, and terminal fixtures; private modules are synthetic. Unavailable shells are reported as skips. The Xonsh interactive test uses readline with a test-owned PTY rather than depending on optional prompt-toolkit. Run `python3 -B tools/test_powershell_init.py` on a machine with `pwsh` for portable native PowerShell parsing, generation, environment and error checks. This separate runner does not require Bash, POSIX PTYs, symlink privileges or a live profile. It is not native Windows evidence when run on another platform.

Run the Bash dispatcher and Zsh suites for shared behavior. Startup measurements and remaining platform/regression limits are recorded in the [initialization plan](../plans/shell-init.md).
