# Termux location lookup

**Implemented; native network acquisition verified, GPS/permission-recovery/service-cancellation acceptance remains pending.** The owner-approved `androidots/bin/termux-geo` Bash helper provides Nominatim reverse lookup, private bounded caches, strict script output, and Dots human presentation. Androidots owns implementation and its command reference; this plan tracks parent-shell integration and acceptance.

- [x] Implement device/explicit/stdin acquisition, JSON/get/format/coordinates, deadlines and cache-only reads.
- [x] Implement static Bash/Zsh/Fish completion generation and guarded local installation.
- [x] Register Androidots-local completion directories in interactive Termux personal startup, before Zsh compinit and Bash completion loading.
- [x] Verify isolated acquisition/cache/error/installation tests and native shell completion discovery.
- [x] Verify the [presentation gate](../docs/presentation.md#acceptance-gate), native 40/80/120-column PTYs, machine-output bypass and cancellation.
- [x] Measure warm lookup and startup behavior; synchronize documentation.
- [x] Run the explicitly authorized final `termux-geo completion --all --install` against this checkout and verify installed files.

Defaults: network provider, 60-second fix age, 20-second overall deadline, English Nominatim addresses, JSON when redirected. GPS is explicit. The public endpoint is rate-limited and cached; cache-only reads never acquire data. Coordinates and geocoder object positions remain separate. Existing status helpers and live status bars are outside scope.

This Android adapter is a named platform exception: native Windows PowerShell 5.1/7, Linux and WSL have no Termux device acquisition adapter or new app destinations. Their personal completion paths must remain unchanged. GPS, Android permission denial/recovery, and Android service cancellation still require owner-device acceptance, separate from the verified network provider and mock-provider/native-shell evidence. No package installation, commit, push or live shell reload is authorized by this implementation.

## Initial implementation evidence

Native Termux, Bash 5.3.20: 28 isolated command tests and six native Bash/Zsh/Fish integration tests passed. Syntax/ShellCheck, changed-document link checks, and the parent documentation verifier (801 links in 108 files) passed. PTY acceptance exercised 40/80/120 columns, forced-decoration data bypass, NO_COLOR, plain fallback, delayed phase changes and interrupt cleanup. Mocked data only; no owner coordinates were queried or sent externally. Help/fields/completion have no acquisition; malformed/missing data, cache corruption, stale/sleep/reboot cases, HTTP cooldown, concurrency, binary-preserving completion backups, preflight drift and partial installation failures are covered. Managed transaction previews/pickers are inapplicable to this command.

The first native test exposed Android's denial of `/proc/uptime`. The implementation uses Bash 5.3 `BASH_MONOSECONDS`, combines wall elapsed time to cover suspend, and validates boot identity. This avoids a Python runtime dependency. Measured repeated jq parsing on warm reads was consolidated into one validated rendering pass.

Thirty sequential warm samples per mode, test-owned cache and mocked providers: JSON median/p95 59.88/85.45 ms; city getter 59.45/84.91 ms; coordinates 61.18/69.28 ms. All issued zero provider calls. Before consolidating parsing, medians were approximately 131/183/104 ms respectively. Ten earlier cold JSON mock samples measured 602 ms median, 744 ms p95; these are local fixture overhead, not internet/GPS performance guarantees.

Thirty sequential samples per original/changed isolated shell adapter/startup: Bash median 65.60 → 67.82 ms (p95 76.52 → 72.88); Zsh 14.20 → 12.57 ms (p95 32.01 → 16.10); Fish 66.18 → 67.54 ms (p95 73.98 → 75.40). These bounded public-fixture measurements show no material startup regression; they do not measure owner plugins or Android tab startup.

Broader checks retain existing failures: shared-shell suite 19 tests, four failures; shell-init suite 30 tests, two failures/five errors/17 skips; Zsh suite 29 tests, one failure. All seven assertion failures reproduce with the original HEAD versions of the three changed shell files substituted only inside disposable fixtures. They concern existing prompt/tool/theme expectations and a missing theme fixture. Three representative Xonsh error subcases also reproduce because its installed launcher cannot execute. Those unrelated fixtures/launchers were not modified.

Final authorized installation created `termux-geo.bash`, `_termux-geo`, and `termux-geo.fish` in Androidots' respective local completion directories, all mode 0644. No prior targets existed, so no backups were required. Each installed file exactly matched generated source and passed native syntax checks. Fresh controlled Bash/Zsh/Fish processes discovered the actual installed files using disposable homes/caches; the owner shell was not reloaded. Existing shells need the updated paths loaded, normally by starting a new shell.

## Native timeout repair

The device wrapper's `ulimit -f 64` caused the native Termux API bridge to hang. Direct network acquisition returned in 0.64 seconds; the restricted call timed out. Evaluating the same helper without the restriction succeeded in 0.74 seconds. The mock provider did not reproduce this Android compatibility failure.

The repair removes the resource-limit change, captures at most 65,537 bytes through a reader in the existing timed process group, and rejects device responses above 64 KiB. The wrapper retains pipe failure status and reaps pipeline children during cancellation. Timeout errors identify device location, address lookup, stdin reading, or cache locking; curl connection/request timeouts also return 124. Machine stdout remains empty on failure. Provider defaults, cache policy, flags and installed completions are unchanged.

Native checks with the inherited Android environment and disposable HOME/config/data/state/cache/temp roots succeeded: refreshed network coordinates in 1.157 seconds and a cache-only read in 0.060 seconds. A separate Nominatim request using public example coordinates returned city, state, postcode, country and attribution in 1.163 seconds. Device coordinates were neither printed in reports nor sent to the address service. An earlier stripped-environment native check timed out; the normal inherited Android environment succeeded. These observations are acceptance evidence, not latency guarantees.

All 34 focused command tests passed, including resource-limit inheritance, exact/oversized device-output boundaries, phase-specific errors, HTTP timeout status, stalled stdin, child cleanup, lock reuse, machine decoration suppression and human timeout output in 40/80/120-column PTYs. All six shell-integration tests, Bash syntax, ShellCheck, tracked/task-local untracked whitespace checks and 802 relative Markdown links passed. Installed Bash/Zsh/Fish completions still match generated source. GPS, permission denial/recovery and separate Android-service cancellation remain unverified.

## Help colors

The help renderer uses shared Dots bold cyan for headings and blue for command syntax, option signatures and example commands. Descriptions retain the normal foreground. A single static text source preserves wording and spacing across colored, redirected and standalone output. Existing color controls apply; help does not start progress, location or HTTP work. Flags and completion files are unchanged. The existing Termux platform exception continues to apply.

The focused help check passed for automatic color in 40/80/120-column Termux PTYs, forced color, `DOTS_COLOR`, `NO_COLOR`, disabled color, dumb terminals, redirected output, completion help and missing-library fallback. Stripping color reproduces plain help exactly. Field listings and generated completions remain undecorated, with no provider calls or cache creation. These checks apply the existing presentation gate without changing other renderers.

The full 34-test command suite, Bash syntax, ShellCheck, whitespace checks and 802 relative Markdown links passed after the help change. The installed Bash/Zsh/Fish completions still match generated source; no reinstall or shell reload is needed.
