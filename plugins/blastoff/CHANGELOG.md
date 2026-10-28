# Changelog

## 0.1.12 — default Starship path and preserved config links

- Preserve active-file symlinks during apply, module load, edit and restore; guard
  the link chain and physical target, and share physical-target locks across aliases.
- Keep explicit `--replace-link` conversion and unsafe-parent/library protections.
- Reuse canonical-target provenance when switching to Starship's default path;
  retain legacy alias records as recovery evidence after successful mutations.
- Add `resolved_config` to current/doctor without changing the configured path field.

## 0.1.11 — installer host detection and frontend parity

- Identify Termux, WSL, Linux, Windows and other hosts in lifecycle plans; use
  native defaults and reject incompatible Bash/Python combinations before writes.
- Recognize MSYS2/Git Bash and Cygwin at the Bash boundary and direct users to
  the native PowerShell installer without launching it automatically.
- Preserve exact legacy PowerShell installer arguments through the shared transport;
  consistently reject batch runtime candidates and report missing Python with status 3.
- Repair native completion test setup, run PowerShell parity from unittest when
  available, and expand argument-mode, state, lifecycle and platform coverage.
- Keep shared application JSON, storage and ownership formats unchanged. Native
  Windows/PowerShell/WSL and interactive acceptance remain separate evidence gates.

## 0.1.10 — theme-list identity and contrast

- Show identical full help for bare blastoff, -h and --help. Global flags without
  a command also show help; explicit JSON retains the existing welcome object.
- Dim local:/preset: prefixes and highlight names using shared Blastoff accents.
- Identify current tracked themes; retain modified origins and report changed or
  unavailable sources without guessing from a full library scan.
- Keep JSON unchanged, inspection read-only, and both frontends on the shared core.
- Update list help, documentation, tests and review artifacts; actual native and
  human acceptance evidence remains in STATUS.md.

## 0.1.9 — backup-list readability

- Distinguish backup IDs, labels, values and separators with shared accents.
- Separate records and move Size to its own line on narrow terminals.
- Parse known timestamps as UTC and reuse inspected exact byte sizes.
- Preserve JSON, plain output, diagnostics, metadata and read-only behavior.
- Update output guidelines, examples and validation evidence; native PowerShell
  and human appearance remain separate acceptance gates.

## 0.1.8 — review follow-up

- Fancy Unicode is the shared browser default; --fzf / pick fzf select basic user
  presentation. Preserve ASCII, responsive Ctrl-X previews and safe multiselection.
- Fix unquoted fzf hex-color parsing and bat config/theme/cache inheritance;
  distinguish isolated fixtures from real-configuration appearance checks.
- Make readable human output explicit throughout, including backup metadata;
  JSON remains opt-in with stable schemas and stderr diagnostics.
- Add PowerShell argv transport, bounded offline completion and root CurrentUser
  install/uninstall with WhatIf, profile backups and independent owned resources.
- Add native-session/lifecycle/performance harnesses and reconcile project surfaces.
  Actual results and unavailable native/human gates are recorded in STATUS.md.


## 0.1.7 — editing, provenance and backup cleanup

- Add verbose stderr diagnostics and no-write dry-run across core mutations.
- Track last-loaded origin independently from exact matches; interactive theme
  save uses y/as/N, validates destination baselines and supports local save-as.
- Add staged theme editing with editor selection/waiting, pre-edit backups,
  concurrent-change checks and retained failed/invalid work.
- Add permanent backup deletion by IDs, frozen all-set or fzf multi-selection,
  default-No confirmation, explicit noninteractive authorization and alias escaping.
- Make basic fzf the default; preserve reviewed user options, offer fancy Unicode/
  ASCII styling, responsive visible Ctrl-X previews and bat/plain source display.
- Add read-only module show/browser; update all four completions, help, manual,
  lifecycle payload verification and current/historical documentation boundaries.
- Native Windows remains deferred. Rendered prompt samples are deliberately absent;
  native fzf and human visual results must be read from STATUS.md, not inferred.

## 0.1.6 — linked dotfiles storage

- Allow the storage root and its ancestors to be directory links, including
  Windows symlinks/junctions, without changing the link or moving existing data.
  Resolve storage once; canonical aliases share the operation lock.
- Refuse dangling/looping/non-directory targets and unsupported reparse types.
  Retain linked-child, stored-file, active-config and installer/profile guards.
- Report canonical storage paths without changing JSON schemas; support root
  links in offline Bash/Zsh/Fish and PowerShell name completion.
- Add isolated mutation/recovery/locking/redirect/completion regressions and
  Windows-path fixtures. Native Windows/PowerShell verification remains pending.
- Bump the immutable runtime identity; no automatic live upgrade or migration.

## 0.1.5 — gradient header and readable status

- Use `lib/artwork/logo` unchanged as the shared welcome/root/nested-help artwork.
  Its 37-column, 13-row Braille wordmark fits narrow Termux screens and receives
  the existing left-to-right purple-to-pink gradient at rendering time.
- Keep NO_COLOR, JSON, redirected/non-Unicode/dumb-terminal and too-narrow
  fallbacks, bounded regular-file-only artwork reads and ANSI resets.
- Make `current` (including bare `-t`/`--theme`) and `doctor` human-readable by
  default, with purple titles, pink labels and plain redirected/NO_COLOR output.
  Preserve explicit `--json` schemas and escape controls in human path values.
  Status commands remain read-only and never launch discovered tools.
- Preserve older reference assets and use a new immutable runtime identity.

## 0.1.4 — Battery-style lifecycle review build

- Add public `bash install.sh` / `bash uninstall.sh`, with `--dry-run` and
  `--prefix`, no action word or `--yes`; retain legacy shell/PowerShell entry points.
