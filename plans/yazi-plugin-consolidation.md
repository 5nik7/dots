# Yazi plugin consolidation

**Status: Implemented; native Termux verification complete, interactive visual comparison deferred**

## Accepted design

Bundle the nine plugins initialized by `config/yazi/init.lua` plus the keymap's pane toggles into `config/yazi/plugins/dots.yazi`. Rename the bundled Yatline renderer and extension global to Dotline. Keep one setup table in `init.lua`, retaining current options. Preserve original plugin folders inactive for reference, unrelated package dependencies, existing user edits, and project data/events. No commits, publication, package installation, or changes to the paused Go scope are included.

The [plugin README](../config/yazi/plugins/dots.yazi/README.md) owns the feature inventory and interfaces. The bundle uses Yazi-relative module imports and independent module state; its dispatcher forwards project, pane, and internal refresh actions, while its fetch entry forwards Git jobs. Pane updates use a UI synchronization block. Personal configuration, shortcuts, and fetcher rules address `dots`.

Repository naming and Git-head status are combined in `githead.lua` with one event subscription set and request generation. The `githead` display component joins repository name and status with a plain space in one colored group, and the active section contains only that component. Repository styling options live under `githead`; the separate bundled `repo.lua` and dispatch route are removed. The original standalone `dots-repo.yazi` remains untouched.

The bundled hovered-path component is named `hover.lua`, with a `hover` setup table and colored getter. Its regression runner is `test-hover.lua`. Module loading, the active header, native probe, and documentation use those names together; path fitting, icons, colors, and symlink-target behavior are preserved. The inactive standalone symlink plugins retain their original names and interfaces.

## Acceptance and evidence

- [x] Consolidate sources and JSON helper; retain original license notices.
- [x] Rename the renderer to Dotline and migrate bundled getters.
- [x] Switch setup, keymaps, fetchers, and merged package dependencies.
- [x] Document setup, options, commands, persistence, attribution, and verification.
- [x] Lua fixtures: setup order, command dispatch, argument preservation, Git fetch forwarding, pane restoration, shared Git refresh/stale-result rejection, and symlink width/control-character/path cases.
- [x] Native Yazi 26.9.1 on Termux: isolated bundle-only startup, distinct module state, Git callbacks and fetching, project save/load/last/delete/delete-all and merge event dispatch, folder rules, pane shortcuts, narrow/wide redraw, and clean exit without logged errors.
- [ ] Owner visual comparison in their normal terminal/font; automated redraw checks do not establish pixel-perfect equivalence.

The native test owns temporary home/config/state/cache/data/runtime roots, Git configuration/repository, and DDS socket directory. It never reads or changes live project data. Other platforms remain unverified; Windows-path Lua fixtures are simulated evidence.

## Presentation gate

Apply the [presentation contract](../docs/presentation.md#acceptance-gate) to the relevant application UI boundaries: retain existing styles, semantic colors, labels, icons, separators, and layout; test symlink fitting and control-character sanitization and native 40/80/160-column redraws. The application keeps Yazi's theme contract. CLI stdout/JSON/color-mode and Gum gates do not apply because no Dots CLI view or machine-output format changes. Interactive visual comparison is explicitly deferred above.
