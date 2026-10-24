# Dots shell environment

`dots init [bash|zsh|fish|nu|xonsh|powershell]` emits a hook for **Dots integration
only**. The adapters under `lib/dots/shell/` own settings, derived paths, theme
variables, Dots completions and prompt refresh. Personal aliases, prompt choice,
plugins and third-party tools remain under `shells/`; shared application/editor defaults belong to the environment registry. Repository
startup files load both layers; an explicit hook in another rc loads only Dots.

## Starship configuration

Dots personal startup no longer sets `STARSHIP_CONFIG`. Starship discovers
`~/.config/starship.toml` (including on Windows); the managed resource links that
home-relative path to `config/starship/starship.toml`, independently of
`XDG_CONFIG_HOME`. On startup/reload, native adapters remove only recognized old
Dots-generated overrides. Deliberate custom values remain supported. Windots
Clink follows the same rule. Existing links and prompt contents are retained.
Blastoff 0.1.12 preserves this active-file link during normal writes and tracks
the resolved repository file; explicit `--replace-link` still converts the link.

## Settings

Edit `${XDG_CONFIG_HOME:-$HOME/.config}/dots/config.env`. Native Windows PowerShell
uses `%APPDATA%/dots/config.env` unless XDG_CONFIG_HOME is set. DOTS_CONFIG_FILE
selects an explicit file. A missing file uses defaults; initialization does not
create it. For example:

```ini
DOTS_THEME_DEFAULT=catppuccin-mocha
DOTS_INIT_THEME=1
DOTS_THEME_AUTO_UPDATE=1
DOTS_INIT_COLORS=1
DOTS_INIT_COMMANDS=1
DOTS_INIT_COMPLETION=1
DOTS_TERMUX_AUTOSTART=0
DOTS_ZSH_SUGGESTIONS=autosuggestions
```

This is data, not a shell script. Values are literal, optionally enclosed in
matching single or double quotes. Blank lines and whole-line `#` comments are
accepted. Expansion, command substitution, `export`, unknown keys and duplicate
keys are not accepted. Invalid settings stop initialization before replacing the
last resolved settings. Explicit nonempty environment overrides take precedence
over the file, then built-in defaults apply. File-derived defaults are not
exported into the override namespace, so subsequent reloads see edits correctly.

Settings are defined in [settings.tsv](../lib/dots/shell/settings.tsv).
Boolean options use `0` or `1`; all six integration switches default to `1`.
The fallback theme is `catppuccin-mocha`. DOTS_COLOR and DOTS_ICONS accept
`auto`, `always`, or `never` and default to `auto`. The personal Termux hook
defaults on; the personal Zsh suggestions setting defaults to `deja` and also
accepts `autosuggestions` or `none`. Initializing Dots alone does not activate
those personal integrations.

Settings apply when initialization runs again, including a new shell or the
repository's `rl` helper. Theme changes follow published state at the next prompt
when enabled. No settings watcher, background service, theme-directory scan or
palette calculation runs on ordinary prompts. Shell/plugin activation preferences
may still require a new shell.

## Variables and diagnostics

DOTS is the selected checkout. [paths.tsv](../lib/dots/shell/paths.tsv) defines
the common path exports and shortcut keys for every native adapter. DOTBIN, DOTSCRIPTS, DOTFILES, DOTSHHHH, SHELLS,
ZSH, PWSH and the theme command paths are derived from it. DOTCONFIG remains a
compatibility alias of DOTFILES. These runtime paths are not config options.
`dot` provides named paths including root, bin, scripts, files/configs, secrets,
shells, themes, config and state; its theme entry follows the selected theme.

| Shell | Paths | Color formats |
| --- | --- | --- |
| Bash | `${dot[root]}` | `${blue[hex]}` |
| Zsh | `$dot[root]` | `$blue[hex]` |
| Fish | `$dot_root` | `$dots_color_blue_hex` |
| Nushell | `$env.dot.root` | `$env.dots_colors.blue.hex` |
| Xonsh | `dot['root']` | `blue['hex']` |
| PowerShell | `$dot.root` | `$dots_colors.blue.hex` |

Native palette and semantic-role maps remain available. Named color shortcuts
are optional; stale Dots-owned colors are removed when a new palette loads.
`rst` and `RST` reset SGR colors and attributes; PowerShell's case-insensitive
variable names make them the same variable. Shell maps/records are native runtime
values, not portable exported arrays. Child processes use scalar exports or CLI
queries. The old 256-entry COLOR/FG/BG maps are no longer allocated at startup;
their explicit utility functions remain callable for compatibility.

