# Zsh Configuration

The shared configuration supports the existing Termux workflow with explicit startup stages. WSL/Linux detection and path policy have fixture coverage; native WSL/Linux and MSYS2 interactive verification remain pending. MSYS2 has a separate adapter and does not share WSL cache identity.

## Startup Order

`zshenv` sets the repository default and detects the execution environment without external commands. It retains `dotstro`, `is_termux`, `is_wsl`, and `has_pip_pkg`. Set `DOTS` before launching Zsh to use another checkout; its default is `$HOME/dots`.

`zshrc` loads these stages synchronously:

1. `core/environment.zsh`: XDG defaults, shared utilities, environment modules, editor selection, and paths.
2. `core/cache.zsh`, existing functions/aliases/options/FZF settings, and the selected theme.
3. Installed completion providers, followed by `core/completion.zsh` and one `compinit` with its normal ownership checks.
4. `integrations/tools.zsh`: immediately available runtime managers, directory hooks, history integration, generated completions, and Starship.
5. The existing local configuration hook, FZF shell bindings, then FZF-tab and widget-wrapping plugins.

Existing `functions.zsh`, `aliases.zsh`, `options.zsh`, `fzf.zsh`, `completions.zsh`, and `plugins.zsh` entry points remain available. Tool activation and plugin/widget wrapping happen once per shell; start a new shell after changing their activation code. `rl` reloads ordinary configuration and reapplies the theme without duplicating hooks or FZF options.

The first-run Zinit/plugin download behavior is retained. Installed plugins are reused. Missing optional tools do not prevent basic shell use; this is not an installer or a claim that every optional integration works without its dependencies.

## Environment Modules

The explicit compatibility list replaces the recursive repository scan:

```text
androidots/termux.env
bin/colors.env
dot.env
ruby/ruby.env
secrets/secrets.env
shells/shells.env
themes/themes.env
windots/win.env
```

Readable files are sourced in this order, including existing platform-specific files for compatibility. Missing optional sources are skipped; no submodule is initialized. The list does not inspect or expose private values. Register additional absolute paths in a Zsh array before the loader runs, for example in a local startup wrapper:

```zsh
DOTS_ZSH_EXTRA_ENV=("$HOME/my-shell/environment.zsh")
source "$DOTS/shells/zsh/zshrc"
```

The existing `secrets.sh` and `zsh[local]` hooks remain supported and reapply on reload. Platform adapters centralize new environment-specific behavior; compatibility modules retain their existing contents.

## Paths and Platforms

Zsh path insertion uses literal array membership and preserves existing precedence. Existing directories are retained in place; missing directories are not added. `fixpath` removes duplicate entries without sorting executable precedence. Shared utility functions retain their Bash path implementation.

Termux derives site-functions from its prefix. Linux and WSL retain the installed shell's native completion paths. WSL detection accepts its environment markers, kernel release, or distribution configuration; distribution names remain separate from execution context. MSYS/Cygwin detection selects the MSYS adapter. No adapter translates drive paths, imports Windows PATH, or enables cross-filesystem linking.

For WSL performance, prefer keeping the checkout, plugins, and cache on its Linux filesystem. MSYS2's native behavior still requires verification.

## Generated Data and Reloads

Generated `uv`, `uvx`, and Starship completions live beneath `$XDG_CACHE_HOME/dots/zsh/<platform>-<zsh-version>/`. Cache signatures include the resolved executable's path and file metadata and generator arguments. Generation is synchronous on a miss, validated as Zsh syntax, and published through a temporary file and rename. Failed generation is never evaluated. If storage is unavailable, successful validated output can still be used for the current shell.

Metadata-preserving in-place executable edits can require an explicit refresh. `rlcs` deletes these generated completion entries and the configured completion dump, rebuilds completion, and reconnects FZF-tab. `rlc command ...` reloads selected autoloadable completion functions. Existing `ZSH_COMPDUMP` overrides are honored; otherwise the dump uses the platform/version cache directory. No `compinit -C` shortcut disables ownership checks.

Completion dumps are normalized before loading and after generation so autoload declarations treat names such as Termux's `_uu-[` literally. Existing affected dumps are repaired automatically, with stale compiled copies invalidated. If an affected dump cannot be rewritten, completion initializes in memory without loading it. Normal shell globbing remains enabled; only the dump's autoload declarations use [Zsh's `noglob` modifier](https://zsh.sourceforge.io/Doc/Release/Shell-Grammar.html#Precommand-Modifiers).

Vivid's `LS_COLORS` output is cached as data using the selected theme, executable, and metadata for [Vivid's documented custom theme/database locations](https://github.com/sharkdp/vivid#customization). Theme changes and changed inputs invalidate it. Catppuccin keeps its existing generated-palette cache. Theme application replaces FZF color options instead of appending duplicates.

Session-dependent activation remains immediate. Prompt modules, display formatting, and timeout settings are preserved. The Git-host icon uses a shell pattern instead of a separate grep process. The malformed `NVM_DIR` default and `ll` alias are corrected; an existing NVM installation can therefore initialize where the old typo prevented it.

## Verification

Run from the repository root:

```bash
python3 -B tools/test_zsh.py
python3 -B tools/zsh_fixture.py --samples 10
python3 -B tools/zsh_interactive.py --samples 5
python3 -B tools/verify_core.py docs
git diff --check
```

The unit suite owns disposable roots and needs installed Zsh plus basic host tools. The timing and PTY tools also require the existing public Zinit installation and five configured plugins; they copy them without Git history. They copy only selected public configuration and use synthetic private/platform modules. Their Git wrapper refuses remote operations. They do not install dependencies or source the developer's startup files.

Timing fixtures use fresh HOME, configuration, state, cache, history, and repository roots. Termux interpreter support is retained. The non-PTY startup test can emit ZLE warnings from installed integrations; real interaction is checked separately using a controlling pseudo-terminal. Use `tools/zsh_compare.py <baseline-source-directory>` for a public-interface comparison. The PTY runner accepts `--baseline` to report historical reload differences without failing its equality check. Fixtures and logs remain in the reported temporary directory for inspection. Logs contain fixture state only.

`ZSH_DEBUGRC=1` retains function profiling. Use the disposable fixture for profiling, especially when private/local modules could have side effects. Measurements and limitations belong in the [focused plan](../../plans/zsh-startup.md).
