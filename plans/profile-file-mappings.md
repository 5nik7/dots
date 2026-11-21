# Profile file mappings

The [file catalog](../docs/files.md#ownership-and-formats) takes portable source–target declarations from the active profile layers. Each platform ships a flat array. The Termux profile retains the shortened resource IDs and the edited configuration selection.

The [Files workflows](../docs/files.md#add-link-and-find) cover active-profile and global imports, explicit linking, and reviewed discovery. Correct pre-existing links retain their identities and uninstall ownership. Both files and theme commands use the stable publication path. Yazi’s flavor directory is a single mapping under the app’s managed config root on each platform. Windows uses its native Yazi location and supported overrides.

## Delivery and acceptance

- Files owns the commands. The Files menu includes Find, and Config shows the profile that declares each mapping. Existing backup, presentation and menu preferences cover the new actions.
- Setup, publication and inspection share the profile's theme mappings. Fixtures exercise first publication, migration of Yazi’s former two file links into the `theme:yazi` directory link, backup, cancellation, drift, rollback and undo.
- Bash and the native controller share route metadata and six-shell completion grammar. Files JSON and narrow terminal output have separate checks.
- Find accepts recursive roots as positional paths or repeatable `--path DIR` options. Its menu entry, backup and presentation preferences, and installer routing still apply. Roots and category corrections are per-invocation choices. The catalog checks new filename-based IDs against existing mappings and reserved names.
- The existing Add picker groups scan results by action and shows one compact path per row. The Files menu and both shell frontends use this picker. Existing picker colors, icons, previews, approval and backup preferences cover both Add and Remove. Removing a replaced mapping or one with a deleted repository source affects profile metadata only. The installer, shell startup and completion grammar need no changes for these workflows.
- The canonical guides, manual and local wiki describe the new commands. The root README’s first commands and installation entry points continue to apply.

## Profile maintenance

The `files relink`, `files prune` and `files sync` routes share the selected profile and the existing file transaction store. Bare invocation previews. `--yes` applies eligible work and `-i` or `--interactive` reviews candidates individually before a final confirmation. Sync evaluates link ownership after the selected removals and retains one undo point for the combined batch.

- **Files menu** — The three entries open interactive review with the shared presentation and confirmation adapter.
- **Configuration** — Existing profile mappings, backup locations, colors and icons supply the inputs. Selection and filters apply to a single invocation.
- **Delivery** — Bash and the native PowerShell bridge share the Python controller and static help. All six shell completion protocols cover the options and filters. The manual and Wiki describe the commands. The installer already exposes the command framework. The root README’s setup and first commands still apply.
- **Acceptance** — Isolated Termux tests cover previews at 40, 80 and 120 columns, selection and cancellation, healthy links, byte-identical and edited files, deleted sources, inherited rows, conflicting claims, stale plans, repeat application, rollback and undo. Native Windows PowerShell 5.1/7, desktop Linux and WSL execution require their respective hosts.

## Catalog listing

Both `files list` and `files ls` use the same read-only renderer on Bash and native PowerShell. Below 50 columns, the short view stacks linked files and indents the destination arrow by two spaces. The stacked arrow is `󱞩` with icons or `->` in plain text. Linked directories stay inline when they fit, with one source icon. Exceptional statuses have bracketed headings. With grouping enabled, stashed IDs appear together at the end. Explicit sorting or disabled grouping preserves the selected order. The wide layout starts at 50 columns. Link arrows use the theme’s `dark_foreground` at every width.

- **Configuration** — The Config browser validates `apps.files.list_view` and `apps.files.group_by_status`. Terminal width selects the narrow layout automatically. The listing uses the existing theme colors, file styles and `icons.status.stashed`. Preferences apply on the next listing.
- **Menu** — The Files menu’s List entry opens the selected view. Both spellings open the same report.
- **Delivery** — Verify the 49/50-column transition together with 40, 80 and 120 cells, long basenames, Unicode, ambiguous path pairs, plain output, explicit ordering and grouped stashed IDs. Check the existing tab-separated and JSON contracts, both dispatchers and profile settings. Completion covers the alias, flags, view names and filters. The installer exposes both commands through the existing dispatcher. Setup and first commands in the root README still apply. Native Windows, Linux and WSL host checks require their respective runtimes.

The narrow layout passed ten renderer cases and eleven catalog cases on Termux, including real terminal checks at 49 and 50 columns. The active theme’s `dark_foreground` matched the emitted arrow color for stacked files, inline directories and wide rows. The original listing also passed twenty typed-configuration cases. Seven existing resource-presentation cases previously failed on both the working tree and revision `ff43d24` with the same tests affected.

## Verification

The four shipped profiles validate locally, including Termux’s hand-edited mappings and generated theme links. Isolated tests cover both source scopes, mixed link operands, repeat discovery, legacy IDs, inherited declarations, publication switches, first install, rollback and uninstall. The fresh default installer passed first install, repeat and uninstall for the Termux profile and a WSL profile simulation on the same Termux host. Native Windows PowerShell 5.1/7, WSL, and desktop Linux host checks remain pending.

A three-run Termux benchmark measured catalog construction and listing over 1,000 existing sources with absent destinations. Median elapsed time was 713 ms with flat declarations and 622 ms with grouped declarations. At 100 rows it was 145 ms and 98 ms, respectively. The flat reader checks the source template, owning repository, and ancestor safety when it reads a declaration.

The local wiki export passes its source and checkout consistency checks. Two standalone Wiki browser tests also fail on the pre-change revision because their mocks target the previous selector. The failures concern terminal browsing, outside the file mapping and export changes.
