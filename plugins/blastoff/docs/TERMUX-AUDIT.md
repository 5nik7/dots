# Native Termux working-tree audit — 2026-09-30

The rebuild was already moved into this repository; no package integration,
branch change or reference-asset move was performed. Initial Git status had
modified `.gitignore` and `README.md`, with all rebuild directories untracked.
Only `.gitignore`, `README.md` and `LICENSE` were tracked. The repository license
is MIT. Existing README changes were retained; `.pi/tasks/` was added to the
existing ignore rules. `.local/` remains ignored and untouched.

## Incoming inventory differences

The incoming `CHECKSUMS.json` did **not** describe this checkout exactly.
All its present payload files matched except `.gitignore`. Six recorded paths
were absent; byte comparisons found the following:

| Incoming path | Current location / result |
|---|---|
| `.local/src/banner` | Identical `.local/src/Modules/blastoff/0.0.2/banner` and `.local/blastoff-rebuild.local-src-banner` |
| `.local/src/blastoff.psd1` | Identical `.local/src/Modules/blastoff/0.0.2/blastoff.psd1` |
| `.local/src/blastoff.psm1` | Identical `.local/src/Modules/blastoff/0.0.2/blastoff.psm1` |
| `.local/logo/b.png` | Identical `.local/logo/bw.png` |
| `.local/logo/icon.png` | No byte-identical file found under `.local` |
| `.local/logo/logo.png` | No byte-identical file found under `.local` |

Additional files included the MIT license, `.local` guidance/reference copies,
and numerous existing logo variants. These were not overwritten or renamed.
The two unmatched images remain an explicit provenance gap, not a reason to
reconstruct assets or undo the user's move. Current checksums describe the
reviewed source inventory, not proof that every original archive asset survived.

The source launcher and install shell script arrived with mode `0660`, not
executable. Use `bash bin/blastoff` / `bash scripts/install.sh` in the checkout.
The isolated installer and archives assign executable launcher modes; no source
mode change was needed. Termux source execution must not assume `/usr/bin/env`.

The active environment override resolved to
`/data/data/com.termux/files/home/dots/config/starship/starship.toml`.
Only the environment value was inspected; that file was not opened or changed.
All exercised config/storage/install paths were temporary.

## Reproduced findings and bounded fixes

- Baseline `python3 -m unittest discover -s tests -v`: 35 tests, two failures
  (14.792 seconds): stale inventory prevented lifecycle installation; cached
  help had different line wrapping on Python 3.14.6. Wording/options were
  identical after whitespace normalization. The parity test now compares words;
  packaging no longer silently rewrites core help for the packager's Python.
- Packaging previously scanned the entire checkout, including live agent logs
  and arbitrary untracked files. `verify.source_files()` now shares an explicit
  source-path boundary with packaging, excludes bytecode/runtime state, and
  rejects source symlinks. `.local/src` and `.local/logo` remain included as
  references; other ambient `.local` files are not distribution inputs.
- `package.py --checksums-only` refreshes inventory without creating archives;
  `--output-dir` permits archive checks entirely under a temporary root.

- Regression fixtures reproduced deletion through symlinked `themes` and
  `modules` child directories. Deletion now checks safe parents before backup
  and again before unlink; outside files survive and no backup is created on
  initial refusal.
- Regression fixtures reproduced a lost external edit during module merging,
  for both an existing config and one created during the merge. Module load
  now captures a fingerprint before reading/merging and passes it through to
  the write boundary. A changed baseline fails before backup/replacement.
  Both regression tests failed before the fixes and passed after them.

These fixes do not alter the selected shared-core architecture or claim native
PowerShell parity. See `STATUS.md` for final checks, timings and pending gates.

## Interactive follow-up findings

- Real fzf 0.74.4 inherited `FZF_DEFAULT_OPTS=--filter=local:alpha` and applied
  alpha immediately, bypassing interactive confirmation. Picker subprocesses now
  receive an environment without `FZF_*`/`GUM_*` overrides, preventing ambient
  filters, command-running previews/binds, listeners, timeouts and label changes.
- Numbered Escape+Enter returned usage status 2; it now cancels with 130. It is
  deliberately still a line-oriented fallback: bare Escape needs Enter.
- A standalone native PTY probe showed `input()` deferring Ctrl-C until a newline
  on this Termux Python, even after restoring SIGINT's default disposition.
  `sys.stdin.readline()` responded immediately. The fallback now prints and flushes
  its prompt and reads through TextIO; real PTY regression coverage exercises
  Ctrl-C, EOF, blank input and Escape+Enter.
- Local listing/picker candidates previously included `CON` and `lpt1`, although
  applying those names is rejected by the portable-name contract. Discovery now
  uses the same `name()` validation, without changing or deleting these files.
- A minimal runtime copy with no `.local` or `assets` directory successfully ran
  help/version/list/current/doctor and all three completion-output commands.
  Missing optional images cannot break these runtime paths. The two unmatched
  historical images remain absent; no replacements were invented. All 20
  `.local` reference files in the prior checksum inventory still matched before
  this follow-up. The original directories were not modified.

Human visual and plugin checks are reproducible via `INTERACTIVE-CHECKS.md`.
Automated PTY evidence must not be represented as a human visual approval.
