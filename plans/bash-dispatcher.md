# Bash Dispatcher Foundation

**Status: Implemented; native Termux verification complete**

Implement the approved Bash framework in the existing checkout. Go remains paused.
The first slice includes direct longest-prefix dispatch, repository/local/explicit
command roots, optional static comment metadata, shared color/icon helpers, and
on-demand Bash/Zsh/Fish completion. No functional theme commands or installer.

- [x] Inspect the prototype and capture an isolated baseline.
- [x] Implement modular routing, help/catalog, presentation, and completion.
- [x] Verify all three shells with disposable extensions and user roots.
- [x] Measure dispatch/catalog scaling and shell startup effects.
- [x] Synchronize decisions, guides, reference documentation, and README.

Baseline source: `500d45d`. Thirty measured samples after five warmups in an
isolated HOME/repository: help 14.76 ms; directory lookup 15.14 ms. Raw evidence:
`$TMPDIR/dots-bash-baseline-_ckmeq8w/baseline.json`. Device timing is advisory.

Tests must not source private/live startup chains or execute real extensions.
Keep commits, pushes, downloads, and machine installation outside this task.

## Implemented Contract

[Decision 0006](../docs/decisions/0006-bash-command-framework.md) records the
approved Bash-specific extension model. [The command reference](../docs/commands.md#implemented-bash-command-framework)
owns authoring, roots, flags, helper functions, and completion behavior.

The entry point loads only routing for direct execution. Help/catalog, UI helpers,
and suggestion generation are separate modules. Shell-native adapters are linked
into the repository's existing configuration layout; no command discovery occurs
on shell startup. No real management extensions ship in this slice.

## Verification

- 21 isolated Bash framework tests passed, including real controlling-terminal
  Tab presses in Bash, Zsh, and Fish; argument/stream/status preservation; PID and
  signal delivery; collisions; symlinks; malformed metadata; live additions;
  color/icon controls; and independent stdout/stderr terminal handling.
- Native Tab tests cover `--option=value`, directory names containing spaces,
  quoted paths, choices containing spaces, and literal shell metacharacters.
  Completion never evaluates metadata or user substitutions. Bash uses explicit
  literal quoting for fixed candidates, plus native filename completion.
- All 17 existing Zsh regression tests passed. Public-fixture Zsh/FZF-tab
  acceptance passed for dots completion, existing Tab/history/preview behavior,
  vi-mode cursor changes, and exact hook/keymap/FZF/fpath equality after reload.
  Evidence: `$TMPDIR/dots-zsh-kaex9c8g/`.
  The final adapter also passed a focused cached-session FZF-tab recheck in
  `dots-final-pty.log` there, after the cursor-position regression was added.
- Bash/Zsh/Fish syntax checks, ShellCheck, Markdown links, and whitespace checks
  passed. No Go implementation, tests, or CI were changed or invoked.

## Performance Evidence

Twenty measured samples after three warmups per case, sequential native Termux
runs. Counts below exclude one executable dispatch probe. Data is advisory;
mobile-device load and thermal state are not controlled.

| Extra commands | Direct dispatch | Typed-prefix completion | Empty-prefix completion | Global help |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 30.79 ms | 29.47 ms | 29.40 ms | 28.74 ms |
| 100 | 26.95 ms | 28.91 ms | 101.64 ms | 115.74 ms |
| 1,000 | 32.14 ms | 27.77 ms | 647.43 ms | 813.23 ms |

Full catalog listing at 1,000 commands was 804.45 ms. Full enumeration scales
with catalog size; targeted dispatch does not enumerate, and a typed completion
prefix limits metadata reads to matching filenames. Persistent caches remain
unnecessary for the current small catalog; the large-catalog timings are an
explicit remaining tradeoff of next-Tab discovery.

Raw scaling and shell-loading samples: `$TMPDIR/dots-bash-bench-k9u3bqy6/results.json`.
Median fresh-shell adapter registration cost relative to a bare shell was
approximately 0.46 ms for Bash, 1.44 ms for Zsh, and 1.33 ms for Fish. This isolates
adapter registration; it is not a timing claim for the owner's private startup.

The original baseline above was captured earlier in the session. To separate
implementation cost from device drift, 30 paired samples alternated baseline and
new invocations afterward: directory lookup 22.01 → 22.84 ms; help 23.41 → 31.47 ms.
The richer help now loads the static catalog and renders more information; its
roughly 8 ms increase is expected. Raw paired samples:
`$TMPDIR/dots-bash-paired-z_c0yox_/results.json`.

## Limits and Delivery

Native evidence is Termux-only. Linux/WSL/MSYS remain design targets; no Windows
native/PowerShell support is claimed. Completion uses literal argument hints;
combined short options, shell-expression expansion, runtime providers, and
undeclared argument inference are outside this version. Temporary artifacts may
be removed by ordinary temporary-directory cleanup.

The implementation is in the existing checkout without commits, pushes, a new
worktree, package changes, or live-home installation. Start a fresh configured
shell to load its new adapter. Go development remains paused.

Final runtime source SHA-256: `80a9b6e9769e426781dc6747568c0a52255f30d4887bbe7898507cf8ca0e8910`.
This hashes sorted paths and contents, NUL-delimited, for `bin/dots` and files
under `lib/dots`, including the final cursor-position fix after the timing run.
