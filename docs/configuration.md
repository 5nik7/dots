# Configuration: inspect, change and explain

## Help and usage preferences

`apps.cli.tagline` sets the root help phrase beneath the Dots artwork. Its default is `Manage your dotfiles and more...`, without a `dots —` prefix. The value is literal, printable single-line text; an empty string hides it, and null/unset inherits. The default tagline style uses the selected theme's accent if present, otherwise the ordinary foreground.

`colors.apps.cli.help.*` styles help text across Dots, bundled applications and standalone aliases. The [help role table](presentation.md#help-syntax-and-tagline) defines executable, command, subcommand, option/flag, argument, heading, description, punctuation and tagline defaults. Each role supports `fg`, `bg`, `bold`, `dim`, `italic`, `underline`, `reverse` and `strikethrough`. Existing color references, fieldwise inheritance and reset apply. These preferences affect help and usage, including parser-error usage; ordinary reports and authored artwork retain their existing settings.

```sh
dots config browse --query colors.apps.cli.help
dots config set apps.cli.tagline 'Manage your dotfiles and more...'
dots config set colors.apps.cli.help.argument.fg magenta
dots config explain colors.apps.cli.help.tagline.fg
dots config set apps.cli.tagline ''
dots config unset apps.cli.tagline
```

These examples use shared defaults; add `--profile ID` for a profile override. Help-only saves activate on the next invocation without theme publication or application reload. Config previews/explanations show the same missing-accent fallback as help. Basic Bash and PowerShell help remain usable with built-in defaults when Python is absent.

## Cleanup preferences

`apps.cleanup.checkpoint_min_age_days` is an integer from 0 to 36500 (default 30).
It controls the next invocation's checkpoint age filter; `--older-than`
overrides it. Normal default/parent/profile resolution, validation and reset
apply. Use `dots config browse --query apps.cleanup` or Cleanup → Configuration.
Shared CLI formatting, semantic colors and resource styles apply to human views;
`icons.menu.cleanup` controls the family icon. Approval and arbitrary deletion
paths are not persistent preferences. See [Cleanup](cleanup.md).


## Clipboard preferences

`apps.clipboard` controls optional copy recording, bounded retention, deduplication, exclusions, watcher polling and previews. `colors.apps.clipboard.*` and `icons.menu.clipboard` style human reports; existing CLI/menu formatting and popup preferences remain authoritative. See the [defaults and activation table](clipboard.md#configuration-and-storage). Config exposes these through its normal hierarchy, validation, reset, completion and browser. Saves apply on the next invocation or watcher poll without publishing a theme or starting capture.

`dots config` manages Dots preferences and supported application controls. Use `dots files` when you want to manage an application's configuration file as a resource, and `dots theme` when you want to select or publish a palette. These operations have different owners and recovery records.

## Inspect before changing

```sh
dots config list
dots config get formatting.apps.menu.popup.width
dots config explain formatting.apps.menu.popup.width
dots config path
dots profile layers
```

`get` prints the effective value; `explain` adds its source, supported choices, consumer and activation behavior. Scalar values and paths remain useful in scripts. Add `--json` for structured data; object and array values have readable terminal views. Unknown keys fail instead of creating an unused preference.

## Config precedence

For shared colors, icons, formatting and application preferences, the active profile overrides its parent layers, which override shared defaults. Within a layer, an application-specific override wins over the general value. Inheritance is fieldwise: changing one style field does not erase the others. Unset/null resets supported fields to their inherited value; `false` and an empty icon remain explicit values where supported.

Unqualified `set`/`unset` and Config browser edits save Dots preferences to shared defaults. Use `--profile ID` to edit that profile instead; `--defaults` makes the shared target explicit. These scopes cannot be combined. Ordinary `get`/`list` still inspect effective active-profile values; `--defaults` inspects shared values only. `profile.alias` does not inherit. Native Weather, pkgs and Codex-alert preferences retain their native file owners, including for unqualified writes. Shell startup settings also support explicit environment overrides and legacy settings files, as explained in [environment precedence](shell-environment.md#settings). See [profile configuration](profiles.md#profile-configuration) and [data contracts](specification.md) for exact rules.

## Edit a preference

```sh
dots config set formatting.apps.menu.popup.width '90%'
dots config set formatting.apps.menu.popup.border rounded
dots config set formatting.apps.cli.label_width '40%'
dots config unset formatting.apps.menu.popup.width
dots config set colors.apps.todo.field.acceptance.value.fg
```

The last example opens that option's editor in a usable terminal. Color editors retain semantic roles, `palette.NAME` references and global references such as `colors.daylight.day.fg`. Icons offer the cached Fonts glyph search or literal input. Other typed editors use the key's declared choices or input rules. Explicit values remain available for scripts; omitted values in noninteractive/data/dry-run calls are errors.

Bare `dots config` opens List/Get/Set/Import appearance in shared-default scope. List is read-only. All shows meaningful endpoints across categories: individual icons/settings and grouped color styles such as `colors.apps.todo.field.alias.value`. A selected category immediately shows all its endpoints. Enter opens a style's fg/bg/attribute fields or the selected value's details/actions; Escape returns to the endpoint list. Alt-F opens category/subcategory filters and sorting (key A–Z, Z–A, or local overrides first). Alt-G changes category directly, Alt-A toggles individual leaf fields, Alt-S changes profile/default scope, and F1 opens help. Queries and focus are remembered. Reviewed edits keep Cancel and Save visible, with Cancel selected initially; Alt-P toggles the preview. Cancellation leaves storage unchanged. The [popup guide](profiles.md#configuration-popup) covers the complete interaction.

`dots config list` prints a categorized terminal report with the profile alias and source path, file-owner counts and corresponding `get` commands, and recursively indented settings, icons, colors, formatting and application controls. Color records combine their fields on one row, for example `high fg:warning,bold,underline` or `selection fg:bright_foreground,bg:selection_background,bold`. The value previews that exact color/style; field names remain blue. Explicit false/null fields remain visible. Icons show their resolved preview color with a muted annotation: native direct color/style names, or the configuration key supplying the color. Menu icon previews use `colors.apps.menu.icon` (theme accent by default), then any consumed icon-specific and representative per-entry overrides, matching the shared menu renderer. This also covers Keys application categories, Weather/navigation choices and launcher icons. Semantic status samples name the actual status or label control; activity/stash/separator samples identify their tmux or Gitmux context. Icons with only the ordinary text-foreground fallback have no color-key annotation. App-specific entries use their corresponding app override. Tmux clock/battery samples follow their component styles; window/session samples identify the active state in their annotation. Native weather icons use their native style and fallback rules under Icons; their stored keys remain `apps.wttr.icons` and `apps.wttr.night_icons`. File and Git samples read the existing published theme tables and label their representative filename/type or repository context. Annotations name the native `file-colors.toml` field (following `use` inheritance) or a Vivid suffix rule, rather than inventing a `dots config` key. These published samples are shown only for the active profile; saved native rule edits require the usual explicit theme publication. Other consumers may use a different context. Unbound navigation placeholders remain unannotated. Shared CLI formatting and color/icon preferences apply. JSON and ordinary redirected listings retain their existing formats.

Config menu previews, Details and Save/Reset reviews show paths under the current home directory as `~/…` (`~` for home itself). This includes source/destination files, winning sources, file mappings and path-valued settings, including nested lists and objects. File colors and icons still describe the original resource. Paths outside home, relative paths and literal `${HOME}` references retain their spelling; editors, saved values and scalar/JSON output retain the full original values.

## List categories and fallback values

```sh
dots config list colors
dots config list icons colors formatting
dots config list apps files
dots config list colors icons --json
```

List accepts `all`, `icons`, `colors`, `formatting`, `apps`, `files`, `profile`, `settings`, and `environment`. Tab completes categories after every operand. Repeated categories appear once in the requested order; `all` or no operands selects the complete report. Unknown categories are errors. Profile/default options can appear between category operands.

The report retains the existing Config key set. It does not enumerate other native files, presets or application options. Existing rows whose values come from a published template or a consumer fallback show that value and a muted source note. FZF color rows use the published template colors when their Config override is null, with styled colors/attributes. Runtime-owned values that cannot be read without executing an application identify their owner instead of claiming a resolved value. Profile/default views do not borrow another profile's publication. These are human-view annotations; stored values, JSON, scalar Get and ordinary redirected output retain their data contracts. List never publishes or reloads consumers.

## Codex warning toast

`apps.codex.toast` exposes only these five fields from the existing
`config/tmux/codex-alerts.toml` file:

| Config key | Native `[termux]` field | Default / allowed values |
| --- | --- | --- |
| `apps.codex.toast.fg` | `toast_foreground` | `warning`; palette role, `palette.NAME`, global `colors.ROLE.fg/bg` reference or `#RRGGBB` |
| `apps.codex.toast.bg` | `toast_background` | `dark_background`; same color syntax |
| `apps.codex.toast.bg_opacity` | `toast_background_opacity` | `100`; integer 0–100 percent, transparent to opaque |
| `apps.codex.toast.position` | `toast_gravity` | `middle`; `top`, `middle`, `bottom` |
| `apps.codex.toast.short` | `toast_short` | `false`; `true` adds `-s` for a shorter visible duration |

```sh
dots config get apps.codex.toast
dots config set apps.codex.toast.fg warning
dots config set apps.codex.toast.bg dark_background
dots config set apps.codex.toast.bg_opacity 50
dots config set apps.codex.toast.position top
dots config set apps.codex.toast.short true
```

Tab offers colors, positions, booleans and example opacity percentages. The Config popup uses the same editors
and guarded review/save flow. List shows the five native values with
their owning fields; foreground/background values preview their delivery color.
Opacity applies after resolving the background color: 50% on `#123456` sends
`-b "#80123456"` (Android alpha before RGB). The opaque default keeps the
existing six-digit argument. Terminal samples preview RGB and show the opacity
as a number; they do not simulate Android transparency.
Edits preserve TOML comments and unrelated notification settings, use retained
transactions, and can be undone with the reported `dots files undo` command.
Unset restores the built-in default. These native fields have no profile
inheritance; inactive profiles and `--defaults` are unavailable for this group.

The worker rereads settings each five-second cycle. An already running worker
must load the updated code once before using new opacity/hex/reference colors or reset
fallbacks. Config saves do not restart it or send a test notification. Toast
delivery remains Termux-only; `short` does not change polling or event timing.
Missing/unresolvable colors retain black-background/yellow-foreground fallbacks.
See [Codex notifications](themes.md#codex-attention-notifications).

## Codex vibration

`apps.codex.vibrate` uses the same native configuration, scope rules, Config
popup, completion and retained undo as the toast controls:

| Config key | Native `[termux]` field | Default / allowed values |
| --- | --- | --- |
| `apps.codex.vibrate.duration` | `vibration_ms` | `300`; integer 1–10000 milliseconds, passed with `-d` |
| `apps.codex.vibrate.force` | `force_vibration` | `true`; adds `-f` to allow vibration in silent mode |
| `apps.codex.vibrate.count` | `vibration_count` | `1`; integer 0–10, with zero disabling vibration only |

```sh
dots config set apps.codex.vibrate.duration 300
dots config set apps.codex.vibrate.force true
dots config set apps.codex.vibrate.count 3
dots debug alert
```

`termux-vibrate` has no count option. Dots sends the configured number of requests
sequentially, waiting the pulse duration plus 150 ms after each successful request
before the next. API latency may lengthen the interval. Failure or timeout stops
the sequence without retries. Each event starts at most one sequence, using the
settings captured at delivery. Repeats use a finite helper so toast delivery and
worker polling remain independent; an already started sequence can finish after
the event is acknowledged. Count and reset handling need an updated worker.

[`dots debug alert`](debug.md#test-codex-alerts) sends a labelled test toast and
uses these settings immediately, without creating a Codex event or restarting
the worker. It waits for all API requests and reports their results. The Config
List shows these three fields with their actual native/default source.

## Keys and Weather menu appearance

Keys category/mode selectors and Weather main/Location/Units selectors reuse `colors.apps.menu.icon`, `.label` and `.description`, plus existing `formatting.apps.menu` controls. Defaults are accent icons, blue labels and muted descriptions/counts. Individual icon roles can override the shared icon style; a per-entry style is applied last. Foreground, background and supported text attributes inherit fieldwise. Empty icons hide the glyph without leaving its separator; `false` attributes remain explicit overrides.

```sh
dots config set colors.apps.menu.label.fg blue
dots config set icons.weather.daily '󰖙'
dots config set 'colors.apps.menu.entries["keys:categories:tmux"].icon.fg' orange
dots config set 'colors.apps.menu.entries["wttr:main:daily"].label.bold' true
dots config unset 'colors.apps.menu.entries["wttr:main:daily"].label.bold'
```

Keys uses `icons.applications.APP`; see [Keys styling identities](keys.md#browsing-and-notation) for category/mode entries. Weather's icon roles are:

| Choices | Icon role | Shipped glyph |
| --- | --- | --- |
| Current conditions | `icons.weather.title` |  |
| Daily forecast | `icons.weather.daily` | 󰖙 |
| Hourly forecast | `icons.weather.hourly` | 󰥔 |
| Change location, custom and automatic location | `icons.weather.location` |  |
| Change units, US and Metric | `icons.weather.units` |  |
| Refresh | `icons.navigation.refresh` | 󰑓 |
| Help | `icons.navigation.help` | 󰋖 |
| Back / Close and submenu Back | `icons.navigation.back` | 󰅁 |

Supported glyph styles use corresponding `colors.icons.ROLE` keys. [Weather](wttr.md#commands-and-output) documents its per-entry IDs. Values are read when the menu opens, through the existing Config save/refresh workflow. Navigation hints, Keys binding-table/detail colors, native weather artwork and weather report styles retain their own owners.

## Know when a saved value takes effect

Shared CLI formatting and root logo choices apply on the next invocation. Popup dimensions, placement and frame colors apply when the next popup opens. Shell startup settings generally need initialization again or a new shell. Supported visual saves refresh affected active consumers while preserving the selected palette.

Use `dots config explain KEY` to check the actual consumer and activation rule. `--no-refresh` saves a visual preference without refreshing consumers; `dots config refresh` retries later. If activation fails after a successful save, the saved preference remains and the command reports the retry path. Reads and completion never publish themes or activate applications.

## Find the right control

| Area | Examples | Reference |
| --- | --- | --- |
| Icons and semantic colors | `icons.git.branch`, `colors.ui.heading.fg` | [Styles and inheritance](profiles.md#icons-and-semantic-colors) |
| CLI and menu alignment | `formatting.apps.cli.label_width`, `formatting.apps.menu.label_gap` | [Row layout](profiles.md#shared-row-alignment) |
| Popup frame and dimensions | `formatting.apps.menu.popup.border`, `formatting.apps.menu.popup.height` | [Popup appearance](profiles.md#dots-popup-appearance) |
| Font output and previews | `apps.fonts.list_details`, `formatting.apps.fonts.preview.position`, `colors.apps.fonts.version.fg` | [Font output preferences](fonts.md#output-preferences) |
| Root help logo | `apps.cli.logo_gradient` (`classic` or `installer`) | [Application controls](profiles.md#application-and-formatting-controls) |
| Neovim editor and highlights | `apps.nvim`, `formatting.apps.nvim.lualine.sections` | [Neovim integration](neovim.md) |
| Weather | `apps.wttr` | [Native weather configuration](profiles.md#native-weather-configuration) |
| Files and source mappings | `files.dots`, `files.termux` | [Managed files](files.md) |

This is a starting map, not a second settings catalog. Completion, Config details and `config explain` read the implemented declarations. The [profile reference](profiles.md#application-and-formatting-controls) documents supported controls and platform limits.

## Recovery and troubleshooting

If a value appears unchanged, check its effective scope and source with `explain`, then its activation rule. Inspect the active layers with `dots profile` and `dots profile layers`. Use `dots config check` for validation and `dots config path` to locate storage. Do not replace a profile file to change a single key.

Config mutations use the existing guarded transaction workflow. Preserve the reported transaction ID and use `dots files history` / `dots files undo ID` for supported recovery; undo refuses destructive restoration after drift. File mappings, native app files and published themes retain their respective ownership rules.

Package output roles and their consumers are listed in [package output colors](packages.md#output-colors). They inherit profile colors and apply on the next invocation. Native `apps.pkgs` behavior controls remain in pkgs JSON, including the default-enabled `upgrade.gem_system` self-update.

## Canonical keys and completion

Feature styles use `colors.apps.todo`, `colors.apps.fonts`, `colors.apps.wiki`,
`colors.apps.pkgs` and `colors.apps.menu` for both reports and popups. Popup geometry uses
`formatting.apps.menu.popup`, popup colors use `colors.apps.menu.popup`, and
Font preview placement uses `formatting.apps.fonts.preview`. Native FZF slots,
Neovim highlight names, weather/pkgs settings, environment names and file IDs
retain their native spelling and owner.

Tab at the key position searches all full leaf keys by default, for example
`dots config set ` followed by Tab. Type `..` then Tab for immediate branch
choices. The trigger is consumed on selection and fzf-tab opens with an empty
search field. `colors..` then Tab starts inside Colors; selecting a branch leaves
a trailing dot, so another Tab continues through its children. Bracket-quoted
native keys remain intact. The former `@` shortcut is no longer needed.

A completed leaf followed by a space and Tab offers its Allowed values,
including Dots settings, style booleans and application enums, or its symbolic
colors/cached glyphs with names and codepoints. Zsh uses its existing fzf-tab menu;
other shells use their native completion surfaces. The `..` shortcut only applies
to configuration keys; literal values and other command completions are unchanged.
Readers and completion accept old aliases, while discovery and new writes use
canonical keys. No shell startup scan, glyph download or publication occurs.

```sh
dots config set colors.apps.todo.field.alias.value.fg colors.daylight.day.fg
dots config set colors.apps.tmux.clock.icon.fg palette.rosewater
dots config set apps.tmux.clock.icon_mode daylight
dots config set apps.tmux.session.multiple true
```

See [tmux component preferences](tmux.md#component-preferences) for spans,
platform limits and activation.

To rename existing saved keys, preview and then apply the retained transaction:

```sh
dots config migrate --keys --all-profiles --json
dots config migrate --keys --all-profiles --apply --yes --json
```

Without `--all-profiles`, only the selected profile is rewritten. The all-profile
operation includes shared defaults and declared profiles. It compares effective
consumer values before saving, preserves TOML comments and unrelated fields,
rejects conflicting aliases and stale inputs, and is a no-op when repeated.
Use the reported transaction with `dots files undo ID` for guarded recovery.
Migration does not activate a profile, select a theme or reload a shell.


Backup defaults are `apps.bak.store="~/.bakstore"`, `apps.bak.location="store"`, and `apps.bak.mode="move"`. Alternatives are adjacent location and copy mode. Profile inheritance and explicit flags apply; changes take effect next invocation. There is no saved backup opt-out. Reports use existing CLI presentation controls; link rows use resource styles and `icons.operations.link`.

## Preference files and appearance import

| Data | Shared defaults | Profile overrides |
| --- | --- | --- |
| Behavior, formatting, shell settings | `default/config.json` | `profiles/NAME/config.json` |
| Colors and color attributes | `default/colors.toml` | `profiles/NAME/colors.toml` |
| Icons | `default/icons.toml` | `profiles/NAME/icons.toml` |
| Identity, inheritance, environment, paths and managed mappings | — | `profiles/NAME/profile.json` |

The typed color/icon controls use a reserved `[controls]` TOML table with quoted
public Config keys. `{ inherit = true }` declares a nullable control; `{}` declares
an extensible map. Ordinary style tables retain their existing syntax. Use
`dots config` for validated edits; there is one stored declaration per scope.
Legacy inline profile preferences remain readable, with separated files winning
at the same layer. Existing file-style catalogs, Git configuration, theme
connectors and native application files retain their specialized owners.

```sh
dots config set apps.cli.logo_gradient installer
dots config set colors.ui.heading.fg cyan --profile windows
dots config unset colors.ui.heading.fg --profile windows
dots config import termux --profile windows --dry-run
dots config import termux --profile windows --apply --yes
dots config import termux --apply --yes  # target shared defaults
dots config migrate --layout --all-profiles
dots config migrate --layout --all-profiles --apply --yes
```

Import merges source-profile appearance declarations (including inherited profile
customizations, excluding shared defaults) into the target. Imported values win;
unrelated target fields survive. `SOURCE=defaults` explicitly copies shared
appearance. Colors, icons, formatting and portable display controls (CLI logo, Fonts/Wiki
display and tmux clock/session/indicator appearance) are included. Shell settings, file mappings, environment, package choices, backup
locations and native application files are excluded. Config → Import appearance
uses the same guarded preview and Cancel/Save review; noninteractive imports
preview unless `--apply --yes` is supplied. Imports and layout migrations do not
publish themes or reload applications; new invocations read saved preferences.
Use the existing explicit refresh command when published visuals need updating.

Layout migration preserves effective values, strips only preference groups from
manifests, and supports repeat no-op and ordinary `dots files undo TRANSACTION`.
The repository's Termux appearance has been promoted to shared defaults; redundant
Termux declarations were removed so future shared edits take effect there.

The [tmux clock controls](tmux.md#retained-widget-readings) include automatic location acquisition, its refresh interval and sun-time retention. They use the same Config editor, completion, precedence and published preference refresh as the other `apps.tmux.clock` settings.
