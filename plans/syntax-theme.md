# Shared syntax theme reference adaptation

**Status: Implemented; local acceptance passed with the limits below.**

Adapt the 186 rules from SchweGELBin/catppuccin-bat-sub commit `ccf194fdc9322d3566a7a178817763434c0dd088` into the Dots shared tmTheme. Preserve reference scopes, ordering and font styles, map colors to existing Dots tokens, retain opaque Dots global settings and generic diagnostic/diff fallbacks, and honor resolved Git colors with concrete foreground fallbacks for `reset`.

## Acceptance

- [x] Pinned source attribution and MIT notice; dynamic template with no fixed Mocha colors.
- [x] Shared derived Git tokens and equivalent Bash/native rendering, including custom colors/reset.
- [x] All selectable palettes parse without unresolved tokens; Yazi copies match the shared output.
- [x] Actual bat cache and token colors on dark/light samples, supported attributes, and terminal file preview/raw contracts in owned roots.
- [x] Selected override, fingerprint, connector, idempotence and rollback regressions.
- [x] Documentation and focused test entry point synchronized; Markdown links and diff checks pass.

Template source only: no live publication, cache rebuild, activation, commit or push. Preserve unrelated edits. Native Windows/PowerShell consumers and terminal rendering require separate acceptance; local Python renderer tests establish shared-controller parity only. Use explicitly selected test classes/methods to avoid inherited-suite expansion. The existing Vivid/Zsh round-trip failure and 40-second all-family Neovim timeout were previously reproduced against HEAD and are outside this template update.


## Verification

- Six focused cases passed: reference scope/style preservation, all-selectable-palette Bash/native rendering and Yazi byte equality, Git overrides/reset, real bat token colors and attributes, template fingerprint/idempotence, and direct Delta cache consumption.
- Native Termux bat 0.26.1 checks cover Python, Rust, JavaScript, Bash, JSON, YAML, Markdown and diff text on Catppuccin Mocha and Latte. Bold, explicitly enabled italic text and style resets were observed. Reference strikethrough declarations are preserved; their visible rendering is not claimed for every consumer.
- Delta 0.20.1 loaded the generated Dots cache and produced the expected syntax foregrounds with user Git configuration disabled. The two older `GitTheme` cases could not initialize because they reference absent `config/git/gitppuccin`; that file is also absent from HEAD. The direct syntax test supplies relevant consumer evidence without changing the unrelated fixture.
- Fifteen selected regressions passed: the full `FileColors` class, two explicit Codex connector/override/rollback cases, Leaf's two-connector backup/idempotence/restore case, and real terminal highlighting through both command frontends.
- Compact key/value XML retains the identical parsed theme and keeps the source at 64,133 bytes, below the existing 64 KiB preview bound. Exact generated/source raw previews pass. No inspection limit or data-output contract was changed.
- Source attribution and the MIT notice are included. Documentation links and `git diff --check` pass. Live inspection still reports the original 70-rule published theme; the edited source contains 193 rules. No live refresh or activation was performed.

Native Windows PowerShell and application rendering remain pending. The source uses existing platform-neutral template expansion and the shared Git-token helper; Termux tests establish Bash/Python output parity, not native Windows visual acceptance.
