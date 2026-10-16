# Current Dots theme color arrays

**Status: Implemented and activated on native Termux, 2026-10-16.**

Generate Bash/Zsh color arrays from the native palette plus resolved Dots colors, with Dots values taking precedence. Include semantic roles, terminal aliases and native extras; exclude mode metadata. Preserve every existing format and fixed Catppuccin flavor array. Keep native `dots_palette`, semantic `dots_roles`, and Fish interfaces unchanged.

Generate and cache declarations at publication, tracking owned unprefixed names so switching removes obsolete colors. Migrate legacy Catppuccin ownership on first reload. Reject unsafe/reserved shell variable names before publication. Preserve unrelated work and the selected local palette; refresh locally after isolated acceptance.

Acceptance: native Bash/Zsh dark/light, native/generic/pywal palettes, resolved color and derived-format equality, compatibility digest, stale-name cleanup, unsafe-name rejection, failed publication, idempotence and prompt-driven refresh. Run affected theme/workflow/file-theme/shell suites, syntax and documentation checks; compare generation and warm startup timings. Follow the [presentation gate](../docs/presentation.md#acceptance-gate), preserving data output and existing human views.


## Verification and rollout

- Shared-theme checks: 31 cases passed across the full run and focused retries. The all-family Neovim case still exceeds its existing 40-second limit; the focused editor case passes. The initial Rose Pine `_nc` rejection was corrected and covered alongside Kanagawa mixed-case names. Cleanup assertions explicitly inspect associative-array fields in both Bash and Zsh.
- Workflow: 27 cases, one optional skip. Vivid/FSH: 11 passed. Zsh: 22 passed. Shared shells: 19 passed. Shell initialization: 30 cases pass with seven skips after a process-local test harness exclusion of unavailable Xonsh. The unmodified run fails because its installed launcher names a missing Python 3.13 interpreter; no package or runner changes were made for that unrelated issue.
- Native isolated Bash and Zsh PTYs verified prompt-driven Mocha → Tokyo Night → Latte switching, resolved `blue`/`hint`, obsolete-color removal and retained fixed Mocha aliases. Fixture snapshots use explicit clobber redirection because the public Zsh config enables `noclobber`.
- Five alternating warm Zsh startup pairs measured medians of 1.874 s before and 2.013 s after, with overlapping ranges. Uncached Mocha initialization generation measured 0.618 s versus 0.771 s: the expanded array/format set adds generation work, which remains cached. Isolated sourcing (three runs of 50 loads) measured 8.97 ms versus 12.17 ms per load. Unchanged prompts still bypass initialization.
- Local `dots theme refresh` retained Catppuccin Mocha and published generation `g.FNYDlfPU`. Clean Bash and Zsh processes verified 70 current-theme color arrays, `blue=#89b4fa`, `hint=#94e2d5`, `background=#1e1e2e`, and the unchanged fixed Latte blue. Existing shell hooks load the new generation at the next prompt.
- Syntax and whitespace checks pass. ShellCheck reports only the existing source-resolution and guard findings. Documentation-link validation still reports the pre-existing missing Yazi symlink-plugin README. Native desktop/WSL/Windows behavior remains unverified. No commit or push was made.

Follow-up, 2026-10-16: Bash/Zsh initialization now also defines global `rst` and `RST` scalars as SGR reset (`ESC[0m`). Matching readonly values remain sourceable, and `rst` is reserved against color-name collisions. The format/native-palette and legacy-initialization cases pass, including repeated sourcing with readonly reset variables. Local publication was refreshed and both four-byte values verified.
