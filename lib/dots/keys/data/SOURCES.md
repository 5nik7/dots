# Bundled key references

These files are inert reference data for `dots keys`, not application configuration. Browsing never downloads data or launches an application. Bundled rows identify configured defaults; they do not certify the installed version, feature availability, or active runtime keymap.

## Yazi

`yazi-default.toml` is the complete 254-binding shipped preset from [sxyazi/yazi at 8dd895c695a5950330c2623eb43debf323b60654](https://github.com/sxyazi/yazi/blob/8dd895c695a5950330c2623eb43debf323b60654/yazi-config/preset/keymap-default.toml), inspected on 2026-10-25. The upstream MIT attribution is retained in `LICENSE.yazi`. All eight contexts are included. The provider compares the first two strokes when merging tables, matching that revision's `yazi-config/src/keymap/section.rs`.

To refresh, resolve the requested upstream tag to a commit, review the complete preset and merge semantics, replace the data with that commit's preset, and update this revision and the per-context completeness assertions in `tools/test_keys_defaults.py`. Do not refresh during ordinary CLI execution.

## Codex CLI

`codex-defaults.json` derives from [OpenAI Codex CLI 0.164.0](https://github.com/openai/codex/tree/6aaac694803004a63c6f393d153c96d22521a6b9), commit `6aaac694803004a63c6f393d153c96d22521a6b9` (tag `rust-v0.164.0`), inspected on 2026-10-25. The upstream Apache 2.0 license is retained in `LICENSE.codex`. Dots transforms the Rust declarations into reference data and adds contextual explanations; it does not ship or execute the Rust implementation.

The import covers every action in `codex-rs/tui/src/keymap/bindings.rs`, including actions with no default key, plus the shared leader: 156 actions and 234 default bindings. Defaults come from `keymap.rs`, `keymap/vim_search.rs`, `keymap/chords.rs`, `keymap/leader.rs`, and `keymap/chords/quick_dial_defaults.rs`; descriptions and accepted configuration slots come from `codex-rs/config/src/tui_keymap.rs`. Input hashes are recorded in the catalog.

Reproduce the action catalog from a local checkout of that commit, without running Codex or using the network:

```sh
python3 -B tools/import_codex_keys.py /path/to/codex --output lib/dots/keys/data/codex-defaults.json
```

`codex-contexts.json` separately records fixed contextual controls and uses `binding_from` for controls that inherit configurable actions. Each entry names the audited upstream handler. This covers reserved chat controls, prompt history/search, completion popups, attachments, Vim transitions/search input, approvals, questions, MCP forms, settings, key capture, warnings, hooks, feedback, app connections, resume/fork, external-writer views, transcript selection/copy/search, activity focus and Unix suspension. Normal typing and dynamically assigned item-specific accelerators are not enumerated. Runtime conflict validation, terminal event aliases, selected features and active focus can affect availability. The catalog is a reference, not a second Codex key dispatcher.

For an upgrade, audit the central inventory and its resolver together with the named supplemental handlers; update version/revision, descriptions, fixed bindings and tests together. Arrays in user configuration are alternatives; a space inside an entry denotes a two-stroke chord. Only composer `submit`, `queue`, and `toggle_shortcuts` inherit global action settings in this revision. Preserve explicit empty arrays, raw notation and source attribution when refreshing.
