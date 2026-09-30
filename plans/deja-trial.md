# Deja Zsh trial

**Status: Implemented; promoted to the default at the owner's request after the trial.** Not a resumption of the Go roadmap.

## Default adoption

Deja is now selected when `DOTS_ZSH_SUGGESTIONS` is unset or empty. `DOTS_ZSH_SUGGESTIONS=autosuggestions` keeps the original engine available; explicit `deja` still works. Missing-binary and invalid-selection fallbacks, Tab preservation, and fresh-shell switching remain unchanged. The owner accepted the measured startup tradeoff after trying Deja. General fixtures explicitly select autosuggestions; the native Deja runner tests unset-selector activation. No additional installation or live history import is required.

Default-adoption verification: all 22 Zsh unit tests and both native PTY runners passed, including unset-selector Deja activation and explicit autosuggestions selection. The three-sample alternating warm medians were 1.0751 s for autosuggestions and 1.1659 s for Deja. Evidence is retained in `dots-zsh-nf3480rs` (Deja) and `dots-zsh-jtn2w5eq` (general PTY) under the reported temporary root. Documentation verification still encounters only the known removed-Yazi-link failure noted below. The original trial scope and evidence are retained as history.

## Original trial scope

- Build upstream Deja natively on Termux with Go/CGO and test using disposable home/config/cache/state roots.
- Add `DOTS_ZSH_SUGGESTIONS=deja` as an opt-in alternative to the default `autosuggestions`; retain a missing-binary fallback and prevent engine mixing on reload.
- Load synchronously through the existing load-once Zinit wrapper, preserve FZF-tab's Tab binding, and inherit the initial suggestion color unless explicitly overridden.
- Install only a new user-local binary after native acceptance; do not run the upstream installer or import real history. Zinit retains ownership of its optional plugin checkout.
- Document activation, restart-based rollback, daemon/plaintext-history implications, and native-platform limitations.

## Acceptance

- [x] Unit tests cover default/selected/missing/invalid engine, load-once behavior, and explicit key/style overrides.
- [x] Native isolated Deja checks cover daemon/query, arrow acceptance, vi mode, Tab, highlighting configuration, and reload.
- [x] Compare isolated startup timings; run existing Zsh checks and documentation links (pre-existing full-link failure recorded below).
- [x] Record installation provenance and limitations.

Follow the [presentation acceptance gate](../docs/presentation.md#acceptance-gate). No new CLI view is introduced; the optional dependency warning uses the existing shell diagnostic style.

## Baseline

Termux Android/ARM64, Go 1.27.1. The initial tool environment omitted Termux's `LD_PRELOAD`; its 0.6522 s warm startup median and completion PTY timeout are not valid full-integration baselines. Restoring `/data/data/com.termux/files/usr/lib/libtermux-exec-ld-preload.so` made all 22 Zsh tests and the existing PTY suite pass. This is required by existing `/usr/bin/env` shebangs, not a Deja workaround.

Upstream revision: `97156840defebb476be0bbc97bbcca3b75934c66`. Native CGO build passed. Unmodified upstream tests passed all packages except three shell tests that hardcode `/usr/bin/true`, which is absent on Termux (including with the correct preload). Native integration acceptance used the actual built binary instead; upstream tests were not patched.

## Verification and installation

- `tools/test_zsh.py`: all 22 tests passed; native syntax is included.
- `tools/test_deja.py`: passed against copies of the installed binary/plugin. Real daemon/query, right-arrow ghost acceptance, vi cursor transitions, single-candidate Tab completion, suggestion style configuration, and equal keys/hooks after two reloads. This is not a visual palette audit or exhaustive upstream acceptance.
- Existing `tools/zsh_interactive.py --samples 2`: passed FZF-tab menus, directory/history pickers, completion refresh, vi mode, reload equality, and prompt checks with correct Termux preload.
- `tools/zsh_fixture.py --samples 5`: passed, default warm median 1.0671 s, noninteractive 0.0095 s.
- Same-fixture alternating engine comparison (six samples each): autosuggestions 1.0681 s; Deja 1.1775 s, about 109 ms / 10% slower. An earlier block-ordered comparison showed 238 ms; mobile load drift affects these advisory measurements. Synchronous readiness is retained deliberately for this opt-in trial, not promoted to the default.
- Alternating original-versus-current selector comparison (six samples each): 1.2177 s versus 1.2523 s; samples overlap and drift upward in both groups. No subprocess/cache/scan was added to the default selector path; this noisy result is not evidence of a speedup.
- Full Markdown verification still reports the pre-existing `docs/testing.md` link to removed `config/yazi/plugins/dots-symlink.yazi/README.md`. No documentation cleanup was mixed into this change.

Installed new (previously absent) `~/.local/bin/deja` and `~/.local/share/zinit/plugins/Giammarco-Ferranti---deja`. The plugin checkout retains its upstream Git origin and exact tested revision. Local provenance/installation receipt, including binary SHA-256, is `~/.local/state/dots/deja-trial-9715684.json`. No real history was imported, no live shell was sourced, and no live daemon was started. At initial installation selection was explicit via `DOTS_ZSH_SUGGESTIONS=deja zsh`; default adoption above supersedes this. No personal hook was edited. Update the binary and plugin together after reviewing/testing upstream changes.

Retained temporary evidence: `dots-deja.PeyuWK` (source/build/upstream tests), `dots-zsh-794kw4yp` (final native Deja PTY/timings), `dots-zsh-j_hi0tjk` (existing PTY suite), and `dots-zsh-sqjpb2vc` (alternating selector comparison), under the reported Termux temporary directories. Other native platforms and full human visual review remain unverified.
