# Tmux keybinding reference

Current follow-up: the shared [keybinding browser](keys.md) supersedes the less viewer and popup wrapper below; earlier verification remains historical.

**Status: Implemented and verified on Termux, including popup theme colors on 2026-10-22.**

## Scope and decisions

- Ship `dots-menu-tmux-keys` and the automatically discovered `dots menu tmux keys` route. Show described live bindings, including tmux defaults/plugins, in a searchable, read-only less pager; `--print` bypasses paging. No action selector, raw-command fallback, JSON, installation, server reload, or state writes.
- Use Dots headings/styles and controls; retain the user's replacement of the Omarchy call in `config/tmux/tmux.conf`. The current binding inherits the shared popup border and retains its bold yellow icon title through tmux's styled `-T`. The 2026-10-22 follow-up gives all popups the shared theme’s `background` and `foreground`, with `lighter_background` borders and terminal-color fallbacks before publication. The new command must be on tmux's PATH.
- Keep less optional, with warning plus complete printed fallback. Normal exit/empty results succeed, invalid syntax returns 2, operational failures return 1, and pager interruption returns 130. Static help/completion never contact tmux.
- Prefix legend uses the current pane's session when available. Group notes by table: prefix, root, copy-mode-vi, copy-mode, then custom tables; omit empty sections. Preserve tmux key spelling and within-table order.

## Verified adjustment to the initial plan

The initial plan proposed enumerating tables from canonical binding commands and reading `list-keys -N` for each table. Native inspection of tmux 3.7c showed that note output may contain literal tabs/newlines and canonical command output does not safely frame arbitrary table names. Instead, one `list-keys -F` snapshot uses `q|a` quoting for `key_table`, `key_string`, and `key_note`. The non-evaluating parser removes ordinary quoting while leaving control escapes visible. Unsupported/malformed output fails before stdout. This explicitly requires formatted key listing support rather than claiming compatibility with every version supporting notes.

All tmux queries use global `-N` to prohibit server startup and `-u` to preserve Unicode and field separators in ASCII locales. This was verified against the installed manual and a disposable server. No shell evaluation or configuration sourcing is involved.

## Presentation acceptance

Follow the [presentation contract](../docs/presentation.md#acceptance-gate). Human terminal and printed modes share `ui.bash`; headings/counts use cyan and keys/labels use blue. Resolve destination color before capturing output or piping to less. Diagnostics independently use stderr policy. Escape control characters and retain full descriptions. After user feedback, reference rows now keep keys and descriptions on the same logical line at every width, with per-table padding capped at 12 characters and an inline prefix legend. Long content may wrap naturally; it is never deliberately stacked or truncated. The viewer-specific row helper reuses shared semantic styles without changing other commands' narrow layouts.

Coverage includes help, populated/empty lists, dependency warnings, malformed/query/pager failures, auto/forced/disabled color, `NO_COLOR`, `TERM=dumb`, redirected streams, spaces, Unicode, leading dashes, quoted punctuation, and terminal-control injection. PTYs exercise 40/50/80/120 columns, including a 50-column regression for the reported phone-popup layout. Structured data, mutations, conflicts, previews, partial apply, rollback and recovery do not apply. Printed output is not a stable machine schema.

The less child clears inherited options and preprocessor hooks, enables secure mode, and never evaluates `$PAGER`. No quit-if-one-screen option is used. Early quit has no producer SIGPIPE because the complete rendered view is supplied through a here-string.

## Verification

- [x] Focused fake-tool and native suite: `python3 -B tools/test_tmux_keys.py` — 19 tests passed on Termux, including native tmux 3.7c quoted records/session prefixes, the repository popup binding and blue/cyan decoration, `q` returning control to tmux, and native less short-list/search/exit input.
- [x] Bash dispatcher/metadata/three-shell completion suite: `python3 -B tools/test_bash_dots.py` — 24 tests passed, including native Bash/Zsh/Fish Tab acceptance.
- [x] Final Bash syntax, ShellCheck and `git diff --check` passed.
- [x] Full relative-link audit: 567 links across 76 Markdown files, no newly broken links.
- The original repository-wide documentation check was blocked by a missing Yazi README link. The 2026-10-22 rerun passes all 818 links across 110 files.

Independent review follow-ups: the popup test now explicitly starts its session in the owned home and asserts the popup's working directory. The sanitizer preserves valid UTF-8 sequences under byte-oriented C locales while escaping C1 controls; added C/C.UTF-8 arrow, emoji, combining-character and C1 regressions. Termux still uses codepoint iteration in C, so this does not establish native Linux byte-locale evidence.

Tests own their homes/config/state/cache/repositories, tmux sockets and terminals. Preserve Termux's inherited `LD_PRELOAD` when running through a sanitized tool environment. Native Linux/WSL/Windows verification and graphical visual review are not claimed; terminal captures provide the current layout evidence. No dependency installation, commits or pushes are part of this task.

## Popup theme follow-up (2026-10-22)

Use the shared tmux template for popup content colors, preserving border/title overrides and geometry. Verify dark/light publication and the actual keybinding popup in owned tmux servers, then refresh the selected live theme and apply its popup style to the existing server. Native Windows PowerShell has no tmux equivalent; no Windows destination or shell interface changes. Native Linux/WSL acceptance remains pending.

Verified on Termux with tmux 3.8: all 19 keybinding tests pass, including the actual popup's RGB background, current border/title colors and dismissal. The isolated application connector test passes with Nord and Catppuccin Latte popup colors loaded into a private tmux server. Documentation links and whitespace checks pass. Live refresh retains Catppuccin Mocha and publishes the popup colors through the normal journaled publisher; the running server reports `bg=#1e1e2e,fg=#cdd6f4`.

The border follow-up removes the binding’s hardcoded `-S` override and publishes `popup-border-style` with `lighter_background` foreground on `background`. Acceptance covers dark/light publication, native popup RGB border rendering, and selective live binding reload after theme publication.

Border verification passed on Termux/tmux 3.8: all 19 keybinding tests, the isolated dark/light application connector case, documentation links and whitespace checks. Live publication and selective binding reload completed; `popup-border-style` reports `fg=#313244,bg=#1e1e2e`, and the active keybindings binding has no border override.
