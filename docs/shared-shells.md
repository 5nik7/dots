# Shared Bash and Zsh configuration

**Implemented.** Bash and Zsh load the same everyday functions and aliases from `shells/shared/functions.sh` and `shells/shared/aliases.sh`. Script utilities remain in `bin/lib/common.sh`. Native bootstrap, completion engines, prompt hooks and editor widgets stay in their respective shell adapters. Old function/alias entry points are compatibility loaders; edit the shared definitions instead.

## Commands and compatibility

Zsh's effective behavior is the default for conflicting definitions. Existing Zsh command names and completion mappings are retained. Bash-only helpers are also available in Zsh. Both shells use the existing safe `mkcd` implementation, and directory shortcuts quote paths at invocation time. `.sb` now enters the Bash configuration directory.

| Command | Shared behavior |
| --- | --- |
| `rl` / `rlp` | Reload the running shell's Dots configuration and report success. |
| `rlc command ...` | Reload native completions for the named commands; unavailable Bash providers produce a diagnostic. |
| `rlcs` | Refresh supported generated completions; Zsh also rebuilds its completion dump. |
| `ff` | FZF file picker with the existing terminal-aware preview. |
| `findfiles pattern` | Former Bash `ff` filename search. |
| `eff` | Edit the selected file; cancellation never opens the editor. |
| `l`, `ls`, `ll`, `lt` and variants | Zsh's eza layout when available; plain ls fallbacks otherwise. |
| `cd` | zoxide's `z` after successful activation; native cd otherwise. |
| `y` / `d`, `yap` | Yazi navigation/project helpers; failures preserve the caller's directory and temporary files are cleaned up. |
| `mkcd directory` | Enter an existing directory or create parents and enter it; refuse non-directory targets. |

Git/worktree, package, network and backup helpers remain explicit user commands. Startup never invokes them. Their existing workflows are not replaced by a new management engine.

## Interactive startup

Both shells share XDG defaults, editor selection, public application settings, ordered runtime paths, FZF layout and palette settings. Zsh retains its compatibility environment arrays, explicit private/platform module list and local hook. Bash retains its personal `~/.bash_aliases` hook, loaded after shared aliases. Zsh-only private modules are not interpreted by Bash.

Bash uses native Readline vi mode, quiet bells, supported insert/command cursor indicators, a 100,000-entry history limit, duplicate suppression and append/read synchronization at prompts. Bash and Zsh keep separate history files. No Bash editing plugin is installed: Zsh's syntax highlighting, autosuggestions and FZF-tab completion UI remain Zsh-specific.

Installed Bash integrations activate synchronously: zoxide, direnv, Atuin, Television, mise, usage, batpipe/batman and Starship, plus available Cargo, NVM, rbenv and Bun paths. Activation succeeds once per shell; failed and newly available tools can retry on reload. Bash-generated code is checked for successful generation and valid syntax before evaluation. Starship uses the same configuration as Zsh; a native prompt remains when it is unavailable. Batpipe's Bash environment is configured directly without its process-tree shell detection.

Bash loads installed bash-completion when available and the Dots/Anodize providers. Available uv, uvx, Starship, pip and ipinfo completions load once and can be explicitly refreshed. These Bash completion results are session-local; Zsh retains its existing generated-data cache. FZF bindings load after history/search integrations so FZF retains Ctrl-R, including after a newly available integration activates. Missing optional tools do not prevent shell startup.

Both shells load the published theme and Gum environment at startup and follow generation changes before the next prompt. Unchanged prompt checks use shell builtins; palette application replaces FZF colors rather than appending them. Bash composes with scalar or array `PROMPT_COMMAND`, and history/theme maintenance returns the incoming command status for downstream hooks. Publication and noninteractive initialization never execute the Gum artifact.

## Reload and verification

Open a fresh shell after this migration to initialize the full integration stack. Subsequent `rl` calls reapply ordinary shared settings, commands, aliases and themes without duplicate paths, hooks or key bindings. Personal overrides belong after the shared setup. Running child processes retain their inherited environment.

See [shell initialization](shell-init.md), [testing](testing.md#shell-initialization) and the [migration evidence](../plans/shared-shells.md). Native acceptance is on Termux; Linux/WSL/MSYS platform fixtures do not establish native desktop or Windows behavior. No tools, home-directory links or themes are installed by this migration.
