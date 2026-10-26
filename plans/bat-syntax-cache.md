# Bat custom syntax caches

Status: implemented; Termux verification and the authorized live refresh completed
2026-10-26. Native Windows consumer acceptance remains pending.

## Accepted behavior

Include the user's custom `.sublime-syntax` definitions in every Dots-generated Bat cache, preserving the selected theme and Bat built-ins. The user selected a permanent implementation fix plus a journaled refresh of the current theme after verification. Preserve the existing normal Bat configuration/cache and its Dots theme connector. The active generation inspected during planning contained only `bat-source/themes/Dots.tmTheme`; its cache omitted the repository's valid G-code syntax. An isolated build with both assets listed G-code and Dots and rendered colored G-code successfully.

Both the Bash and native Python/PowerShell publishers share configuration discovery, bounded recursive input snapshots and compilation. Resolve source assets through installed Bat's `--config-dir` before staging overrides, honoring `BAT_CONFIG_DIR` and native platform defaults independently of `BAT_CONFIG_PATH`. Support linked configuration directories and linked syntax files/directories with cycle detection, retaining ordinary file snapshots under `bat-source/syntaxes`. Only `.sublime-syntax` files are copied; VCS internals are excluded. Reject unreadable/broken/invalid inputs before activation. Bound input reads to 2 MiB per file, 64 MiB total, 16,384 directory entries and 64 directory levels.

Publication/setup fingerprints include source paths, relative syntax names/content and compiler identity/version. They detect additions, removals, same-size/timestamp edits and compiler changes. Syntax changes while preparing a generation are refused before publication. Shell-initialization fingerprints remain separate: no custom-syntax scans or Bat queries/builds are added to startup or prompts. Bat remains optional. No new public CLI flag or settings schema is introduced.

## Acceptance

Test both publishers with owned home/config/state/cache roots, source overrides/defaults, linked/nested inputs, spaces/Unicode, missing syntax directories and missing Bat. Verify Dots plus G-code and built-in languages, snapshots independent of source edits, repeated refresh idempotence, same-metadata changes, add/remove, invalid syntax, link cycles, special files and source drift during compilation. Failure must retain the previous generation. Cover inactive setup and shell-only initialization boundaries, focused publication/recovery and file-color regressions. Follow the [presentation gate](README.md#presentation-gate-for-every-plan), preserving undecorated machine output and bounded phase messages. Native Windows engine/app execution remains pending if unavailable; native controller fixtures do not establish Windows acceptance.

After focused tests, update source documentation and regenerate/check the local wiki. Preview and refresh the current theme through the existing journaled workflow, preserve the selected identity, retain recovery state, and verify active cache contents plus shell generation adoption. Preserve earlier Yazi/Codex/Zsh work and the unrelated Yazi layout edit. No commits or pushes are included.

## Evidence

`tools/test_bat_cache.py` passed all 14 checks. The shared syntax suite passed
6 checks, the explicitly selected `FileColors` suite passed 11, and the native
CLI suite passed 13 with one unavailable PowerShell runtime check skipped.
The native CLI run cleared inherited `YAZI_CONFIG_HOME` in addition to its fixture
isolation. Six selected theme cases passed: atomic publication/idempotence,
snapshot immutability, failed-publication rollback, first-selection rollback/drift,
all 15 injected flush failure boundaries, and Zsh prompt refresh/hooks.
These are Termux and shared-controller results; Windows defaults, link privileges,
PowerShell 5.1/7 and native consumers still require acceptance on Windows.

Bash syntax, relative Markdown links and source/wiki whitespace checks passed.
ShellCheck reported no new diagnostics relative to HEAD in the three changed
Bash files; existing source/global-variable/generated-shell warnings remain.
The local wiki was rebuilt with retained transaction
`831d0b0dd2934cedb51f7107e74009e9` and `dots wiki check` reported healthy.

The current selection was previewed with
`dots theme set catppuccin-mocha --dry-run` (`refresh` does not accept `--dry-run`),
then refreshed through `dots theme refresh`. Committed generation `g.QpnFRrW1`
retains previous generation `g.d2gX2tzQ` and the `catppuccin-mocha` selection.
Its staged G-code file matches the source byte-for-byte; Bat lists G-code,
Python and Dots, and renders a G-code sample with four distinct RGB colors.
The generated Zsh export and Delta link address the new cache. Normal Bat cache
file sizes, modification times and inode identities are unchanged, and the
existing Dots theme source connector is preserved. Enabled GTK/Starship hooks
reported unchanged output. No commits or pushes were made.
