# Config discovery and tmux controls

Status: implemented and locally verified on Termux. Native acceptance limits are recorded below. Selected Todo: `525f71ab35194ed6ab6034db071d0007`.

Primary owner: dots-config. Configuration assessment: update existing controls and add the requested tmux bindings. Menu assessment: update Config and its value editors; retain the root launcher. Follow the [presentation gate](../docs/presentation.md#acceptance-gate), [configuration contract](../docs/profiles.md), and [safety rules](../docs/safety.md).

## Agreed contract

Normalize existing Dots-owned keys under colors, icons, formatting.apps.FEATURE and apps.FEATURE. Feature names replace renderer-specific feature paths. Keep native adapter paths, DOTS/environment names, file IDs and quoted native keys. Old paths remain aliases; writes use canonical keys. Preserve layer-first inheritance, then shared/surface/feature specificity. One feature style applies to reports and popups. Retain unsupported existing records for inspection/removal.

Migrate this checkout's declared profiles through previewed retained transactions, preserving effective values, comments and unrelated fields. Reject contradictory aliases; deduplicate identical values. Verify undo, stale guards and repeat no-op. Migration does not select themes, reload shells or activate profiles.

Expose purpose, type/constraints, visible component, consumer, source/destination, effective value and activation. Add global day/night/sunrise/sunset and battery critical/low/normal/charging/unknown colors. Preserve symbolic palette/global references; missing native names fall back to the inherited semantic style and remain saved. Reject cycles and non-color references. Weather retains native overrides and read-only provider boundaries.

Tmux clock, tabs, battery, session, windows, git and indicators gain independent supported spans, styles, literal before/after surrounds and spacers. Preserve the current appearance. Clock icon supports fixed/day/night/unknown, initially hidden. Battery thresholds/glyphs inherit the provider unless overridden, and icon/text have independent styles. Session names select workspace/session/repository; host icons/colors have independent toggles and overrides. The optional multiple-session list is display-only, retains the active session under width limits, and starts disabled. Preserve Gitmux content ownership, attention detection/acknowledgement, singleton suppression and window mouse ranges. Network indicator integration is excluded.

Config List/Get/Set use branches, breadcrumbs, Back, remembered query/focus and full-path search. Keep guarded edits and default-Cancel review. Tab builds one dotted argument, keeping bracket segments intact; values include enums, palette/global colors and cached glyphs. Zsh integrates fzf-tab; other native adapters share candidates. Glyph selection inserts only, without clipboard, execution, downloads or saves. Completion and previews remain read-only.

## Work packages

| Package | Todo | Depends on |
| --- | --- | --- |
| A: canonical keys, metadata and migration | `88f9acf391e84dfe952dfe06eacad3b7` | none |
| B: references and shared colors | `a1a399169c964892a68c27809be21968` | A |
| C: clock, tabs and battery | `f37edb7daf7c4f81895c1a8adba75b87` | A, B |
| D: session, windows, Git and indicators | `feffae343f4540c796fdda3b4f27bfbc` | A, B |
| E: hierarchical browser/editors | `01226ec1427743e680f32ed5e2b88be3` | A, B |
| F: completion and glyph insertion | `2c41e7bde36c4d6d86f372d35e41a703` | A, B, E |
| G: acceptance and documentation | `e221281754394d079998ab873f95c913` | A–F |

## Acceptance

Use owned homes/config/state/cache, provider fixtures and private clients. Verify inheritance and aliases, conflict/stale/interrupted migration, rollback/undo/idempotence, real consumers, style resets, literal safety, defaults, missing providers/palette/glyph data, real Tab, cancellation and exact scalar/JSON/redirected output. Review 40/80/120 columns and short terminals, plain/light/dark output and client isolation. Measure completion/startup/status paths without adding warm-start scans or per-span processes.

Bash and shared native PowerShell controllers change together. Native Windows destinations remain unchanged; no implicit WSL/tmux activation. Clock/tabs/battery retain platform boundaries. Native Windows PowerShell 5.1/7 and desktop Linux/WSL terminal evidence must be recorded separately from Termux fixtures. Update canonical docs and available wiki output, metadata, relative links and whitespace checks. Do not commit or push.

## Evidence

The canonical interface, compatibility readers, branch browser/value editors, shell completion, symbolic references and generated tmux controls are implemented. The shared native renderer now resolves preferences from the selected checkout and receives the complete native palette when creating its snapshot. Native marker tests retain existing number colors, unread-alert precedence, inherited attributes and trailing resets.

The authorized six-file key migration completed in retained transaction `0cce5a1663294cfcb6e03d6349243f24`. Preflight compared effective typed and consumer values across all four declared profiles; the repeat preview contains no operations, and all profile checks pass. The existing Termux blocked-status style and unrelated aliases change remain intact. No live theme selection, profile activation or shell reload was performed.

Verified acceptance:

| Area | Local evidence |
| --- | --- |
| Configuration and migration | Styles (7), typed controls (13), live refresh (11), profile commands (10), row alignment (9), and discovery/migration (11), including conflict, stale-input, interruption, rollback, undo and repeat no-op checks. |
| Browsing and values | Config menu cases, popup controls (6), FZF (2), Fonts browser including selection-only glyphs (8), Fonts presentation (10), and Wiki presentation (7). The Config menu's stale fixture signature was corrected and its affected case passed on rerun. |
| Shell completion | Actual Bash, Zsh and Fish Tab insertion; actual Zsh fzf-tab branch, symbolic-color and named-glyph selection. Exact inserted text and no command execution are checked. Native controller tests (23) pass with two unavailable PowerShell-engine skips. |
| Tmux | Original status suite (19, including one optional battery-source skip), generated controls/layout (6), published activity transitions (3), and workspace cases, including the sustained two-client/provider test. Private clients cover 40/80/120 columns, literal safety, attribute isolation, alerts, singleton labels and reloads. |
| Publication and Gitmux | Selected native/Bash theme reference and transaction checks (4), all-palettes renderer/Gitmux adapter checks (5), file-color publication, and direct native Gitmux state/compact/width/color checks (2). |
| Weather | The 49-case suite has one unavailable native PowerShell skip. Its narrow-label expectation was updated to accept the supported stacked layout and passed its focused rerun; the shared/native color precedence check also passes. |
| Documentation and metadata | Command catalog validation (244 external commands), 1255 relative links across 161 Markdown files, shell syntax, config skill validation and both checkout whitespace checks. |

The local wiki was rebuilt in retained transaction `4b57476a8ee846e08834756725075b99`; its subsequent check reports healthy with no drift. No documentation was committed or published remotely. Fixture corrections preserve the behavioral assertions: workspace provider scripts are replaced atomically, and private tmux cleanup tolerates a bounded final-log race only in test-owned directories.

On this Termux session, six-call in-process measurements showed root-key discovery at 885 ms cold / 342 ms median warm, color candidates at 240 / 158 ms, and tmux compilation at 147 / 152 ms. Removing repeated consumer lookups and unnecessary path parsing reduced the measured warm root lookup from 1862 ms. These are local reader/compiler measurements, not full shell startup timings; the existing warm-start tests pass and no startup scan or per-span process was introduced.

Native acceptance still requires Windows PowerShell 5.1/7 and desktop Linux/WSL terminal runs. Shared-controller and Termux evidence do not establish those results. The direct Gitmux checks passed using the installed `~/go/bin/gitmux` through `DOTS_TEST_GITMUX`; provider fixtures and renderer parity supply additional bounded local evidence. No install, commit or push is part of this change.

## Follow-up: stale published indicators

The reported `bold] COPY bold] PREFIX bold] ZOOM` output came from the running server's older published theme, which placed comma-separated styles containing nested color expressions directly inside conditional arms. The current compiler already uses stored fragments; the live snapshot had not been refreshed during the original source implementation. `ConfigLive.test_refresh_repairs_legacy_indicator_conditionals` now reproduces the exact stale format on a private server and verifies repair through each generated tmux artifact, empty inactive output, independent COPY/ZOOM transitions, retained palette bytes and repeat no-op.

For the user's reported live issue, Config refresh completed in retained transaction `3716191cc67e4b6babebabc5eee7b98a`, producing generation `g.3fcc07d543174bb4a0dd3ea06389edcc`. The verified default tmux server was notified, and its right-hand format now expands to empty with copy mode, prefix and zoom all off. The refresh retains Catppuccin Mocha and uses the existing bounded visual refresh path; no full server configuration reload, theme selection, commit or push was performed.

## Follow-up: smart endpoints and categorized output

Status: implemented and locally verified on Termux. Primary owner remains dots-config. Menu assessment: update List/Get/Set to list all meaningful endpoints in the selected category, with All spanning categories. Icon/settings leaves remain selectable; style records group fg/bg/attributes and open their fields on Enter. Alt-F opens category/subcategory filtering and key ascending, key descending or local-first sorting; Alt-G remains the direct category chooser, Alt-A exposes individual leaf fields, and Alt-S retains scope. Queries and focus remain per frame; Back returns from a style record to its endpoint list. These are session-only view choices.

Configuration assessment: update existing discovery and presentation consumers; no new stored controls are needed. Human `config list` uses the shared CLI indentation, column and color/icon preferences, recursive children, file-owner counts/get commands, profile alias/source and weather glyph/style pairs. Native weather keys retain their actual owner. JSON, scalar values and ordinary redirected listing remain stable. `@` in the key-completion position requests all full leaf keys, replaces itself with the selected key, and supports typed narrowing; it is completion syntax, not a saved key or a command to execute. Standard dotted completion remains available. Finite Allowed values must reach value completion through shared declarations, including Dots settings, visual attributes and native weather enums.

Acceptance: isolated endpoint/filter/navigation, guarded editor, human tree at 40/80/120 columns, exact data and Bash/native-controller parity; actual Bash/Zsh/Fish insertion plus Zsh fzf-tab all-key and Allowed-value selection without execution; private multi-client popup evidence. Preserve native Windows PowerShell 5.1/7 and desktop Linux/WSL terminal checks as named pending evidence. Update source docs/metadata, validate links and whitespace, and rebuild/check local Wiki. This refinement does not activate profiles/themes, reload live shells, commit or push.

Evidence: all eight smart-browsing/report tests pass, covering endpoint grouping, category/subcategory filters, sort and frame persistence, guarded setting input, narrow recursive reports, explicit column preferences and exact Bash/native-controller output. All nine alignment tests and eleven discovery/migration tests pass. Twenty of twenty-one Config menu cases passed in the full run; the remaining case expected the old root label. That expectation was updated for All, and its focused private-client rerun and the new smart-endpoint/Alt-F test both pass at 40/80/120 columns. Explicit sorting disables FZF relevance reordering while retaining fuzzy filtering.

Actual Bash, Zsh and Fish checks verify `@` replacement, setting/style/weather Allowed values and cached glyph insertion. Fish additionally checks scoped keys and literal `@` in the value position. Real Zsh fzf-tab selects a full key from bare `@`, enum and boolean values, a symbolic color and a named glyph without executing the command or invoking a generic preview. Native Windows PowerShell 5.1/7 and desktop Linux/WSL terminal evidence remains pending. The generated manual, 244-command catalog, Markdown links, menu-authoring skill and whitespace checks pass.

## Follow-up: compact style previews and default full-key completion

Status: implemented and locally verified on Termux. This request supersedes the `@` completion shortcut above. Plain key completion lists full leaf keys. `..` requests immediate branches with an empty FZF search field; selected trailing-dot branches continue hierarchical completion. A suffix trigger such as `colors..` scopes the branch choices. Values keep their Allowed-value/color/glyph completion. Completion remains inert and shared by Bash/Zsh/Fish and the native PowerShell controller; FZF query behavior is scoped to Config keys only.

Color records in the human list combine foreground/background and attributes on one row, with their value styled as the represented sample. Icons preview their resolved style; muted annotations show native direct color/style values or the supplying configuration key. Preserve null/false fields, symbolic references, selected-profile inheritance, width wrapping, explicit columns, plain readability and exact JSON/scalar/redirected contracts. No new stored controls: existing styles and CLI formatting own this presentation. Menu assessment: existing Config browser remains unchanged; update only shell completion selection. Primary owner remains dots-config.

Acceptance: isolated compact-style/icon provenance and reset checks at 40/80/120 columns; both frontend data parity; actual native Tab and Zsh FZF blank-query/branch/leaf/value/cancellation checks, with no command execution. Validate metadata/manual/source docs and rebuild/check local Wiki. Windows PowerShell 5.1/7 and desktop Linux/WSL terminal evidence remain separate pending checks. No theme/profile activation, live shell reload, commit or push.

Evidence: the eleven browsing/report cases pass, including compact foreground/background/attribute samples, explicit false/null fields, repeated glyphs with distinct styles, native weather numeric colors/fallbacks, selected-profile inheritance, missing native palette names and exact data/frontend contracts. Tmux icon samples follow clock/battery component controls; window/session samples explicitly identify the active state. All nine alignment and eleven discovery/migration cases pass. Real Bash/Zsh/Fish checks cover branch consumption, full-key/value insertion and cached glyphs. Real Zsh fzf-tab verifies empty queries at the root and scoped/continued branches, scoped cancellation, full-key selection, Allowed values, symbolic colors and named glyphs without executing commands or generic previews. Its first Tab now opens branch choices rather than stopping after replacing the trigger with a common prefix.

Four-call measurements in an owned Termux fixture found 4,200 full-key candidates at 756 ms first call / 503 ms median of subsequent calls. Immediate root branches returned 16 candidates at a 415 ms median in the same warmed process. These measure the in-process provider, not shell startup; no cache or startup scan was added. Syntax, manual freshness, 244-command metadata, configuration-skill validation, source links and whitespace checks pass. Native Windows PowerShell 5.1/7 and desktop Linux/WSL terminal evidence remains pending.


## Follow-up: menu icon provenance correction

Status: implemented and locally verified on Termux. Menu icon samples follow the actual menu consumer: `colors.apps.menu.icon` (theme accent by default), then the role-specific `colors.icons.menu.*` override. Icons with only a generic text-foreground fallback receive no color-key annotation or trailing annotation spacing. Keep native weather/component styles, selected-profile resolution and data interfaces intact. Primary owner remains dots-config. Configuration assessment: update the listing's existing style consumer; no new controls. Menu assessment: unchanged; use its existing rendering precedence as evidence. Verify samples against `menus.entry_spans`, plain/colored widths at 40/80/120, override precedence and exact frontend data; update canonical docs and local Wiki.

Four focused checks pass: actual menu-span color parity with shared accent and icon overrides, unannotated foreground fallbacks with no trailing spacing at 40/80/120 columns, existing tmux/component and compact-style samples, and exact Bash/native-controller data output.


## Follow-up: remaining icon color consumers

Status: implemented and locally verified on Termux. Audit the undeclared preview sources against the current consumers; do not add color controls or change consumer behavior. Expand Config samples for shared menu roles (Keys categories, Weather navigation and launcher/action entries), semantic CLI statuses, tmux activity indicators, and file/repository identities. Native file and Git styles belong to the published theme rules, not `colors.icons.*`; annotate their real owner and representative filename/type/ownership context. Do not infer provenance from equal RGB values, invoke providers, scan repositories, or invent a universal color for context-dependent icons. Keep unmatched glyphs unannotated.

Primary owner: dots-config, with dots-config-audit and shared presentation. Configuration assessment: update existing preview consumers only; no controls added. Menu assessment: no behavior change; its existing entry spans supply the preview evidence. Acceptance: compare menu/status/resource samples with their actual renderers, including overrides, background-only/nullable fields, absent publication and selected-profile isolation; retain exact data output and 40/80/120-column plain/colored reports. Run isolated focused checks, source documentation validation and local Wiki rebuild/check. Native Windows PowerShell 5.1/7 and desktop Linux/WSL terminal evidence remains pending; no platform-specific runtime or destination changes.

Audited consumer evidence (source-only scan followed by direct tracing):

| Area | Existing owner and consumer | Disposition |
| --- | --- | --- |
| Menu/application/navigation choices | `menus.entry_spans`, `menu_cli.entry`, `keys.presentation.menu_rows`, `wttr.browser`, `menu_sessions.action_menu` | Shared menu style, only consumed role overrides, and representative per-entry style; annotate menu context. |
| CLI statuses/project rows | `files/catalog.py:Presentation.status`, `style_config.ROLES`, `menu_session_ui.render` | Status error/success/warning; info uses ui.label for ordinary file statuses; noncurrent project uses ui.accent. |
| Tmux activity/stash/separator | `tmux_controls.py`, `default/themed/tmux.conf.tpl`, `config/gitmux/gitmux.conf` | Follow component precedence; stash uses only ui.muted foreground; separator names its ui.separator control and native background. |
| File and Git glyphs | `resources.tsv`, `resources.Resources.describe/match_style`, `git/inspection.py`, Gitmux template tokens | Representative published rules, native use inheritance, branch/repository identity style; Gitmux consumes foreground plus its fixed attributes. Filename Vivid rules remain labeled Vivid, with no inferred field based on equal colors. |
| Weather fallback glyphs | `wttr/core.py`, `wttr/styling.py`, native icon_colors and daylight roles | Name a native override or actual daylight fallback; retain separate native icon list. |
| Unbound placeholders | navigation.environment, navigation.next, navigation.ellipsis | No active first-party named consumer found; preserve unannotated fallback. Empty fixed/unknown clock icons stay empty. |

The scanner covered first-party default/profile/config/shell/CLI/script/library/tool/plugin text, excluding non-source, symlinked, oversized and explicitly excluded inputs. No private repository initialization, home crawl or external app execution was used. Runtime listing reads only selected preferences and bounded published snapshots; it never runs this audit. Native sample publication is unavailable for a different profile or shared-default view. Existing completed Todo records are retained; this follow-up adds verification notes only.

Verification: all 15 Config browsing tests and all 17 resource regressions pass. Focused reruns cover the final background-only override and malformed optional publication handling. Human views retain exact 40/80/120-column wrapping, per-entry/menu/status/native source parity, missing snapshot fallbacks and profile isolation; Bash/native-controller data contracts remain exact. Canonical docs, relative links, whitespace and local Wiki are checked separately. No live consumer reload, theme publication, commit or push.


## Follow-up: existing-key fallback values and repeatable List categories

Status: implemented and locally verified on Termux. Final user scope is the original Config key set only. Add source-labeled fallback values to existing rows, including published FZF colors where the declared Config override is null. Do not add native file inventories, presets, additional application options or an observed-data namespace. Keep saved/JSON/scalar/redirected values exact; human annotations distinguish concrete fallback values from runtime-owned settings without evaluating apps or configuration.

Add repeatable `config list CATEGORY...` operands for the existing categories, deduplicated in requested order. No operands or `all` selects everything; unknown names fail before inspection. Preserve native/Bash parity and static completion. Profile/default views cannot borrow another profile's publication.

Owner: dots-config. Configuration assessment: update existing consumers only, no stored controls or keys. Menu assessment: no changes; existing editor keys/categories remain the source of truth. Acceptance: identical before/after key sets, FZF native styles/source precedence and last-assignment behavior, existing tmux/runtime fallback ownership, category combinations/order/errors/completion, 40/80/120-column human views and exact data contracts. Verify in owned roots, update metadata/manual/source docs and local Wiki. Native Windows PowerShell 5.1/7 and desktop Linux/WSL terminal evidence remains pending. Existing completed Todo records are retained.

Verification: all four existing-key List tests and all 15 Config browsing tests pass. Six focused checks cover published-theme readers, automatic tmux row placement, narrow/redacted profile reports and exact Bash/native-controller settings output. Tests assert unchanged key sets, no native inventory or shell evaluation, inactive-profile isolation, duplicate FZF slot precedence, category completion/order/errors and 40/80/120-column rendering. The live read-only Apps report retains its existing rows and shows FZF template sources. Manual freshness, the 244-command catalog, relative links and whitespace checks pass. Local Wiki regeneration is verified separately; native PowerShell 5.1/7 and desktop Linux/WSL remain pending.
