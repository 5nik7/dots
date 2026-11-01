# Keys and Weather menu styling

**Status: Implemented and locally verified.** Approved and verified on 2026-11-01; tracked by project Todo goal `dd17e58688484be68bfda66e9c53403e`. Native Linux/WSL and Windows PowerShell checks remain pending as agreed.

## Agreed behavior

Style Keys category/mode selectors and all Weather menu choices with the existing shared menu renderer. Keep navigation hints, Keys binding tables/details and Weather reports/previews unchanged. Reuse shared colors, application icons, per-entry overrides and popup/row formatting; preserve profile > parent > shared-default inheritance, empty glyphs and false attributes. Settings are read on invocation; existing Config save/refresh behavior remains authoritative.

Categories retain their order, wording, positive counts and one filtered snapshot. Counts and their separator use the menu description style. Modes remain text-only, with aggregate `all` first, sorted actual modes, current focus and search restoration. Styling identities are `keys:categories:APP`, `keys:modes:all`, and `keys:modes:mode:NAME`; an actual mode named `all` stays distinct. Nonprintable names use a disjoint `mode-json:` identity with ASCII JSON escaping, and empty names display `(empty)`, preserving exact selection values without invalid menu records.

Weather retains all action IDs, cache-only opening/filtering/previews, session-only location/units, and current report/Refresh behavior. Main rows use `wttr:main`; nested menus retain `wttr:Location` and `wttr:Units`. Every choice has an optional icon: current conditions use `weather.title`, location choices use `weather.location`, Help uses `navigation.help`, and new roles cover `weather.daily` (󰖙), `weather.hourly` (󰥔), `weather.units` (), `navigation.refresh` (󰑓), and `navigation.back` (󰅁). All unit choices share the units role; all Back choices share the back role.

Shared `menus.choose` gains an internal opt-in `preserve_row_styles` argument for Weather's nested selectors; existing callers keep their defaults. Final content geometry supplies percentage columns, and resolved fit geometry is not applied twice. Display data remains inert and separate from selection/action identities.

## Ownership and integration

- Primary owners: `dots-keys-maintenance` and `dots-wttr-maintenance`, with menu, configuration and CLI presentation support.
- Menu assessment: **update** both existing families' selectors; no new route or launcher.
- Configuration assessment: **update** actual consumers of `colors.apps.menu.{icon,label,description}`, `colors.icons.*`, `icons.applications.*`, and `colors.apps.menu.entries["MENU:ENTRY"]`; add only the five missing glyph roles above. Existing Config CLI/popup/explain/completion and validation expose supported fields.
- Storage, precedence and refresh remain owned by the current configuration controllers. No schema migration, second settings store or native weather configuration change.
- Both Bash and native PowerShell use the shared controllers. Native Windows keeps its terminal FZF path, existing app/config/cache destinations and separate state; no Bash/WSL dependency or tmux equivalent is introduced.
- Preserve dirty source and wiki work. No installation, live reload, publication, commit or push is authorized by this implementation.

## Goal tree and dependencies

All children have high priority and attach to `dd17e58688484be68bfda66e9c53403e`.

| Goal | Work and acceptance | Dependencies |
| --- | --- | --- |
| `1828311ab8004fe5bad34144d6283636` | Shared/per-entry fg/bg/attributes reach rows; selected styling survives; new glyph controls, inheritance/reset and empty icons work. | Foundation |
| `da421968ca5e47da815d0ee653568037` | Styled Keys category/mode menus; correct counts/snapshot/query/cancellation; unchanged binding tables/details. | Shared foundation |
| `d4b353dad1f34d3f894d5cb7d5aa63c3` | Styled icons/labels for every Weather choice; preserved query/focus, cache-only browsing, session controls and reader handoff. | Shared foundation |
| `adb7ad36d8984e05b225b3eb363c1b2a` | Isolated checks, Termux visual acceptance, data compatibility and synchronized canonical/wiki docs; native gaps recorded. | Keys and Weather |

## Acceptance and verification

