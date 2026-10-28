# Bundled blastoff in Dots

Follow ../../AGENTS.md first. This directory is first-party Dots source; the original standalone-repository instructions below are historical where they concern release packaging or installation. Public install/uninstall scripts delegate to Dots. Do not run legacy standalone installers against the live machine. Dots integration tests live in ../../tools/test_bundled_apps.py. Original release checksums and device evidence describe the imported revision, not this Dots tree.

# Blastoff agent instructions

Read `docs/PROGRAMMING-PREFERENCES.md`, `docs/CLI-CONTRACT.md`, and
`docs/IMPLEMENTATION-PLAN.md` before changing behavior. Read `docs/STATUS.md`
for evidence and unfinished platform gates. Current user instructions win.

## Priorities

1. Protect user data and keep operations predictable.
2. Keep startup and common operations fast; measure instead of guessing.
3. Match the Bash and native PowerShell command contract.
4. Provide colorful, compact human output and clean machine output.
5. Ship help, Bash/Zsh/Fish/PowerShell completion, man page, install/uninstall, version,
   changelog, checksums, tests and practical documentation together.

The user selected one shared Python 3.11+ core with thin Bash/PowerShell entry
points. Do not introduce separate implementations of the same behavior.
Do not add Node, proot, network services, telemetry or required picker tools.

## Repository and reference sources

The source now lives in the `plugins/blastoff/` directory of Dots. The original standalone checkout remains untouched.
Inspect its existing Git status, tracked files, AGENTS files and docs first.
Reference scripts/module live in `.local/src`; branding work lives in
`.local/logo`. These are sources to inspect, not paths to execute automatically.
The supplied archive is a review workspace, not a checkout of that repository.
Never assume it represents main or copy it over existing work blindly.

## File safety

- Starship's active config is nonempty `$STARSHIP_CONFIG`, otherwise
  `~/.config/starship.toml`, even if the override does not exist yet.
- Store themes in `~/.config/blastoff/themes` and modules in
  `~/.config/blastoff/modules`; `BLASTOFF_HOME` overrides only the storage root.
- Resolve storage-root directory links once; aliases share the canonical lock.
  Keep linked storage children and active-config parent write protections strict.
- Help, version, list, doctor and completions must not create files/directories.
- Validate UTF-8 TOML before a mutation. Keep unrelated module settings intact.
- Back up replaced/deleted content (explicit backup delete permanently removes
  its selected pairs; do not create backups of backups). Stage in the destination directory and
  replace atomically. Detect external edits, locks and unsafe destinations.
- Preserve active-file symlinks by default: pin and guard the link chain, lock
  and atomically update its regular target. Keep parent-directory write protections.
  `--replace-link` explicitly records and replaces the link, leaving its target alone.
- Never break a lock automatically, recursively delete user directories or
  silently migrate legacy paths. Migration copies from an explicit source.
- Never run a theme's custom commands, use eval, or render a live prompt as
  validation. Generic TOML validity is not full Starship schema validation.
- No installs, profile edits, PATH changes, live-config changes or Git pushes
  as part of tests. All fixture writes belong in isolated temporary roots.

## Working style

Make a concrete plan, then implement bounded slices with acceptance checks.
Continue routine reversible work without repeated confirmation. Ask only for
missing decisions that block safe progress or genuinely destructive actions
outside the user's instructions. Inspect diffs and preserve unrelated changes.
Do not commit/push the user's repository without being asked. Do not rewrite
history or move release tags. Report what changed, why, actual tests and gaps.

Prefer `rg`, explicit argument arrays and focused helpers. Keep optional tools
optional. Do not build fake safety from regex-only TOML edits. All entry points
must forward arguments, streams, cancellation and exit status predictably.
The PowerShell function uses `$LASTEXITCODE`; a shell script returns the native
process status. Never claim that a function sets the parent shell process code.

## Verification

Run `python3 -m unittest discover -s tests -v` on Linux/Termux or
`py -3 -m unittest discover -s tests -v` on Windows.
Run `bash -n bin/blastoff scripts/install.sh completions/blastoff.bash`,
`zsh -n completions/blastoff.zsh`, `fish -n completions/blastoff.fish`, and
`groff -Tutf8 -man man/blastoff.1` where the native tool exists.
Use `tests/parity.ps1` to compare PowerShell output/exit status with the core.
Run `python3 scripts/benchmark.py`; distinguish Python, Bash and PowerShell
startup. Record machine, host OS, runtime and sample count.
Rebuild checksums using `python3 scripts/package.py` after changes.
Use `scripts/verify.py` to check the source archive before installing.
Treat native Termux and native Windows runs as separate release gates.
A Linux run or fake Starship fixture does not prove either gate.

## 0.1.8 workflow

Read docs/RECOVERY.md and decisions/0002-provenance-and-interactive-editing.md under
docs for staged editing and provenance. Keep history separate from exact matches;
a pending state marker cannot authorize implicit overwrite. Never discard failed
editor output. Dry-run must not create locks, caches, backups or tracking data.
Use fancy Unicode by default, explicit --fzf for user styling, and Ctrl-X source previews; never
render a prompt as validation. Verify actual four-shell completion contexts.
Reconcile commands, flags, defaults, prompts, examples, versions and support claims
across all maintained docs before final checksum/package generation. Preserve
historical evidence and leave native Windows/human visuals unverified until run.

## Human output and PowerShell follow-up

Ordinary commands default to readable human output, including when redirected.
JSON requires explicit --json; keep schemas stable and stdout undecorated.
Diagnostics/verbose go to stderr. Raw completion/TOML exceptions stay raw.
Do not reintroduce a shared emitter that defaults to JSON without a human message.
Preserve exported fzf/bat settings and custom bat caches; never source profiles or
evaluate aliases to discover configuration. Fixture isolation and real-tool
appearance checks are distinct. Manual acceptance is paused at backup deletion
(step 5); preceding passes and a live review installation must not be inferred.
Root PowerShell lifecycle uses CurrentUser ownership, WhatIf and the shared engine.
Import/static completion must not launch tools or scan storage. See POWERSHELL.md
under docs for the parity matrix, platform boundaries and separate native gates.

## Field readability

Current/theme-list/save/backup-list/doctor human reports use the shared Dots renderer and presentation controls. Keep ordinary redirected output and all JSON/raw/completion contracts intact. Help artwork and application pickers retain their own styling. Sanitize data before styling, reset each segment, and keep the same understandable human layout without color.

Keep source prefixes such as local: and preset: quieter than names: use muted prefixes, blue identities, green current markers and yellow modified/history markers in Dots reports.
Keep textual current/last-loaded markers meaningful without color; edited origin
history must never be presented as an exact current-content match.