- Default to native Termux `$PREFIX`, other POSIX `~/.local`, and Windows
  `$LOCALAPPDATA/Programs/Blastoff` (fallback `~/.local`). Migrate verified legacy
  `~/.local` ownership when the public target differs, committing the target before
  resumable legacy cleanup. Never automatically downgrade or replace conflicts.
- Prefer native completion/man discovery, including Termux Zsh's actual autoload
  directory alongside canonical site-functions. Add minimal owned hooks where
  required, Fish conf.d integration, and versioned PowerShell imports when available.
- Preserve linked profiles/targets by refusing unsafe edits with manual instructions;
  retain regular-profile encoding, unrelated content and recoverable backups on
  uninstall. Keep immutable runtimes and repair missing/unmodified support output.
- Show compact colored lifecycle plans respecting NO_COLOR. Dry-run performs no
  writes, probes or profile execution. Source integrity stays mandatory; only
  reviewed deliberate changes warrant `bash scripts/build.sh`, never auto-refresh.
- Current verification results are recorded separately in `docs/STATUS.md`; native
  Windows remains unverified. No live installation or profile change is implied.

## 0.1.3 — reviewed inventory and PowerShell completion build

- Register offline PowerShell completion on module import for `blastoff` and
  `Invoke-Blastoff`, retaining argument forwarding and native exit status.
  Complete static grammar/options and safe stored names without runtime launches.
- Include the reviewed integration planner and PowerShell completion tests in
  the source inventory. The planner is not yet wired into the lifecycle driver;
  installation still does not edit profiles or PATH.
- Refresh source checksums and archives after intentional additions. Use a new
  release identity rather than overwrite the installed immutable 0.1.2 payload.
  PowerShell runtime/native Windows validation remains unavailable and pending.

## 0.1.2 — branded help review build

- Share the actual terminal wordmark/header between welcome and all help paths;
  ship verbatim compact/wide text copies, with safe narrow/redirected fallbacks.
- Group commands by task and color headings/names without duplicating argparse's
  brace-enclosed command lists; preserve parser options, descriptions and aliases.
- Keep the shared grammar lightweight so help exits before application imports;
  normalize color flags before help, independent of their argument position.
- Retain undecorated JSON, NO_COLOR precedence, read-only behavior and existing
  picker/file protections. Native Windows remains deferred.

## 0.1.1 — terminal UX review build

- Add a fast, width-aware ASCII welcome with version/examples, purple/pink
  accents and explicit color/JSON policy; retain complete --help.
- Style fzf with source labels, border, guide and an Alt-P configuration-preview
  toggle; improve gum/numbered instructions without requiring optional tools.
- Ship a bounded, sanitized TOML preview helper with session-local preset caching;
  never apply themes or execute their custom commands during preview.
- Verify helper resolution in the installed layout and synthetic version upgrades.
  The new identity permits updating immutable 0.1.0 installations without deleting
  their payload or user data. Native Windows execution remains deferred.

## 0.1.0 — 2026-09-30 — review build

- Rebuild Bash and native PowerShell entry points around one Python 3.11+ core.
- Separate Blastoff theme/module storage from the active Starship config.
- Make listing read-only and keep local/preset names distinct.
- Add theme save/copy/import/delete, backup/restore and explicit legacy migration.
- Add conservative TOML module save/load with unrelated-value preservation.
- Add optional fzf/gum/numbered selection, JSON and NO_COLOR support.
- Add Bash/Zsh/Fish completion, man page and versioned owned-file lifecycle.
- Add pi instructions, preference guide, workflow skills/prompts, source audit,
  implementation plan, isolated safety tests and startup measurement tooling.
- Preserve existing original source and branding assets; record incoming inventory
  discrepancies in `docs/TERMUX-AUDIT.md` rather than assume a lossless move.
- Refuse deletion through linked storage subdirectories and detect external
  config edits during module merging, with regression coverage.
- Bound source packaging to explicit paths, exclude agent/runtime state, and
  support temporary archive destinations and checksum-only refreshes.
- Keep cached-help wording checks portable across Python argparse wrapping changes;
  add isolated native shell, literal-argument and opt-in real Starship tests.

- Expand offline Bash/Zsh/Fish completion by argument position, safe source
  prefixes/names, paired backup IDs and space-containing paths; avoid suggesting
  existing names for free destination operands.
- Isolate picker options from ambient fzf/gum configuration; recognize numbered
  Escape+Enter cancellation and use responsive TextIO input for Termux Ctrl-C.
- Filter reserved portable names from local discovery/picker choices; add native
  PTY tests and a disposable human visual-check helper. Optional branding remains
  independent of runtime help and commands.

- Prepare the native Windows validation handoff and isolated literal-argv/status
  parity checks; correct test-only Windows path/newline/POSIX assumptions.
- Omit the top-level POSIX launcher on fresh Windows installs, regardless of
  Git Bash/WSL discovery. Native Windows execution remains pending.

See `docs/STATUS.md` for native Termux evidence and remaining Windows,
interactive shell/picker and release gates. This is not production certification.

- Refuse deleting a stored theme/module when its regular path is the active
  config; reject non-object backup metadata with clean errors.
- Explain mutation/recovery semantics and shared options in nested command help.
- Add an opt-in installed-package Termux lifecycle rehearsal, everyday quickstart
  and approval-ready real-install plan; explicitly defer native Windows.

- Keep local list/picker choices when optional preset discovery fails, with
  concise human warnings and structured JSON discovery status. Distinguish a
  successful empty list; retain strict failures for explicit preset requests.
- Validate complete preset-list output and classify launch/UTF-8 failures as
  preset errors. No completion, wrapper or file-mutation logic was changed.
