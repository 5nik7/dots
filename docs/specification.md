# Implemented Data Contracts

This reference describes the data consumed and produced by the live theme, file catalog, shell and checkout installation controllers. Command-specific behavior is documented in [commands](commands.md), [files](files.md) and [installation](installation.md).

## Implemented Theme Data Boundary

The [theme format and selection rules](themes.md) use a deliberately restricted palette TOML string/table format. Runtime selection uses per-user immutable generations with legacy read-only fallback.
Family IDs permit internal hyphens, flavors do not, and native color names preserve
case/underscores. Metadata can override semantic mappings in `[roles.FLAVOR]`.
The sole dynamic `source = "pywal16"` imports validated colors.sh literals; it is
not an arbitrary source callback. Schema-1 published JSON includes additive resolved
hex `roles`; the Neovim reader still accepts earlier Catppuccin snapshots without it.

### Implemented shell color array projection

Bash/Zsh initialization projects native palette colors plus resolved Dots template colors into named associative arrays. Resolved Dots values take precedence; mode metadata is excluded. Variable ownership, reserved names, supported fields and compatibility behavior are defined by the [shell color API](themes.md#shell-and-neovim-behavior). This does not change the native palette JSON or Fish scalar interfaces.

## Implemented Inventory Catalog Boundary

The schema-1 JSON [file catalog](files.md) is implemented for locating, classifying and tracking
source/target intent. It uses `.dots/sources.json` plus per-repository `.dots/files.json`,
explicit platform applicability and qualified replacement IDs. Directory ownership
conflicts with nested target claims. Catalog inspection and tracking are distinct from the managed operation routes. Installation, linking, copying, adoption and undo use the shared file transaction engine; linking is the default and copying is explicit.

## Implemented location and operation data

Catalog resources accept optional boolean `enabled` (default true). False is a
repository-wide stash: the record/source remains, while active target claims,
replacement precedence and installation exclude it. Existing mappings and unknown
metadata survive `files edit`; `files track --update` preserves optional metadata
including disabled state and platform targets. Catalog schema remains 1 with this
additive field; older CLIs must be updated before relying on stashing.

Mapping operations preserve the installation receipt's first-install baseline.
An intentionally unlinked owned target uses `after: null` while retaining its
original `before`, backup transaction and index. Reinstall/restore can then create
the link without mistaking that absence for drift. Uninstall may restore the
original pre-install object. New live destinations are recorded with their own
baseline. Catalog-only edits do not create installation receipts.

The [catalog/location formats](files.md) are the bounded JSON schema-1 model under decision 0010. Per-repository `.dots/file-locations.json` describes platform-specific roots/exact paths, import destinations and exclusions. Existing catalog claims win over adoption; owner ambiguity and duplicate destinations are errors. Machine-local `dots/files.json` contains schema 1 and a boolean `backup`; CLI backup flags override it. Journals and snapshots have schema 1 and transaction IDs, object identities/hashes, phases and prior catalog/link metadata. They are machine state, not desired-state manifests. No arbitrary environment interpolation, hooks or private-source initialization is added.

The catalog's `files check` operation removes only approved absent-source entries
through the same journal model. It adds no catalog fields; unrelated record data,
replacement declarations and installation receipts are preserved. Its versioned
inspection/result JSON is documented in [files](files.md#check-missing-sources).

## Implemented Anodize recipe

`themes/ID/anodize.json` is a schema-1 authoring document. [Its recipe contract](anodize.md#recipe-and-ownership) owns baseline colors, absolute adjustments, overrides, generation options, source references and local generated-file receipts. Generated `colors.toml` uses the existing flat-theme contract.

## Implemented shell path variables

The native shell initialization [environment contract](shell-init.md#environment-and-execution) owns the checkout-derived `DOTS`, `SHELLS`, binary/script/config/secrets paths and shell-directory aliases. The resolved startup file or native loader determines the checkout; initialization replaces inherited Dots path values. Custom overrides can be applied after initialization.

## Implemented theme palette and command metadata

Themes may provide `colors.toml`, `palette.toml`, or both. Palette-only themes are
queryable without resolved application roles; activation requires resolvable
background and foreground and applies existing semantic defaults. With both files,
`colors.toml` wins for application colors; native queries retain `palette.toml`.
Existing `family`, `flavor`, `default_flavor`, and `[roles]` metadata drive grouping
and resolution. A sole flavor is the implicit default; ambiguous families require
a flavor. `logo.txt` is optional usage artwork, not executable input. The exact
implemented contract is in [shared themes](themes.md#unified-commands-and-family-shortcuts).

## Dots shell environment

Dots shell settings are literal data. Their data-only config.env grammar, override precedence, variable ownership and diagnostic JSON are defined in [the shell environment contract](shell-environment.md). Theme defaults are settings; active selections remain published state.

## Implemented file-style overlays

The literal TOML style fields, precedence and exported schema are specified in
[file colors](file-colors.md). These are implemented theme inputs. `use` inherits a named type style; colors
resolve per theme, and explicit false attributes override inherited true values.

## Implemented checkout installation boundary

The bounded [file catalog](files.md) drives [checkout installation](installation.md). Its optional resource `targets` map overrides `target` by platform. Native Windows tokens and the installation receipt are documented in those references. `.gitignore` is not a desired-state manifest.

The implemented catalog schema is unchanged by the consolidated Git layout.
For the fixed `dots:git` directory resource whose entry point includes
`gitplatform`, install/link and live mapping apply/restore additionally plan the
bounded platform selector. It is an installation companion, not an independently
claimable nested catalog target. See [managed Git selection](files.md#consolidated-git-platform-selector).

## Implemented Windows catalog destination token

The existing bounded file catalog accepts `${APP_CONFIG:app}` with an optional relative suffix. On Windows, `files/app_paths.py` resolves the named application's directory and explicit `DOTS_APP_<APP>_CONFIG` override; unsupported or ambiguous locations yield an unmapped target. On other platforms the token is inapplicable. Catalog `targets.windows` can override a POSIX default. App-specific destinations do not redefine `${CONFIG}` globally. See [Windows app destinations](powershell.md#windows-app-destinations).

The implemented eza theme connector resolves `DOTS_APP_EZA_CONFIG` before `EZA_CONFIG_DIR` and the platform default; the authoritative [destination and template contract](themes.md#eza) defines validation and override precedence.

The [Leaf contract](themes.md#leaf) defines its two generated connectors, semantic base/badge tokens, override precedence and shared validated destination resolution. Windows `${APP_CONFIG:leaf}` is unmapped without APPDATA unless explicitly overridden.