```sh
dots env                         # resolved Dots values and provenance
dots env DOTS_THEME_DEFAULT      # one undecorated value
dots env --json                  # versioned values/source records
theme current                   # selected full theme ID
theme color blue hex            # selected resolved palette value
```

`dots env` reports configuration and published state, not arbitrary variables in
the parent shell. It does not enumerate the whole environment, read secrets, or
pretend to inspect parent-local arrays. JSON has `version: 1` and a `values`
object whose entries contain `value` and `source` strings.

In a terminal, `dots env` groups the current theme, settings and paths with shared
Dots colors. Boolean settings retain `0`/`1` alongside disabled/enabled labels;
each value includes its source. Short rows align, while long values and narrow
terminals use stacked fields and wrapped complete paths. Human path fields abbreviate
the home directory as `~` and its descendants as `~/…` (using native separators on
Windows); unrelated path prefixes remain absolute. Display-only control
characters are escaped. Non-ASCII widths are conservatively budgeted without a
new runtime dependency; byte-oriented locales may show escaped Unicode.

Use `dots --color=none env` for the same human layout without styling, or
`dots --color=always env` to force colored human output when redirected. Automatic
color honors `NO_COLOR` and the destination terminal. An ordinary unforced pipe
retains the original `NAME=value [source]` lines. Scalar and JSON queries bypass
all decoration and preserve their exact values. The view uses the terminal palette
and does not load a theme or change shell settings.

## Theme state and native adapters

Selection precedence is DOTS_THEME_SELECTION, the published generation, then
DOTS_THEME_DEFAULT. Selection changes remain journaled; changing themes does not
rewrite config.env. Repository `.default`/`.theme` files and `$HOME/.theme` are
no longer selection inputs. The approved legacy repository files have been removed;
`$HOME/.theme` is left untouched. See the [cleanup record](../plans/shell-environment.md#approved-cleanup).

Publication includes `shell.tsv`, a data-only snapshot of identity, native colors,
roles and color formats. Fish, Nushell, Xonsh and PowerShell read this snapshot;
Bash/Zsh retain their generated sourceable initialization and FSH/Gum integration.
All adapters read the published `ls_colors` artifact alongside their palette.
Vivid runs during publication rather than shell startup for new generations. After upgrading from an older generation, run `theme refresh` to
publish the new snapshot. Missing or malformed snapshots retain previous colors;
a fresh native shell remains usable without theme colors until publication.

Native Windows PowerShell initialization needs no Bash. Profile environment preparation uses Python on a cold load; warm loads use the prepared native adapter.
The [native PowerShell adapter](powershell.md) now provides the CLI and Windows theme publication through Python; warm initialization uses native prepared code and never translates WSL paths.
PowerShell completion uses native readers without Bash. Native
PowerShell and the normal Xonsh launcher must be verified where those runtimes
are available; Termux evidence does not establish Windows support.

## Verification

`python3 -B tools/test_shell_environment.py -v` uses temporary home, config,
state and cache roots and sources only the public library adapters. It checks
literal settings, reload failure, diagnostics, native palette data and the
integration-only boundary. Existing shell-init, theme publication, dispatcher
and completion tests cover their respective contracts. Run focused cases
sequentially on Termux rather than concurrent full suites.

The personal PowerShell profile defaults `BLASTOFF_HOME` to `DOTCONFIG/blastoff` when unset. This is a personal tool setting, outside the shared Dots settings schema; an explicit override is preserved. Starship and Blastoff continue to honor `STARSHIP_CONFIG`. See [PowerShell startup](shell-init.md#powershell-profile).

## Shared profile environment

Application defaults now live in `lib/dots/shell/environment.json`, overlaid by
active literal profile definitions. `dots env` includes these defaults and
exported hook evidence, with private-value redaction. See the authoritative
[profile/environment contract](profiles.md).

## Retired Ruby environment

`DOTRUBY` and `RUBYCOMP` are removed from the environment registry and completion. Initialization/reload unsets inherited values and removes their provenance records. Profile definitions cannot redeclare them. Only the obsolete `ruby/completion` entry under the current checkout, previous `DOTS_PROFILE_CHECKOUT`, or default `~/dots` is removed from PATH, including a trailing slash. Unrelated Ruby paths remain. This applies to Bash, Zsh, Fish, PowerShell, Nushell and Xonsh adapters; a child CLI cannot alter an already-running parent shell. Open a new shell or reload Dots initialization to apply the cleanup. `config/ruby` is independent and remains supported.
