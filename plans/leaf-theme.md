# Leaf with Dots UI and syntax colors

Status: Complete on Termux; native Windows/Linux/WSL acceptance remains pending. Owner approved the template, external syntax support based on Leaf 1.28.2, replacement of the existing executable with retained recovery, and local activation.

- [x] Add and verify Leaf external `.tmTheme` loading in a separate checkout; retain a reproducible source patch and build instructions.
- [x] Render the semantic Leaf template in Bash/native Python and publish both UI and shared bat syntax connectors through existing journals.
- [x] Cover all palettes, path/override contracts, lifecycle recovery and real inline/TUI colors in isolated roots; run shared regressions.
- [x] Update documentation, preview and publish the existing selection, then journal executable/config replacement and verify activation.

The reference TOML and unrelated edits remain intact. No commit/push/upstream submission is authorized. Windows uses APPDATA/leaf, native Rust/Python and the existing link adapter; native Windows PowerShell 5.1/7, Linux and WSL runtime acceptance remains pending where unavailable. Existing operation views follow the [presentation gate](README.md#presentation-gate-for-every-plan).

Source baseline: RivoLink/leaf tag 1.28.2, commit 140e55858c98df50ba52fc4ab7bad277a31ab73f. Custom version: 1.28.2+dots.1. Syntax file paths resolve relative to the containing theme/config, load once per process, and fail explicitly when unreadable or malformed. Built-in names remain supported. Dots reuses bat.tmTheme; no duplicate syntax palette or automatic theme-file watcher is added.


## Verification

- All 34 selectable palettes render matching Bash/Python Leaf TOML with every reference color field and no unresolved tokens.
- Seven Dots fixture tests passed for paths, overrides, publication, shared-parent creation, interruption recovery, drift refusal and owned directory links. Both real-consumer cases also passed: actual inline token RGB and dark/light PTYs at 40/80/120 columns, including picker preview/cancel, resize and document reload.
- Leaf's 441 Rust tests passed; Clippy passed with `--all-targets --all-features -- -D warnings`. The final source revision, including normalized named-theme lookup, passed both checks again; the locked optimized build succeeded.
- The retained patch applies to the exact upstream baseline. The reference TOML is unchanged.
- Shared regressions passed: file colors 11/11; native controller 13 passed with 1 unavailable PowerShell check skipped; installation 25/25; adapters 5 passed with 4 unavailable native checks skipped; Television publication 7/7; selected theme publication 6/6; selected workflow 4/4. Relative Markdown links and whitespace checks passed.
- Published the existing Catppuccin Mocha selection and activated `leaf 1.28.2+dots.1` with only the config selector changed. Live inline output matched Dots comment/string RGB values. Original binary/config recovery payloads are retained in the file transaction store; the public undo dry-run passed.
- Automated native consumer evidence is Termux-only. Human visual review and native Windows PowerShell 5.1/7, Linux and WSL runtime acceptance are not claimed.
