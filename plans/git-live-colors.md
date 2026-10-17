# Owned repositories and live Yazi color references

Status: Implemented and deployed on native Termux. Owner approved implementation, standalone plugin publication and package-manager update.

- Add `git.repo_owned` (yellow, bold); make `git.repo` magenta, bold.
- Use cached local fetch-remote ownership for colored Git CLI identities without changing operation policy or JSON.
- Expose callable `dots.colors` references resolved at setup and refresh; reuse published JSON/Lua exports.
- Apply shared Git styles to header defaults and per-file indicators; preserve explicit overrides and last-good snapshots.
- Convert personal UI color configuration after isolated validation and remote package update.
- Validate Lua, private native Yazi sessions, package upgrade, Git rendering and theme publication.
- Publish only standalone plugin; upgrade through `ya pkg`, then refresh the selected theme.

Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate). Tests own all temporary home, config, state and DDS roots. Installed package files are never manually patched; no discard or hash rewriting.

Implementation is complete. Focused verification passed: seven Git style tests, ten file-color/publication tests, Lua component/reference/style fixtures, 350 GNU ls comparisons, isolated native Yazi theme refresh and the copied personal config, and offline package add/upgrade/refusal. Native hard-link creation is unavailable on this filesystem; Lua metadata coverage remains. All 27 Git operation and 24 Bash dispatcher regressions passed. ShellCheck, Lua syntax, whitespace and relative Markdown checks passed.

Deployment: standalone commit `be61895` was pushed to `5nik7/dots.yazi` main. Targeted `ya pkg upgrade 5nik7/dots` and repeated install succeeded; all 15 runtime Lua modules match source. The package manager wrote revision/hash, with no installed-file edits, discard or manual hash changes. HTTPS fetch was blocked by a proxy 403; a command-scoped Git URL rewrite used the verified SSH remote without persisting transport settings. The tested personal configuration was activated after package update.

Live refresh retained `catppuccin-mocha` (dark), publishing 18 Git roles; ordinary repositories resolve to `#f5c2e7`, owned repositories to `#f9e2af`. Existing unrelated modified files retained their recorded content hashes. Restart existing Yazi sessions once for the new plugin code; later palette refreshes are live. Parent Dots changes remain uncommitted. Native Windows and pixel-perfect font/terminal equivalence remain unverified.