Apply the [presentation gate](../docs/presentation.md#acceptance-gate). Required local evidence is owned-root automated coverage and private Termux FZF/tmux review at 40/80/120 columns and short heights, light/dark palettes, plain/color/icons combinations and `NO_COLOR`. Cover Unicode/wide/empty icons, literal labels, an actual `all` mode, selected span styles, fg/bg/attribute overrides, inheritance/reset, fit/percentage geometry, empty results, missing tools, cancellation, query/focus and two-client isolation. Providers remain mocked; bindings never execute and weather browsing never acquires data. Presentation changes must add no per-row subprocesses.

Run Keys/browser/defaults, Weather/browser, shared menu/launcher and affected style/config/alignment/discovery/completion checks sequentially. Check weather generated artifacts and Bash/native-controller parity; compare Keys print/JSON and Weather JSON/scalar/stock/report bytes under forced decoration. These fixture paths do not establish native Windows evidence.

Update canonical Keys, Weather, configuration, presentation, commands and README documentation; update test/data references only where affected. Run `tools/verify_docs.py`, whitespace validation, and guarded wiki preview/build/check after inspecting both dirty trees. Preserve unrelated generated work; report any synchronization blocker.

Native Linux/WSL and Windows PowerShell 5.1/7 terminal checks remain named pending follow-ups and do not block the agreed local completion gate. No support claim is upgraded without native evidence.

## Progress

- Saved and reconciled all four children through the scoped Todo CLI, retaining their full IDs and parent links. Each package was started when its work began.
- Shared span rendering now preserves explicit icon overrides, including false attributes, and copies presentation state so menu formatting cannot alter binding details. Weather's nested selectors opt into preserving selected-row colors.
- Keys categories and modes and all three Weather menus consume the shared preferences. Popup measurement excludes ANSI styling, and Keys percentage columns use the resolved content width without applying fit twice. No per-row subprocesses were added.
- Canonical behavior and configuration are documented in [Keys](../docs/keys.md), [Weather](../docs/wttr.md), [configuration](../docs/configuration.md#keys-and-weather-menu-appearance), [presentation](../docs/presentation.md) and [data contracts](../docs/specification.md). Command, testing, README and menu-authoring references are synchronized.

## Verification record

| Check | Result |
| --- | --- |
| Keys, browser and defaults | Passed; the category assertion was updated for shared padding/description colors and rerun. Mode edge cases include a real `all` mode, empty/control-containing names and literal IDs. |
| Weather and browser | Passed, including existing report/data contracts, cache-only browsing, session controls and native reader handoffs. Both native browser tests passed again after the geometry correction. |
| Shared menus and five new consumer/config tests | Passed: foreground/background/attributes, selected styles, empty/wide icons, color policies, inheritance/reset, Config discovery/edit/explain/popup/completion and final-width alignment. |
| Style, config values/alignment/discovery/completion and popup controls | Passed in isolated roots. |
| Bash and shared native controllers | Native-controller suite passed with unavailable native runtime skips. Bash suite has the unrelated Zsh assertion described below. Generated Weather artifacts are current. |
| Private Termux FZF/tmux | Reviewed 30 final terminal captures: five views × light/dark palettes × 40×12, 80×24 and 120×30. Actual RGB foregrounds, popup bounds and two-client isolation passed. Narrow rows truncate within their popup; longer menus scroll. No provider acquisition, weather cache or persistent preference mutation occurred. This is terminal-stream evidence, not font rasterization or native Windows evidence. |
| Documentation | Relative links, whitespace and the menu skill validator pass. Canonical sources and the available local wiki pass synchronization checks. |

The broader launcher suite retains two pre-existing Files Install/Uninstall expectation failures (`test_action_map_uses_existing_safe_routes` and `test_navigation_preserves_queries_context_help_and_workflow_return`). Both reproduce with the pre-task menu renderer, and the launcher registry/tests are unchanged by this work. The Bash suite retains `test_zsh_completion_labels_include_values_and_descriptions` failing with `KeyError: '--color='`; it also reproduces in an isolated fixture with every task-modified library restored to its pre-task snapshot. These three unrelated failures are recorded rather than presented as passing.

Native Linux and WSL terminal acceptance and native Windows PowerShell 5.1/7 FZF, Config and data-contract checks remain named follow-ups. The local suite's platform fixtures and runtime skips do not establish that evidence. Existing dirty source and generated wiki changes were preserved; no installation, live reload, commit or push was performed.
