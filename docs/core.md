# Dots core: find your way around

Dots brings dotfiles, shells, themes, platform profiles and everyday maintenance under one command. Start with `dots` for help or `dots menu` for interactive workflows. The Bash and native PowerShell entry points share Python controllers; platform adapters choose native paths and capabilities.

## Choose a starting point

| What you want to do | Start here | Guide |
| --- | --- | --- |
| Install or remove this checkout | `dots files install --dry-run` | [Installation](installation.md) |
| Find a command | `dots help files`, `dots commands` | [Commands](commands.md) |
| Link, adopt or repair configuration files | `dots files list`, `dots files browse` | [Managed files](files.md) |
| Inspect or change a setting | `dots config`, `dots config explain KEY` | [Configuration](configuration.md) |
| Understand your shell environment | `dots env`, `dots profile` | [Environment](shell-environment.md) |
| Choose a palette | `dots theme list`, `dots theme show nord` | [Themes](themes.md) |
| Work with Git repositories | `dots git status`, `dots git publish --dry-run` | [Git](git.md) |
| Manage packages and fonts | `dots pkgs`, `dots fonts` | [Packages](packages.md), [fonts](fonts.md) |
| Track project goals | `todo`, `dots todo` | [Todo](todo.md) |
| Find bindings or sessions | `dots keys`, `dots menu tmux sessions` | [Keys](keys.md), [tmux](tmux.md) |
| Diagnose a problem | `dots debug` | [Debugging](debug.md) |

Standalone `todo` selects the current project, while `dots todo` always selects Dots. Standalone `theme`, `fonts`, `wttr`, `anodize`, `blastoff` and `pkgs` share their respective Dots implementations. Anodize authors palettes; Blastoff manages Starship themes and modules. See [bundled applications](bundled-applications.md) for their installation and runtime boundaries.

## Understand the checkout

| Location | Owns |
| --- | --- |
| `bin/` | Command entry points and static command metadata |
| `lib/dots/` | Shared controllers and native shell integration |
| `config/` | Canonical application configurations; temporary `configs` aliases remain |
| `profiles/` | Platform and inherited profile mappings, settings and environment |
| `default/` | Shared defaults and theme templates |
| `themes/` | Repository palette sources |
| `.dots/` | Source/resource identities, wiki mappings and project goals |
| `plugins/` | First-party Anodize, Blastoff and pkgs sources |
| `docs/` | Canonical guides and reference documentation |

Generated themes, journals and retained backups belong to platform state directories, not the portable source tree. Read [architecture](architecture.md) for component ownership and [data contracts](specification.md) for exact schemas. Optional Neovim and private sources keep separate ownership; see [Neovim](neovim.md).

## Preview, apply and recover

Read the selected command's help and use its supported `--dry-run` before a managed change. File operations classify destinations and preflight the whole plan; replacements retain the recovery information required by the workflow. A correct existing link is normally a no-op. Copying is an explicit alternative, never a silent fallback.

Use `dots files history` to inspect transactions and `dots files undo ID` for supported recovery. Undo checks for later changes before restoring anything. Optional retained user snapshots and mandatory rollback protection are different; package installations and external processes have their own recovery limits. Read [safety](safety.md) before relying on rollback for an operation.

## Read documentation locally

`dots wiki browse` reads the current source guides without a separate wiki checkout. `dots wiki search 'config precedence' --topics` finds relevant headings and passages. Ordinary `dots wiki search QUERY` searches literal text in the exported wiki; `dots wiki show PAGE --source` reads a canonical source file. The [wiki guide](wiki.md) explains browsing, export freshness and explicit publication.

After managed POSIX core installation, `man dots` shows the complete public first-party command reference. Native Windows uses the same [generated reference](https://github.com/5nik7/dots/wiki/Command-reference) through the wiki. Optional/private extensions are discovered by `dots commands` but are not exported into this public manual.

## Platform and contributor boundaries

Termux is the primary local target. Linux, WSL and native Windows use separate destinations and state; native Windows does not require Bash for first-party controller routes. Capability and runtime evidence vary by command, so consult [platforms](platforms.md) and [PowerShell](powershell.md).

Contributors start with [AGENTS.md](../AGENTS.md), the [documentation index](README.md), [principles](principles.md) and the applicable [plan](../plans/README.md). Work in the existing checkout by default; optional worktrees follow the [worktree guide](../agents/guides/worktrees.md). Documentation changes do not authorize installation, commits or publication.
