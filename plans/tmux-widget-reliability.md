# Tmux widget reliability

**Status: Implemented, verified and activated in the owner's tmux server.** The owner approved retained readings, a quiet six-hour Termux location refresh while tmux is attached, seven-day sun-time retention, and the subsequent live preference refresh/reload.

## Behavior and ownership

- Clock uses dated astronomy independently of weather freshness, then the last valid schedule for at most seven days. Recompute day/night; invalidate known location/timezone changes.
- Termux clock worker may call `termux-geo --json`. Acquire at most every six hours after success; retry failures after 5/15/60 minutes, respecting helper cooldowns. Ordinary weather cache-only paths remain unchanged.
- Battery refreshes every 30 seconds with a five-second provider deadline; retain failures with `~` for five minutes, then show unknown. Git refreshes every five seconds with a three-second deadline; retain failures for 30 seconds with `~`, scoped to directory/worktree/HEAD. Confirmed non-repositories clear the Git segment.
- Shared private atomic cache, bounded detached workers, per-key coalescing and process-group cleanup; no daemon, raw coordinates or provider diagnostics in widget records.
- Add `apps.tmux.clock.auto_location` (default false, tracked Termux override true), `location_refresh_seconds` (21600), and `sun_times_max_stale_seconds` (604800). Existing Config owns inheritance, discovery and published preference activation.
- Theme/configuration/weather maintenance own this change. Menu assessment: no change, because existing widgets and Config browser suffice. Installer assessment: existing tmux directory ownership includes helper additions; no packages or destinations added. No public command/flag changes; both shell frontends retain shared configuration/weather contracts.

## Acceptance

- Follow the [presentation gate](../docs/presentation.md#acceptance-gate); preserve configured styling, battery box, width bounds, ranges, scrolling and indicators. Check 40/48/80/120 columns, two clients, delayed/failed providers, recovery and reload.
- Isolated cache/provider tests cover expiration, concurrency, crash recovery, corruption, special files, time changes, sun boundaries/rollover, geo cooldowns, Git identity and hostile names. Measure warm adapter latency and provider counts.
- Run affected tmux/Gitmux/weather/Config/Termux suites sequentially. Native Windows has no tmux/Android consumer; maintain portable weather/Config interfaces and report unavailable native Linux/WSL/PowerShell acceptance.
- Update canonical docs/README, build/check the available Wiki, validate links and whitespace. Live Config refresh/tmux reload remain separate activation after review; no commits or pushes.

## Verification

The implementation fixes two separate causes: solar state previously became unknown at the ordinary 15-minute weather freshness boundary, and the status rows could give window/tab labels space needed by Git or a padded battery box. No intermittent live provider failure was reproduced during planning; read-only Gitmux probes took 0.27–0.34 seconds.

- `tools/test_tmux_widgets.py`: all 20 checks pass, including actual detached fixture workers, eight concurrent battery readers sharing one provider call, stale-token/lease recovery, bounded descendant cleanup, seven-day solar expiration, independent Git fields, an unavailable HEAD retaining an unknown slot, Config validation and native clock-cell colors.
- Native tmux/status/layout/Gitmux checks pass after updating acquisition/layout fixtures, including two clients, 40/48/80/120 columns, all selectable palettes, explicit custom placement, overflowing window lists, pane changes, unknown states, recovery and reload. The full runs were followed by focused reruns of corrected assertions; no live server was used.
- `tools/test_config_values.py`: all 14 pass. The tmux-specific Config discovery cases pass. The broader discovery suite retains one unrelated round-trip failure (`KeyError: formatting`); it reproduces with the committed `config_values.py` in the test process.
- `tools/test_wttr.py`: 43 pass, one optional skip, five unrelated human-view indentation failures. All five reproduce from committed source exported to an owned temporary checkout. `tools/test_wttr_browser.py`: all 17 pass. Generated weather command metadata is current.
- `profiles/termux/tests/test_termux_geo.py`: all 34 pass. Its fixture needed the bundled-profile root and shared renderer dependency copy corrected; all acquisition tests use mocked device/HTTP providers.
- Warm subprocess reads (20 samples each, including Python startup on this Termux device): battery median/p95 268.7/590.1 ms; Git 125.5/274.2 ms; solar 125.5/238.8 ms. No provider workers started during these warm reads. These are local launch/host-load measurements, not native Linux/WSL benchmarks.
- Python/Bash syntax, 510 relative Markdown targets and `git diff --check` pass. Canonical documentation and the local Wiki are synchronized; `dots wiki check` reports healthy. Wiki build transaction: `8664068aeb3d4621ba5f7d26012145c1`.

Actual Android location/network delivery and native Linux/WSL terminal/Windows PowerShell 5.1/7 acceptance are not established by these fixtures. No packages, live refresh, reload, commits or pushes were performed as verification.

## Live activation

After separate owner approval, `dots config refresh` published generation `g.411a47a1363c4441a84cdd736d9aedd2` in transaction `495bfab7ae524317bcf12bad02f4903d`, preserving Catppuccin Mocha. The current 48-column tmux server successfully loaded the updated configuration. Published clock controls enable automatic location at 21600 seconds with 604800-second retention; the live solar cache contains three dated schedules, a successful location-helper result and a valid night state. Battery and both Git fields have successful cached readings. This confirms live integration, not a fresh Android fix or independent network delivery.

The shared refresh reported `pending` solely because Yazi's notification socket refused the connection; a targeted notification retry returned the same error. Preference publication and tmux activation succeeded. No Yazi process was launched to resolve this unrelated notification, and no commits or pushes were made.
