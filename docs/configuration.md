# Configuration: inspect, change and explain

`dots config` manages Dots preferences and supported application controls. Use `dots files` when you want to manage an application's configuration file as a resource, and `dots theme` when you want to select or publish a palette. These operations have different owners and recovery records.

## Inspect before changing

```sh
dots config list
dots config get apps.menu.popup.width
dots config explain apps.menu.popup.width
dots config path
dots profile layers
```

`get` prints the effective value; `explain` adds its source, supported choices, consumer and activation behavior. Scalar values and paths remain useful in scripts. Add `--json` for structured data; object and array values have readable terminal views. Unknown keys fail instead of creating an unused preference.

## Config precedence

For shared colors, icons, formatting and application preferences, the active profile overrides its parent layers, which override shared defaults. Within a layer, an application-specific override wins over the general value. Inheritance is fieldwise: changing one style field does not erase the others. Unset/null resets supported fields to their inherited value; `false` and an empty icon remain explicit values where supported.

Use `--profile ID` to address another profile or `--defaults` to edit shared defaults; these scopes cannot be combined. `profile.alias` does not inherit. Native weather preferences have their own TOML owner. Shell startup settings also support explicit environment overrides and legacy settings files, as explained in [environment precedence](shell-environment.md#settings). See [profile configuration](profiles.md#profile-configuration) and [data contracts](specification.md) for exact rules.

## Edit a preference

```sh
dots config set apps.menu.popup.width '90%'
dots config set apps.menu.popup.border rounded
dots config set formatting.apps.cli.label_width '40%'
dots config unset apps.menu.popup.width
dots config set colors.todo.field.acceptance.value.fg
```

The last example opens that option's editor in a usable terminal. Color editors offer active palette entries, semantic roles and custom values. Other typed editors use the key's declared choices or input rules. Explicit values remain available for scripts; omitted values in noninteractive/data/dry-run calls are errors.

Bare `dots config` opens List/Get/Set. List is read-only. Get and Set first select a category and then an option. Alt-G changes category, Alt-S changes profile/default scope, and F1 opens help. Reviewed edits keep Cancel and Save visible, with Cancel selected initially; Alt-P toggles the preview. Cancellation leaves storage unchanged. The [popup guide](profiles.md#configuration-popup) covers the complete interaction.

## Know when a saved value takes effect

Shared CLI formatting and root logo choices apply on the next invocation. Popup dimensions, placement and frame colors apply when the next popup opens. Shell startup settings generally need initialization again or a new shell. Supported visual saves refresh affected active consumers while preserving the selected palette.

Use `dots config explain KEY` to check the actual consumer and activation rule. `--no-refresh` saves a visual preference without refreshing consumers; `dots config refresh` retries later. If activation fails after a successful save, the saved preference remains and the command reports the retry path. Reads and completion never publish themes or activate applications.

## Find the right control

| Area | Examples | Reference |
| --- | --- | --- |
| Icons and semantic colors | `icons.git.branch`, `colors.ui.heading.fg` | [Styles and inheritance](profiles.md#icons-and-semantic-colors) |
| CLI and menu alignment | `formatting.apps.cli.label_width`, `formatting.apps.menu.label_gap` | [Row layout](profiles.md#shared-row-alignment) |
| Popup frame and dimensions | `apps.menu.popup.border`, `apps.menu.popup.height` | [Popup appearance](profiles.md#dots-popup-appearance) |
| Font output and previews | `apps.fonts.list_details`, `apps.fonts.preview.position`, `colors.fonts.version.fg` | [Font output preferences](fonts.md#output-preferences) |
| Root help logo | `apps.cli.logo_gradient` (`classic` or `installer`) | [Application controls](profiles.md#application-and-formatting-controls) |
| Neovim editor and highlights | `apps.nvim`, `formatting.apps.nvim.lualine.sections` | [Neovim integration](neovim.md) |
| Weather | `apps.wttr` | [Native weather configuration](profiles.md#native-weather-configuration) |
| Files and source mappings | `files.dots`, `files.termux` | [Managed files](files.md) |

This is a starting map, not a second settings catalog. Completion, Config details and `config explain` read the implemented declarations. The [profile reference](profiles.md#application-and-formatting-controls) documents supported controls and platform limits.

## Recovery and troubleshooting

If a value appears unchanged, check its effective scope and source with `explain`, then its activation rule. Inspect the active layers with `dots profile` and `dots profile layers`. Use `dots config check` for validation and `dots config path` to locate storage. Do not replace a profile file to change a single key.

Config mutations use the existing guarded transaction workflow. Preserve the reported transaction ID and use `dots files history` / `dots files undo ID` for supported recovery; undo refuses destructive restoration after drift. File mappings, native app files and published themes retain their respective ownership rules.
