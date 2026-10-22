# wttr and Termux daylight clock

**Status: Implemented; native Windows and owner-device acceptance remain pending.** Owner approved this scope on 2026-10-22.

- Add a standalone `wttr` command with a shared Python 3.11+ controller and Bash/native PowerShell entry points. Preserve the existing weather-script deletions and variants.
- Use wttr.in `format=j1`, explicit location, configured default, then existing `termux-geo` city. Default location is unset; default units are US/Fahrenheit. No IP-location fallback.
- Provide current, daily (1–3), hourly, JSON, fields, literal widget templates, daylight, bounded refresh and strict cached modes. Follow the [presentation gate](README.md#presentation-gate-for-every-plan): shared renderer/progress, colored help, clean data, 40/80/120-column human views.
- Create `config/wttr/config.toml` with Nerd Font condition mappings. Register it as metadata only; Windows uses APPDATA/wttr (XDG override supported).
- Cache weather for 15 minutes with at most six hours of explicitly marked stale data. Coalesce bounded refresh workers, retain failures/cooldowns, and keep manual-location cache entries separate. Background refresh reads only configured default or cached city/address (24-hour fix limit); Android acquisition is foreground-only. Never duplicate location providers or bypass permission gates.
- Remove the network job from the Termux upper row. Keep battery and existing clock geometry; only clock foreground changes: theme yellow by day, blue by night, foreground when astronomy is unavailable/expired. No weather widget yet. Preserve the lower row, theme palette, session/window styles and battery.
- Generate contextual Bash, Zsh, Fish and PowerShell completion from CLI metadata. Explicit installation uses the shared file transaction engine, backups, drift checks and undo; never modify profiles automatically.
- Validate mocked geo/HTTP/cache behavior, recovery, timeouts, malformed data, missing helpers and bounded reads; attached private tmux clients at 40/80/120 columns and repeated reloads; focused parent and Androidots regressions, sequentially on Termux. No live HTTP/location tests, permissions, package installation or live tmux reload.
- Native Windows PowerShell 5.1/7 and desktop validation remain named pending gates where unavailable. Termux geo and tmux have no native Windows equivalent; manual/default weather uses the same controller.

## Initial implementation validation

Verified on Termux, sequentially in owned fixtures:

| Check | Result |
| --- | --- |
| `python3 -B tools/test_wttr.py` | 21 tests: 20 passed; native PowerShell runtime case skipped |
| `python3 -B tools/test_tmux_status.py` | 16 tests: 15 passed; optional external battery-source case skipped |
| `python3 -B tools/test_android_status.py` | 11 passed; retained standalone network contracts |
| `python3 -B androidots/tests/test_termux_status.py` | 29 passed |
| `python3 -B androidots/tests/test_termux_geo.py` | 34 passed |
| `python3 -B androidots/tests/test_termux_sessions.py` | 28 passed |
| `python3 -B androidots/tests/test_termux_bar.py` | 7 passed |
| `python3 -B tools/test_theme_workflow.py Workflow.test_all_application_connectors_and_tmux_include` | 1 passed |
| `python3 -B tools/test_files.py` | 9 passed |
| `python3 -B tools/test_installation_adapters.py` | 9 tests: 5 passed; 4 native Windows/PowerShell cases skipped |
| `python3 -B tools/test_bash_dots.py` | 24 passed |

The weather suite includes actual Bash/Fish candidates, Zsh Tab completion, human help/current/hourly views at 40/80/120 columns, delayed progress and decorated-data suppression. Detached worker tests copy the controller and mock only provider boundaries; concurrent clients cause one weather fetch and use only cached geo. Completion tests exercise shared transaction backup, idempotence and undo. Tmux tests attach real clients on private sockets, validate all three clock colors and repeated reloads at each width, assert zero Android network-module calls, and preserve battery/lower-row behavior.

Twelve isolated warm reads measured median/max 334/416 ms for cached daylight CLI and 458/574 ms for the tmux adapter after deferring HTTP/TLS imports until fetching. The adapter retains its one-second deadline. These are local observations, not cross-platform performance guarantees. The root catalog recognizes `dots:wttr` using an isolated home. Bash syntax, ShellCheck and both repositories' `git diff --check` pass.

Relative Markdown file targets resolve. New/changed anchors resolve; the pre-existing `docs/commands.md` link to `themes.md#commands` remains unmatched (the current section is named “Unified commands and family shortcuts”). That unrelated link repair is deferred.

Native Windows PowerShell 5.1/7, Windows ACL/lock behavior, real Android acquisition/permission handling, public wttr.in availability and font appearance were not exercised. No live tmux reload, theme publication, completion/config installation, package install, commit or push occurred. Existing weather-script deletions/variants and concurrent Neovim work were preserved. Androidots changes are documentation-only.

Durable behavior and exact owner-run activation/recovery commands are in [the weather guide](../docs/wttr.md).

## City and stock-request follow-up

**Status: Implemented and verified in isolated Termux fixtures; native Windows and owner-device/service acceptance remain pending.** Owner approved this follow-up on 2026-10-22.

- Keep plain `wttr` as the custom summary. Change location precedence to explicit input, configured `default_location`, then bounded `termux-geo --json` city. Preserve helper acquisition/permission/cooldown contracts and cached-only bar requests.
- Use the selected city/manual label in custom views, retain geo attribution and expose an `attribution` field. Keep upstream JSON unchanged. Version cache identity/schema so coordinate-only entries cannot preserve neighborhood labels; retain old files.
- Add stock letter groups, `format=VALUE`, moon/date and service-page syntax through native curl/curl.exe. Encode literal values, preserve response bytes, bound output/deadlines, suppress provider stderr and reject local-mode conflicts. Stock requests bypass weather caching; service routes skip location.
- Update static Bash/Zsh/Fish/PowerShell completion, shared colored help, configuration comments and command/platform documentation. Preserve the existing presentation gate and clock/layout/status behavior.
- Verify city precedence, unavailable/malformed providers, stale/recovery behavior, exact stock URLs/bytes, shell completion and cache isolation with mocked providers. Recheck attached private tmux clients at 40/80/120 columns and repeated reloads. Keep native Windows and actual device/public-service acceptance separately pending.

### Follow-up verification

- Weather: the 26-case suite passed with one unavailable native PowerShell skip. A subsequent actual Bash Tab test exposed colon word splitting; after its fix, all four targeted Bash/Fish/Zsh completion and transaction tests passed. The resulting weather suite contains 27 cases, with 26 distinct cases verified and the native PowerShell case pending.
- Parent tmux: 16 cases, 15 passed and the optional external battery-source case skipped. Attached private clients checked 40/80/120 columns, repeated reloads and day/night/unknown clock colors. Parent Android status: 11 passed.
- Androidots geo: 34 passed; parent geo shell discovery: 6 passed; Androidots status: 29 passed; Androidots bar: 7 passed. No Androidots implementation files changed in this follow-up.
- Native bridge fixtures preserve stock bytes and literal arguments. Fake curl covers every requested stock flag/path, URL encoding, timeout, missing curl, nonzero exits, size limits and stderr suppression. Full provider mocks preserve existing permission/cache boundaries; no public weather or real location calls were made.
- Twelve isolated warm reads per surface: cached CLI median/max 306/682 ms; real tmux adapter median/max 383/801 ms. Every adapter sample returned the expected daylight token within its one-second deadline. These are local samples, not cross-platform guarantees.
- Both Git whitespace checks passed. All 329 relative file-link targets in the affected documentation resolved; the previously recorded unrelated `themes.md#commands` anchor remains deferred.

Existing work, weather-script deletions/variants and concurrent Neovim changes were preserved. No commits, pushes, dependency/completion installation, Android permission changes, theme publication or live tmux reload occurred. The [weather guide](../docs/wttr.md) contains exact owner refresh and completion activation/recovery commands. Old cache entries are retained and ignored; owner `wttr --refresh` seeds the city-based entry.

## Styling and service-page follow-up

**Status: Implemented and verified with isolated fixtures and native Termux terminals.** Owner approved configurable attribution, temperature/icon styling, forecast icons, service URL repair and described stock completions.

- Hide attribution in the active default config while preserving its data field. Keep default-visible behavior for older configurations omitting the option.
- Add configurable temperature thresholds/colors, condition-code colors and ANSI-auto widgets with explicit plain/tmux modes. Reuse shared Presentation spans and retain machine-output boundaries, cached-provider policy and bar geometry.
- Use forecast-specific condition codes and astronomy for icons. Validate boundary conversion, missing values, wrapping and style restoration.
- Correct service pages to single-slash paths and derive described Zsh/FZF-tab entries and other supported completion tooltips from shared stock metadata. Update existing generated checkout files only after concurrent-edit checks.
- Use isolated provider fixtures, owned terminals/FZF-tab and private tmux sockets; synchronize documentation and record native Windows limits. No live provider calls, permissions, package installation, shell/server reloads or publication.

### Styling follow-up verification

- `python3 -B tools/test_wttr.py`: 32 tests, 31 passed and the unavailable native PowerShell case skipped. An additional focused FZF-tab rerun passed after extending the same case to check a colon inside a description. Real FZF-tab menus at 40/80/120 columns display descriptions and insert tokens only; metric flags, colon service pages, formats after combined flags and quiet descriptions are covered.
- `python3 -B tools/test_resources.py`: 12 passed, including mixed-color spans, wide characters, inert control text, wrapping and plain fallbacks.
- `python3 -B tools/test_tmux_status.py`: 16 tests, 15 passed and the optional external battery-source case skipped. Attached private clients check 40/80/120 columns and repeated reloads. The weather suite additionally renders tmux widgets in attached clients, verifies literal markup-like data and checks incoming foreground/background restoration.
- Provider fixtures assert canonical single-slash URLs and unchanged curl response bytes. Temperature boundaries/conversion, custom colors, invalid settings, missing values, forecast night/day codes, attribution settings, widget mode/override behavior and undecorated data interfaces passed.
- Twelve isolated warm reads per surface: cached CLI median/max 321/404 ms; real daylight adapter median/max 422/523 ms. All adapter samples returned valid tokens within the one-second deadline.
- Effective config inspection confirms the repository config is selected, attribution is false and widget mode is ANSI-auto. All four checkout completion artifacts match their generators; regenerated Zsh/Fish/PowerShell files passed concurrent-edit fingerprint checks before replacement. Bash/Zsh/Fish syntax checks and both Git whitespace checks passed. All 260 checked relative documentation file targets resolved; the previously recorded unrelated theme anchor remains deferred.

No live provider or public-weather requests, permission changes, package installations, shell/tmux reloads, commits or pushes occurred. Existing work and Androidots changes were preserved. Native Windows PowerShell 5.1/7 tooltip/color/terminal acceptance remains pending; its stock tooltip lookup is case-sensitive to distinguish m/M and q/Q. The weather guide includes the exact owner-run command to reload the already-installed Zsh completion without restarting the shell.


## Theme colors and spacing follow-up

**Status: Implemented and verified in isolated fixtures and native Termux PTYs.** Owner approved the theme-name plan on 2026-10-22. The compact-label/two-space layout was subsequently superseded by the aligned-layout follow-up below.

- Follow the published Dots palette for default temperature and condition colors. Accept supported lowercase names/aliases, six-digit hex, integer or decimal-string ANSI indices 0–255, and `default`. Preserve thresholds and explicit overrides.
- Read at most one bounded, regular palette snapshot per colored render through the existing platform state-root adapter. Fall back to documented terminal colors for missing/bad data; never invoke theme commands or change caches. Both Bash and native PowerShell share this controller; Windows config destinations remain unchanged.
- Make Now/Midday labels compact, use two spaces after nonempty weather icons, and one between current condition and temperature. Keep supporting labels aligned, hourly structure, display-cell wrapping, and widget-template spacing.
- Preserve shared renderer defaults and JSON/scalar/daylight/stock bytes. Cover color policies, ANSI/tmux restoration, native Termux 40/80/120-column PTYs, palette replacement and malformed snapshots with isolated roots. Native Windows PowerShell 5.1/7 and actual font appearance remain pending acceptance.
- Synchronize the weather guide, README and command reference. Preserve prior work; no provider calls, installation, theme refresh, live server reload, commit or push.

### Theme and spacing verification

- Weather suite: 36 tests, 35 passed and the unavailable native PowerShell case skipped. Named palette changes, once-per-render reads, explicit hex/index values, mixed TOML arrays, invalid colors, bounded/malformed/missing snapshots, payload-link refusal, plain/data bypass and exact icon spacing passed. Existing native tmux widget escaping and foreground/background restoration passed.
- Shared resource/presentation suite: all 12 tests passed, including unchanged default label alignment and compact-label support.
- After extending native PTY assertions for icon-enabled summary and hourly rows, the focused PTY case passed again at 40/80/120 columns. It covers compact Now/Midday rows, the two-space icon gap, automatic color, help, widgets, wrapping and progress/data separation. Actual font rasterization remains owner acceptance.
- Read-only effective-config inspection confirms the repository config is selected and the published Catppuccin Mocha palette supplies blue `#89b4fa` and muted `#585b70`. No theme publication is needed to use these defaults.
- Git whitespace checks, including touched untracked weather sources, passed; all 213 relative documentation file-link targets checked in the changed documentation resolve.

Native Windows PowerShell 5.1/7 terminal acceptance remains pending. No weather/location provider calls, installation, live reload, theme publication, commit or push occurred. Prior-session and unrelated checkout changes were preserved.


## Restore aligned weather output

**Status: Implemented and verified.** Owner requested restoration of the earlier aligned layout and a single space between weather icons and conditions.

- Restore ten-character aligned Now/Midday label columns; use one space after each nonempty current, midday and hourly icon. Disabled/empty icons leave no reserved gap.
- Remove the compact-label override and the unused shared-renderer label-width parameter. Preserve theme color names, literal hex/index overrides, temperature thresholds, hourly structure and widget templates.
- Update exact spacing assertions, native 40/80/120-column PTY coverage and current documentation. The preceding compact-layout verification is historical; this follow-up supersedes its spacing behavior.
- Run weather and shared-renderer suites sequentially, whitespace checks and relative documentation-link checks. Both shell entrypoints retain the same controller; unavailable native PowerShell and actual font appearance remain pending acceptance.

### Aligned-layout verification

- Weather suite: 36 tests, 35 passed and native PowerShell skipped because unavailable. Exact aligned labels and single-space icon gaps passed with icons enabled, disabled and empty; native Termux PTYs checked current/midday/hourly views and wrapping at 40/80/120 columns. Theme colors, literal overrides, widgets and machine-output regression checks passed.
- Shared resource/presentation suite: all 12 tests passed. The original fixed label-column behavior is restored.
- Whitespace checks passed for tracked changes and touched untracked sources; all 185 relative file-link targets in this follow-up's changed documentation resolve. Read-only fixture output confirmed the restored layout.

Existing unrelated work was preserved. No live provider requests, installation, theme refresh, tmux reload, commit or push occurred. Native Windows PowerShell and actual font appearance remain pending acceptance.
