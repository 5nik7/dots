# Unified keybinding browser

Status: implemented locally; native Windows and personal terminal acceptance pending.

Implement the approved `dots keys [APP]` browser for Zsh, Bash, PowerShell,
tmux, Neovim, Yazi, FZF, Kitty and Television. Capture caller-owned live state
on demand; otherwise parse literal configuration and installed default data.
Never execute configurations or binding actions to discover keys. Preserve
explicit coverage and source distinctions, exact JSON and existing user edits.
Use content-sized category/app menus, then FZF popup center,99% in tmux and ordinary FZF elsewhere. Retain the old tmux
route. Add the Termux vi-mode insert Backspace callback fix.

Acceptance includes native caller capture, configured parsing, malformed inputs,
control/sequence notation, live precedence, optional dependencies, popup argv,
40/80/120-column presentation, JSON, completion and isolated Neovim/tmux/ZLE
checks. Follow the [presentation gate](README.md#presentation-gate-for-every-plan).
Update docs and the local wiki. Native Windows runtime acceptance is separate.

## Local verification

Category refinement: implemented and verified locally. Interactive `dots keys` and
Prefix → ? open the icon category menu; Apps offers provider counts and availability.
Direct `dots keys all|APP` bypasses categories. Binding previews occupy 45%, with
muted metadata and bold bright-magenta keys. Noninteractive reports and caller
snapshots are preserved. The private-server test exercised category → Apps → tmux,
category → All, and cancellation back to the original pane. After it passed,
only the running server's stale `?` binding was replaced; its previous value was
retained in a private temporary recovery file. Other bindings were not reloaded.

Cancellation refinement implemented: only status 130 is normalized in the tmux
shortcut launcher. All seven tmux tests pass, including Escape/Ctrl-C at the
category, app and binding stages, direct CLI cancellation, and preserved genuine
failure statuses/diagnostics. The live binding was updated after these checks,
with its previous value retained in a private temporary recovery file.

- Key browser: 20 isolated tests passed, including invoking Bash/Zsh maps,
  configuration parsing, live precedence, notation, JSON, native Neovim mapping
  snapshots, category navigation, caller snapshot retention, menu sizing,
  45% previews, field colors and popup color policy.
- Tmux: five tests passed, including private-server notes/prefixes, missing
  dependencies, 40/80/120-column output and a real FZF popup launched by the
  repository binding.
- ZLE: both Ctrl-H and DEL passed after normal-to-insert transitions through
  `i` and `a`, including repeated local reloads and callback deduplication.
- Shared regressions: resource presentation (15), file pickers (19), Bash
  dispatcher (24), shell environment (9), and native controller (13 passed,
  one native PowerShell skip).
- The broader Zsh suite passed 26 of 29 tests. Three existing failures concern
  MSYS platform expectations, missing optional-tool fixture preparation, and
  historical FZF/theme fixture paths. All three reproduce with the original
  integration file in owned fixtures; they are outside this change.
- Both command validators accepted 137 extensions. ShellCheck, shell syntax,
  Neovim StyLua, whitespace and documentation-link checks passed.

Seven alternating warm startup samples in owned public fixtures measured Bash
medians of 318.5 ms before / 318.0 ms after and Zsh 217.3 ms / 218.3 ms. These are
local noisy measurements, not cross-platform performance guarantees. Startup
installs the adapter function without querying maps or launching providers.

Native PowerShell 5.1/7 PSReadLine capture, native Windows preview execution,
GitHub wiki rendering and the user's actual keyboard remain named acceptance
checks. Existing running shells and complete tmux configuration were not reloaded. No commits
or publication are part of this change.
