# Operation progress

**Status: Implemented and verified on native Termux, 2026-09-29; pre-existing suite failures recorded below.**

## Accepted scope

Cover useful waits in the existing Git, theme, file and Anodize command families, including slow human read-only scans. Start animation after 500 ms. Use phase item counts when known and spinners otherwise. `DOTS_PROGRESS=auto|never` is the only new public control; `--yes` retains progress. Preserve data/dry-run output, transaction guards, rollback, command streams and exit statuses. No dispatcher, submodule, standalone-script, live-installation or paused Go migration work.

The [presentation contract](../docs/presentation.md#operation-progress) owns policy and the coverage table. Bash and Python share behavior through their scoped adapters; there is no required Gum dependency. Native Gum's command-owning spinner cannot update in-process transaction counts. Prompt-capable/direct-output external phases use immediate static messages, including Git network/signing/hook commands, theme downloads, tmux reloads and wallpaper adapters. Quiet phases animate without capturing or rerouting child output.

## Implementation

- [x] Shared terminal eligibility, delay, color/icon controls, sanitized labels, narrow layouts and cleanup.
- [x] Bash control-pipe renderer and Python scoped worker; operations remain in the original calling context.
- [x] Git discovery/status/publication counts and local sync phases; pause before prompts and permanent events.
- [x] Theme generation/publication, quiet reloads and counted installed-theme validation.
- [x] File catalog/browser/planning, apply and reverse recovery at existing journal boundaries.
- [x] Both Anodize entry points, with private bridge and raw-output suppression.
- [x] Documentation synchronized without new command routes, flags, metadata or completion tokens.
- [x] Finish verification and record native evidence and limitations below.

## Acceptance and evidence

Apply the shared [presentation acceptance gate](../docs/presentation.md#acceptance-gate). Existing final help, list, empty, success, warning, conflict, preview and recovery layouts remain authoritative; progress itself is transient and has no independent success/error vocabulary. Tests must cover terminal versus redirected streams, disabled/forced colors/icons, `NO_COLOR`, dumb terminals, 40/80/120 columns, long/control/Unicode labels, nested work, prompt suspension, interruptions and worker failure. Data and generated outputs stay exact. Fixtures must exercise real transactions and injected rollback using owned roots.

Native Termux baseline (three warm samples, before integration): Git status medians for 1/5/10 repositories were 197.5/1041.5/1906.1 ms. File-catalog JSON medians for 100/1000/10000 records were 190.1/555.9/3286.2 ms. These are advisory native observations, not other-platform claims.

Two theme-workflow tests currently fail because their expected 33 themes differs from this checkout's 34. Both failures were reproduced with unchanged `HEAD` implementations copied into disposable fixtures. Keep this existing fixture mismatch distinct from progress regressions; do not alter the live theme tree to satisfy it.

Linux/WSL and native Windows terminal behavior, live credential/signing helpers, desktop wallpaper rendering and abrupt power loss are not established by fixture or native Termux PTY evidence.


Follow-up unpaired runs were noisy: Git 1/5/10 repository medians were 212.2/2815.6/6939.3 ms (the 10-repository samples ranged from 3031 to 11622 ms); file medians were 290.4/756.0/4903.1 ms. An alternating comparison then used identical disposable data, unchanged `HEAD` implementation copies, and five warm samples per version, with other verification stopped:

| Disabled-progress JSON case | HEAD median | Current median |
| --- | --- | --- |
| Git status, five repositories | 1349.1 ms | 1306.5 ms |
| File catalog, 1000 records | 678.2 ms | 719.1 ms |

The broad slowdown was also present in the baseline. The paired file median was about 6% higher, with overlapping individual samples; this is advisory evidence under variable host conditions, not proof of an improvement or a stable regression. No dispatch lookup, startup scans or persistent caches were added. Disabled progress starts no rendering workers.

The full documentation checker encounters the existing `docs/testing.md` link to the removed `config/yazi/plugins/dots-symlink.yazi/README.md`. The same target is in `HEAD`; a separate check of touched documents found 182 valid relative links, that one existing broken link, and no introduced broken links.


Native Termux verification passed: progress 11 tests; Bash dispatcher 23; Git operations 27; file operations 21; file catalog 9; browser 17; theme picker 14; confirmations 8; shared themes 23; and the isolated Anodize verifier (Go checks plus 16 CLI tests). The theme-workflow suite passed 12 of 14 cases, with only the two baseline count failures above; the affected lifecycle, wallpaper and connector cases were also rerun successfully. Changed Bash syntax and ShellCheck passed (excluding existing dynamic-source SC1091 and established SC2015 idioms); Python syntax and `git diff --check` passed. The final fixture-environment tightening was rechecked in the three affected progress integration cases.

Representative native PTY output was reviewed at 40/80/120 columns for counted Bash work and a narrow Python spinner, with intact final messages. Automated cases also cover Unicode markers, ASCII fallback, absent `stty`, control-character sanitization, real Git JSON/status, disabled and redirected views, Ctrl-C/SIGTERM, worker failure, and real file apply/injected rollback. This is native Termux terminal/protocol evidence, not a claim about every terminal font or live credential/signing UI. No operation ran against live configs or remotes; unrelated Starship edits were preserved.
