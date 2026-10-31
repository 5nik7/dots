# Implemented Data Contracts

This reference describes the data consumed and produced by the live theme, file catalog, shell and checkout installation controllers. Command-specific behavior is documented in [commands](commands.md), [files](files.md) and [installation](installation.md).

## Font library and catalogs

Fonts use schema-1 JSON. `<Dots state root>/fonts/collection.json` contains
`families` keyed by `nerd:NAME`, `google:LICENSE_DIRECTORY/FAMILY` or content-derived
`local:HASH`, plus `targets` keyed by app target and optional Windows Terminal GUID.
Families retain name/provider, versions, preferred version, nullable pin and
nullable installation. Version records contain filenames, SHA-256, family/style/
full names, variant, monospace/variable metadata, axes, licenses, provenance,
upstream fingerprint and payload-directory digest. Installations record one
version/variant and expected destination digests. Targets record the version/face,
configuration path/digest, explicit config path and optional profile GUID.

Payloads use `<data>/dots/fonts/library/<identity hash>/<version hash>`. POSIX data
uses XDG_DATA_HOME or `~/.local/share`; Windows uses LOCALAPPDATA. Catalogs use
`<cache>/dots/fonts/catalog.json`, where cache is XDG_CACHE_HOME or `~/.cache` on
POSIX, LOCALAPPDATA on Windows. Explicit XDG overrides take precedence. Both JSON
documents are bounded to 32 MiB. Catalogs contain family/version specs, release-keyed
glyph lists, last glyph version and refresh time. Nerd specs identify release tags,
approved HTTPS assets and optional upstream SHA-256; Google specs identify exact
commits, family paths and tree fingerprints. Imports record unknown upstream
versions. External system inventory does not establish ownership.

Command JSON uses `schema: 1` and `items`. Mutation results add `status` (`complete`,
`unchanged`, or dry-run `preview`) and nullable `transaction`; previews enumerate
operation paths/kinds. Post-commit refresh notices are separate from durable status.
Exact path and single-icon formats are described in [fonts](fonts.md).

The collection may additionally contain `directories`, keyed by the normalized absolute backend font-directory path (`abspath` plus native `normcase`). Each value is a schema-1 inventory with `families` and an empty `targets` object. Its version records add boolean `available`: uninstall sets it false while retaining the complete version metadata. Reinstallation validates the original payload digest. Directory payloads use `<directory>/.dots-fonts/library/<identity hash>/<version hash>`; loose files are never adopted. The inventory stays in local Dots state, not inside the checkout, and a moved/copied payload directory is not automatically owned.

Version records may include `known_fonts` (the original face metadata) and boolean `partial`; `fonts` lists the actually retained faces. Compatible expansion unions available faces and licenses, preserves provider identity/fingerprint, and updates the payload digest. Filename, hash or metadata conflicts are refused. Legacy full records remain readable without migration. `adoptions` on the personal collection maps stable `installed:<normalized path hash>` IDs to owned external user lookup paths, with family ID, version, face and expected post-apply digest. These references protect retained payloads from removal.

Active-profile `fonts.json` is schema 1 with an `applications` object keyed by target, optionally suffixed with `:<Windows Terminal GUID>`. Each entry records `id`, `version`, `face`, `variant`, `target`, nullable `config`/`app_profile`, `directory: "PROFILEFONTS"`, the selected `files` name-to-SHA256 map, display `name` and nullable exact `upstream` source specification. Reads never create it. Set, upgrade, rollback and explicit Restore update affected entries transactionally, preserving unrelated choices. Restore validates exact checksums; it does not select latest versions. This file neither establishes ownership of manually copied assets nor causes startup activation.

Installed inventory returns stable path IDs, `ownership` (`managed`, `user`, `system`), `supported`, `migratable`, and nullable `reason`, plus path/display fields. Discovery failures appear in `notices`; unknown/protected ownership is copy-only. Downloaded browsing adds source store information. Multiple-family Install resolves exact versions before apply; `--from` controls source and `--directory` destination. Set's `--directory` remains source selection, while automatic retention and resulting app-origin references use the active profile.

`DOTFONTS` is generated as `<checkout>/fonts` by the shared profile backend, alongside profile `*FONTS` names. `--directory` accepts only a backend-owned name or a matching absolute path; arbitrary environment values cannot redefine it. Aliases for the same path share an inventory. Directory install/update does not activate fonts. Explicit activation copies into the personal library and adds `directory` origin references to the top-level installed/target records. Directory `current` derives active selections from these references, including `selection: "user-fonts"` for registration. This allows a directory copy to be removed without breaking activation.

Directory JSON adds `directory` to the response envelope. Directory family rows add `stored_versions` and `active`; version listing statuses are `stored`, `uninstalled` or `cataloged`. `directories` returns `name`, `aliases`, `path` and `status` for each destination. Directory journals use `fonts-directory-<path hash>-<action>`; scoped undo checks this prefix and retains the global collection drift guard. An unrelated later collection change can therefore block undo rather than overwrite another directory's inventory.

Windows journal entries may add `font_registry: {name, before, after}`. Nullable
native paths are constrained to the current-user Windows Fonts directory and a
fixed HKCU font key. Mirror receipts use `<Dots state root>/fonts/registrations`.
Registry preflight, reverse rollback and inverse transactions retain file guards.

## Shared menu records

`dots menu --json` uses `menu: "dots"` and `title: "Dots menu"`, with exactly the base item fields below. Ordered IDs come from the fixed registry in `lib/dots/menu_cli.py`, including the Fonts submenu; the schema-1 envelope and base item fields remain unchanged. Action meanings are documented in [launcher commands](commands.md#dots-workflow-menu). Availability reflects static command presence, required tmux/Git executables and platform/Python limits; it does not assert that a child inventory contains results. Data views never probe FZF or run those tools. They exclude icons, action arrays, environment and private transport even when decoration is forced.

**Implemented shared library, launcher and session-menu contract.** `Menu.document(query)` in `lib/dots/menus.py` returns schema 1 with `schema` (integer 1), `menu` (stable string ID), `title` (string), and ordered `items` (array). Each base item contains exactly `id`, `label`, `description`, `available` (boolean), and `reason` (string, empty when no reason is needed). IDs must be unique within a menu; unavailable entries require a reason. Icons, executable arguments, callbacks, transport paths and environment are excluded. The shared JSON view uses escaped JSON strings and emits no ANSI, even with decoration forced.

`dots menu tmux sessions --json` uses `menu: "tmux-sessions"` and `title: "Tmux sessions"`. Its items extend the base fields with `name` (literal session-name string), `windows` (nonnegative integer), `attached_clients` (nonnegative integer) and `current` (boolean). `id` is tmux's stable `$N` session ID; `label` equals `name`, and the readable description summarizes counts and current state. All observed sessions have `available: true` and an empty `reason`. `current` refers to the inherited originating pane's session; outside tmux it is false. Socket paths, server/client PIDs and session creation times are private revalidation details, excluded from the document. No server or no sessions produces an empty `items` array; inspection failures and native Windows unavailability produce an error status and stderr diagnostic, not a misleading empty document.

Listing filters use case-insensitive whitespace-separated terms matched against each item's ID, label, description and reason; every term must match. An empty query preserves registry order. The interactive query seeds FZF without filtering the source records first. Printed/JSON and redirected default views never select or execute actions and do not probe FZF. Session views still require read-only tmux observations. `add_arguments` provides `--query` and mutually exclusive `--browse`, `--print`, `--json` parser fields for menu routes; it does not register a route itself.

`Entry`/`Menu` are immutable library records. Actions remain controller-owned literal argument arrays outside the display document. `choose` returns one `Entry`, returns `None` after a listing/empty/missing-tool fallback, or raises `SelectionEnded(130)` for cancellation. Without navigation state, failed or unavailable selection raises an error without retrying or invoking an action. The launcher opts into compact labels and a private per-frame query dictionary: `SelectionEvent` distinguishes Back and contextual help from `SelectionEnded(130)` (Ctrl-C). Unavailable entries return to the controller for a visible reason. These internal frame fields do not enter public JSON. The session controller also provides a private selected/code/message outcome so an empty inventory cannot be mistaken for completed session navigation. `run_action` preserves the selected child's exit status and requires terminal input/output or an explicit validated tmux context. Output actions capture complete stdout/stderr once, then page it. Capture presentation resolves the caller's color/icon policy and terminal dimensions; progress is disabled while capturing. Interactive commands retain their terminal. Internally, `review_output` returns `OutputResult(code, reviewed)` so command success cannot be confused with canceled reading. `run_action(kind='output')` still returns the original command status. The Git sync menu requires both success and normal reader dismissal before offering its separate confirmation. The persistent launcher displays workflow errors and returns to its menu; direct session-command statuses are unchanged.

`DOTS_MENU_CONTEXT` is a private, transient request-file reference passed only to popup-owning child workflows. Consumers must use `TmuxContext.from_environment()` before opening their own chooser. It is not a user setting or a cross-platform tmux bridge. The captured socket, exact client name/PID, pane/session and cwd are revalidated; native Windows refuses tmux context. Hosted terminal workflows receive the caller environment through private mode-0600 transport, never through the public menu document or command-line environment values. `DOTS_MENU_SPOOL_DIR` is a private host-to-child reference for temporary reader captures under that request directory, not a user setting. Output hosts capture and prepare the report, then close before a separately sized reader opens; completion receipts retain the command status independently of reader cancellation. `DOTS_MENU_READER_HANDOFF` is a private request reference set only for cooperating `document` actions. Interactive wiki browsing uses `page_text(..., defer=True)` to prepare its selected document and mark it ready before the selection host exits. Neither variable is a public option, and ordinary terminal reading stays inline. These files are removed after normal completion, cancellation or an exception; no startup cleanup, persistent registry or crash-recovery guarantee is introduced. See [ownership](architecture.md#shared-menu-support).

## Session browser projects

Interactive `dots menu tmux sessions` and managed-workspace reconciliation read this optional file:
`projects.json` beside the active profile manifest (with legacy user-config fallback). It is user-authored data;
Dots does not create or migrate it. Missing files use defaults; malformed files
fail with a diagnostic. The schema is integer `1`, with optional `roots` and
`projects` arrays. Unknown fields are rejected. Paths must be absolute or begin
with `~/`; environment variable expansion is not performed.

```json
{
  "schema": 1,
  "roots": ["~/work"],
  "projects": ["~/notes", "~/src/special-project"]
}
```

These arrays add to `~/repos` and the current Dots checkout. Each root contributes
only immediate directory children with an existing `.git` file/directory (linked
worktrees are included). Explicit projects may be ordinary directories. Missing
or unreadable roots and missing project directories are skipped. Canonical paths
deduplicate symlink aliases; no recursive search, Git invocation, cloning or
initialization occurs. Project labels use basenames and disambiguating abbreviated
paths; the preview abbreviates the home prefix with `~`. Preview data retains
complete paths and session names, while the display clips overflow at the right
edge so each logical line occupies one row.

Managed sessions use `@dots-workspace-data`, a private schema-1 JSON object with immutable `id`, optional startup `origin`, boolean `auto`, last controller-written `expected` name and canonical `projects` roots. Startup IDs preserve `PID-START`; Prefix C and popup creation use fresh 12-digit hexadecimal IDs. `@dots-workspace-auto` and `@dots-workspace-label` supply inexpensive status fields; `@dots-workspace-expected` lets the rename hook ignore controller-owned renames; session-local `@dots-session-number` is a dense creation-order index within a project/label group, empty for groups containing one session. Groups reuse picker association by canonical project root; non-project groups use the full case-sensitive logical label (termux for hidden managed defaults, multi for mixed projects, literal manual names otherwise). Attached and detached sessions count; creation ties use native session ID. A failed complete group inventory retains previous numbers. Number refresh after successful creation or project reconciliation is best effort and reports an incomplete inventory without undoing that operation; the explicit internal numbers action returns an error. These options are internal and do not extend session-menu JSON.

Reconciliation examines all live pane directories without scanning project discovery roots. Git/worktree roots anywhere and explicit `projects` (including Dots) qualify; deepest containing root wins, canonical paths collapse aliases and different paths with the same basename remain distinct. Outside-project panes contribute nothing. Zero/one/multiple roots produce `termux-ID`, `projectname-ID` or `multi-ID`; the bar hides IDs and the default label. Periods/colons in actual session prefixes become hyphens, while display labels keep their safe literal spelling. Unknown or failed observations preserve prior state. If the actual name differs from `expected`, automatic naming is disabled; the manual name remains while observed projects still update. An occupied target name is refused, never merged. Reattachment uses stored startup origin.

The browser associates managed sessions from their live `projects` snapshot, including Git roots outside configured discovery paths; zero or multiple roots remain generic. Unmanaged legacy `@dots-termux-default=1` sessions remain generic until explicitly adopted. Other unmanaged sessions prefer a matching session-local `@dots-project-root`, then the deepest project containing `session_path`, then a single distinct project among current panes. Names alone do not classify sessions. All popup actions retain native tmux IDs and preview data retains full unique names independently of display clipping.

The shared selector optionally carries a validated numeric `index` (or `None`
when no row matches) and query in `SelectionEvent`, and can restore focus using
FZF's inert filter ordering. Existing navigation callers keep their original
contract unless they opt in. Labels and previews cannot supply executable actions.

## Implemented Theme Data Boundary

The [theme format and selection rules](themes.md) use a deliberately restricted palette TOML string/table format. Runtime selection uses per-user immutable generations with legacy read-only fallback.
Family IDs permit internal hyphens, flavors do not, and native color names preserve
case/underscores. Metadata can override semantic mappings in `[roles.FLAVOR]`.
The sole dynamic `source = "pywal16"` imports validated colors.sh literals; it is
not an arbitrary source callback. Schema-1 published JSON includes additive resolved
hex `roles`; the Neovim reader still accepts earlier Catppuccin snapshots without it.

### Implemented shell color array projection

Bash/Zsh initialization projects native palette colors plus resolved Dots template colors into named associative arrays. Resolved Dots values take precedence; mode metadata is excluded. Variable ownership, reserved names, supported fields and compatibility behavior are defined by the [shell color API](themes.md#shell-and-neovim-behavior). This does not change the native palette JSON or Fish scalar interfaces.

Interactive shell initialization supplies `esc`/`ESC` as the single escape character (`0x1B`) alongside `rst`/`RST` as `ESC[0m`, independently of theme and named-color switches. Generated Bash/Zsh theme initialization supplies the same scalars and reserves `esc` against direct color-array collisions. Scope and native spellings follow the [shell environment contract](shell-environment.md#variables-and-diagnostics); these are runtime values, not configuration settings or `dots env` query fields.

### Shared syntax template colors

Both template renderers expose derived `git_added_tmtheme`, `git_deleted_tmtheme` and `git_modified_tmtheme` values from the resolved Git foreground roles. Hex colors pass through; `reset` becomes the resolved theme foreground because tmTheme foreground properties require a concrete RGB color. These are template-only tokens, not new palette fields or exported Git roles. The existing Git tokens retain their meanings. See [the shared syntax template](themes.md).

### Compiled Bat inputs

Publication and inactive setup use a separate fingerprint combining theme inputs
with Bat's executable identity/version, logical and resolved configuration paths,
and relative custom syntax names/content hashes. Source discovery uses Bat's
native `--config-dir`, honoring `BAT_CONFIG_DIR` independently of
`BAT_CONFIG_PATH`. Recursive `.sublime-syntax` inputs are captured as bounded
ordinary file snapshots alongside the generated Dots theme before compilation;
link cycles, broken inputs and preparation drift are refused before activation.
Bat's absence is an explicit fingerprint state and remains supported. The
shell-initialization fingerprint excludes syntax discovery and compiler queries.
See [custom Bat syntaxes](themes.md#custom-bat-syntaxes) for limits and refresh
behavior. Existing cache/export paths and the palette schema are unchanged.

## Implemented Inventory Catalog Boundary

The [file catalog](files.md#ownership-and-formats) joins the schema-2/3 core `.dots/files.json` registry (qualified IDs and platforms), schema-2 `.dots/sources.json` source ownership, and schema-1 profile implementation arrays. A registry entry without a profile mapping never installs. Legacy schema-1 catalogs remain readable. Public command JSON and transaction journals retain schema 1. Directory ownership
conflicts with nested target claims. Catalog inspection and tracking are distinct from the managed operation routes. Installation, linking, copying, adoption and undo use the shared file transaction engine; linking is the default and copying is explicit.

Schema 3 contains exactly `schema`, `resources` and `renames`. Resource rows keep the schema-2 shape. `renames` maps reserved qualified historical IDs directly to current registered IDs with the same owner; cycles, chains and occupied keys are invalid. Effective renames upgrade schema 2 transactionally and flatten prior history. Unchanged reads/edits retain schema 2. Receipt readers resolve historical IDs, while CLI selectors and profile mapping/replacement fields require current IDs. See [rename behavior](files.md#file-id-renames).

Mapping-result JSON remains schema 1. A rename adds an item with `status: rename`, `old_id`, `new_id`, current `id`, affected `profiles`, `metadata` paths and nullable `receipt` path. Combined edits also include the ordinary mapping/live items. Ordinary non-rename items retain their existing fields.

## Implemented location and operation data

Catalog resources accept optional boolean `enabled` (default true). False is a
profile-local stash: the record/source remains, while active target claims,
replacement precedence and installation exclude it. Existing mappings and unknown
metadata survive `files edit`; `files track --update` preserves optional metadata
including disabled state and extension metadata. Profile rows store one target; platform eligibility belongs to the core registry. Older schema-1 catalog target maps are compatibility inputs only.

Mapping operations preserve the installation receipt's first-install baseline.
An intentionally unlinked owned target uses `after: null` while retaining its
original `before`, backup transaction and index. Reinstall/restore can then create
the link without mistaking that absence for drift. Uninstall may restore the
original pre-install object. New live destinations are recorded with their own
baseline. Catalog-only edits do not create installation receipts.

The [catalog/location formats](files.md) are the bounded JSON schema-1 model under decision 0010. Per-repository `.dots/file-locations.json` describes platform-specific roots/exact paths, import destinations and exclusions. Existing catalog claims win over adoption; owner ambiguity and duplicate destinations are errors. Profile `settings.files.backup` is a boolean; legacy `dots/files.json` supplies a schema-1 fallback. CLI backup flags override both. Journals and snapshots have schema 1 and transaction IDs, object identities/hashes, phases and prior catalog/link metadata. They are machine state, not desired-state manifests. No arbitrary environment interpolation, hooks or private-source initialization is added.

The catalog's `files check` operation removes only approved absent-source entries
through the same journal model. It adds no catalog fields; unrelated record data,
replacement declarations and installation receipts are preserved. Its versioned
inspection/result JSON is documented in [files](files.md#check-missing-sources).

`files repair` uses the resolved registry/profile catalog plus existing schema-1 transaction journals and installation receipts without migrating historical data. It preserves first-install `before`/`backup`/`index` values and updates `after` for repaired destinations in the same transaction, including explicitly approved same-resource drift. Newly repaired destinations receive a pre-repair baseline; correct pre-existing links remain unowned. Receipt evidence takes precedence over transaction evidence, which uses only the latest completed operation at the destination. `replacement_unavailable` alone is informational; only actual conflicting catalog claims block repair. Interactive issue/action identities and queued decisions stay internal and introduce no new catalog, receipt or JSON fields. The schema-1 command result is specified in [repair results](files.md#repair-managed-destinations).

Anodize presentation options and LOGO1/LOGO2 precedence are defined by the [logo contract](anodize.md#terminal-logo). The `base` layout selects exact LOGO1; data schemas and recipe bytes do not change.

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

Generated command generations contain `names` (one actual executable basename per line) and `map.tsv` (one `executable<TAB>theme` pair per line, sorted by executable, with no header). Both columns use validated theme identifiers; mappings include unchanged names as identity pairs. Wrappers forward to the original theme, so the suffix changes neither family metadata nor explicit theme routes. The manifest and fingerprint cover both files, wrappers and existing completion artifacts. Old generations without `map.tsv` retain identity completion and remain valid for guarded replacement. Missing or modified manifest-covered files still trigger drift refusal.

The shared allocator first reserves canonical theme names and Dots action names. Available canonical names are retained; external PATH collisions try exactly `name-theme`, then skip if it is also occupied or reserved by another canonical theme. Verified current generated command directories are excluded from executable probes. Naming is recomputed during publication, not shell startup; PATH changes alone do not immediately rename published commands. Windows lookup is case-insensitive and includes PATHEXT plus `.ps1`; POSIX lookup requires executable files. Parent-shell aliases and functions are not inspected. No command-name override setting is introduced.

## Dots shell environment

Dots shell settings are literal data. Their profile fields, legacy data-only config.env grammar, override precedence, variable ownership and diagnostic JSON are defined in [the shell environment contract](shell-environment.md). Theme defaults are settings; active selections remain published state.

## Implemented file-style overlays

The literal TOML style fields, precedence and exported schema are specified in
[file colors](file-colors.md). These are implemented theme inputs. `use` inherits a named type style; colors
resolve per theme, and explicit false attributes override inherited true values.

## Implemented checkout installation boundary

The bounded [file catalog](files.md) drives [checkout installation](installation.md). Each selected profile supplies a single `target`; only legacy schema-1 catalog inputs use `targets` overrides. Native Windows tokens and the installation receipt are documented in those references. `.gitignore` is not a desired-state manifest.

The implemented catalog schema is unchanged by the consolidated Git layout.
For the fixed `dots:git` directory resource whose entry point includes
`gitplatform`, install/link and live mapping apply/restore additionally plan the
bounded platform selector. It is an installation companion, not an independently
claimable nested catalog target. See [managed Git selection](files.md#consolidated-git-platform-selector).

## Implemented Windows catalog destination token

The existing bounded file catalog accepts `${APP_CONFIG:app}` with an optional relative suffix. On Windows, `files/app_paths.py` resolves the named application's directory and explicit `DOTS_APP_<APP>_CONFIG` override; unsupported or ambiguous locations yield an unmapped target. On other platforms the token is inapplicable. The Windows profile supplies its native destination independently of POSIX profiles. App-specific destinations do not redefine `${CONFIG}` globally. See [Windows app destinations](powershell.md#windows-app-destinations).

The implemented eza theme connector resolves `DOTS_APP_EZA_CONFIG` before `EZA_CONFIG_DIR` and the platform default; the authoritative [destination and template contract](themes.md#eza) defines validation and override precedence.

The [Leaf contract](themes.md#leaf) defines its two generated connectors, semantic base/badge tokens, override precedence and shared validated destination resolution. Windows `${APP_CONFIG:leaf}` is unmapped without APPDATA unless explicitly overridden.

## Generated theme file inspection

`dots theme files list|info|check --json` emits schema 1 with `platform`, `generation`, `artifacts`, `findings` and `healthy`. The generation contains `status` (`available`, `absent`, `unavailable`), generation `id`, published `theme`, stable `path` and nullable `resolved_path`. Session selection overrides do not replace the published identity. No new persistent state or source manifest is written.

Artifact records are sorted by generation-relative `id` and contain `kind` (`file` or aggregate `cache`), observed `status`, `required`, stable `path`, `resolved_path`, `source`, `consumers` and `connections`. Source records contain `kind` (`bundled-override`, `personal-template`, `default-template`, `derived`, `generated`, `unknown`), nullable `path`, nullable parent `artifact`, and `basis: current-resolution`. This describes the next refresh's current source selection, never verified historical provenance. Current template outputs and fixed required artifacts may appear with missing status.

Consumer records contain `app`, `kind` (`environment`, `include`, `plugin`), `description` and `activation: unverified`. Connection records contain `app`, parent `artifact`, configured `target`, `resolved_target` (actual destination location after resolving parent directory links), literal `link_target`, `expected` stable source, `status`, `eligible`, `origin` (`fixed` or `transaction`) and nullable `reason`. Paths are absolute except the literal link value, which can be relative. Unavailable destinations use nulls. Directory connectors are associated with each listed derived child.

Findings contain a nullable artifact ID and `message`. `healthy` is false for an absent/unsafe publication, an app filter with no matching artifacts, applicable findings or unhealthy eligible connections; `--app` scopes health to matching artifacts and that app's connections while retaining global inspection failures. `info --json` restricts `artifacts` to the requested file; health/findings still describe the full captured inspection. Human statuses and discovery limits are defined in [themes](themes.md#generated-theme-files).

Successful inspection returns 0 even if it describes problems; `check` returns 1 when `healthy` is false. Invalid operands, unavailable content or paths return 1; parser/usage errors return 2; Ctrl-C cancellation returns 130. Interactive Exit succeeds. File IDs are literal, generation-relative paths without traversal, absolute paths, backslashes or internal journal paths. Completion omits control-bearing names. `path` prints exactly one path plus newline. `show --raw` and redirected regular-file `show` preserve accepted text bytes without a header or appended newline. JSON and scalar/raw output bypass decoration regardless of global settings.

Theme-file connection and consumer records also carry an additive `verification` object: `status` (`matches`, `configured`, `different`, `stale`, `not-configured`, `unknown`), `basis` (`environment`, `configuration`, `installed-content`, `unsupported`), display `summary`, concise `reason`, checked `paths`, and nullable `automation` (`enabled`, `disabled`, `unknown`). Existing consumer `activation: unverified` remains accurate for runtime loading and compatible with earlier readers. Verification data contains no unrelated environment/configuration values.

The response adds `consumer_checks` (true only for explicit `check --consumers`) and `consumer_findings` records containing `app`, `artifact`, `status` and `reason`. Default `healthy` retains its file/link meaning; with `--consumers`, relevant confirmed consumer differences or stale evidence also make it false. Unknown or disabled-plugin results do not fail the check. `info --json` reports consumer evidence only for its selected artifact, while its existing file/link health remains the captured inventory result. `--app` scopes consumer findings without removing other consumers from shared-artifact details.

Directory `show` returns a bounded human/plain listing rather than file bytes. `--source` falls back explicitly to that listing only when the artifact is a directory without an editable source. Directory `--raw` returns an error. Syntax highlighting is terminal-only and never changes scalar paths, JSON or regular-file raw/redirected bytes.

## Profile and expanded environment contracts

Profile schema 1 uses `id`, optional `description`, `alias`, `extends`, `environment`,
`path`, `replaces_commands`, `settings` and `files`; definitions and precedence are specified in
[profiles](profiles.md#definitions-and-inheritance). Profile mappings retain resource and replacement IDs; their platform eligibility comes from the core registry. The internal source flag `bundled`
marks resources that no longer need optional-source acquisition.

Profile `settings` maps registered shell names to validated strings and `files.backup` to a boolean. Profile `files` maps repository IDs to complete implementation arrays without `platforms` or `targets`. The most specific array replaces the inherited/default array for that repository; source ownership and installation receipts keep their existing identities. Profile edits and migration use Store transactions without introducing a new journal schema. See [profile configuration](profiles.md#profile-configuration).

Environment JSON remains version 1 with `values.NAME.value` and `source`, adding
`group`, inherited-match status, sensitivity, defaults and PATH contribution
metadata where applicable. Full reports also include `platform`, `profile` and
`path`. Named queries retain the version/values envelope. Private values are
redacted in every format. See [environment reporting](profiles.md#environment-reporting).

## Profile diagnostics and startup events

Existing bare profile JSON fields remain available. Selected-profile views add
`inspection_only` and retain actual facts under `detected`; foreign runtime facts
are not inferred. New collection views use version 1 with `rows` or `checks`.
Debug JSON uses version 1; startup contains `mode`, `shell`, `runs`, `summary`,
and an execution exit code. Unknown durations are null, source-entry timestamps
are identified as observer timestamps, and inclusive durations overlap. Private
values and forwarded command arguments are excluded. Startup manifests now carry
input metadata and original module identities for read-only cache inspection.
Native adapters have an inert metadata sidecar with an adapter digest.
See [the diagnostic contract](debug.md#output-and-self-tests).

### Detailed trace additions

Debug version-1 reports retain existing fields and add stable event `id`/`parent_id`, optional `self_ms`/`precision`, per-run `changes`, capture `detail`, `initial_path`/`final_path`, and adapter `capabilities`. Changes carry category, name, action, source/line, observation endpoint, process, offset and attribution precision. Selected variable values are bounded native representations; sensitive and non-scalar values are omitted. PATH reports retain ordered rows and add `raw_path`, provenance and history. `DOTS_DEBUG_RECORD=path` opts into native session recording; `DOTS_DEBUG_SESSION` points to its private temporary metadata file. Neither is a globally installed default. Recording start/stop code is an undecorated interface. Compiled startup manifests add `source_map` entries mapping generated line ranges to authored files/lines; they remain inert data.

## Canonical platform file identities

The source IDs `termux` and `windows` replace `androidots` and `windots`. Current selectors and `--with-source` reject the old names with replacement hints. Internal readers canonicalize legacy source/catalog identities, replacement references and installation entry IDs before matching. Duplicate old/new declarations for the same owner are errors. Raw receipt guards, original backup pointers and historical journals remain unchanged. Read-only inspection and no-op installation do not rewrite receipts. Authorized mutations write canonical entry IDs through the existing transaction engine, and undo restores the original receipt data.

`DOTRUBY` and `RUBYCOMP` are retired, reserved profile declaration names and absent from `dots env` and its completion, including when inherited hook metadata mentions them. Native initialization clears inherited exports and obsolete completion paths as described in [shell environment](shell-environment.md#retired-ruby-environment).

## Wiki contracts

`.dots/wiki.json` schema 1 declares `checkout`, `clone_url`, `web_url`, `source_url`, `source_branch`, `exclude_docs`, and ordered `pages` with stable `id`, `title`, `section` and either `source` or `generated: commands`. Page IDs are portable ASCII filename stems, case-insensitively unique, with `AGENTS` reserved and `Home` required; CLI selection is exact. `DOTS_WIKI_DIR` overrides the checkout path; it is observed by `dots env` when inherited, not exported during initialization.

The wiki inventory `.dots-wiki.json` schema 1 records relative source `inputs` and managed `outputs` SHA-256 hashes. It has no timestamps or volatile commit labels. Unknown wiki files remain outside generation ownership. Wiki JSON results use schema 1 with action-specific fields; raw page bytes, paths, URLs and completion remain undecorated. Git status adds `kind: wiki` to the companion root; info adds a `companions` list. Existing submodule schemas and pointer semantics remain unchanged.

## Keybinding records

`dots keys --json` uses version 1 with `rows` and `coverage`. Records retain `app`, `mode`, raw `key` (string or sequence), readable `display`, action identifier, `description`/`description_source`, `evidence` (`live` or `configured`), nullable source/line, known-default flag, optional scope/layer, and status. Live matches shadow configured evidence; separate modes remain distinct. Coverage reports counts, live availability and limitations. Display normalization never replaces raw notation. Bundled Yazi/Codex defaults use `evidence: configured` and `default: true`. Yazi table replacement can shadow an entire context; Codex remaps shadow all default alternatives for the same context/action. Explicit Codex unbinding uses `key: []`, `display: Unbound`, `default: false` and `status: disabled`; the version-1 field shape is unchanged. Codex raw chord strings remain intact, with resolved leader/sequence labels in `display`. Provider-specific static precedence does not establish live activation. Private bridge transport is bounded native metadata or JSON; it is not a command-execution interface.

Personal Zsh keyboard preferences are executable configuration in `shells/zsh/keys.zsh`, outside the shared literal settings schema. The environment registry attributes `KEYTIMEOUT` and `VI_MODE_SET_CURSOR` to that file. Plugin settings and lifecycle precedence are documented in the [Zsh keyboard reference](../shells/zsh/README.md#personal-keybindings-and-history-search).

The private tmux bridge passes `DOTS_KEYS_TARGET_PANE` for the originating pane;
it is transport context, not a public setting. An existing Zsh caller snapshot
wins, and configured-only queries skip IPC. Successful IPC maps use the existing
`live` evidence and merge rules; unavailable or ambiguous capture adds coverage
notes without changing the version-1 schema. The client waits at most one second
for transport and the worker has a two-second lifetime. Frames contain the
existing NUL-delimited shell snapshot with a 16 MiB limit. Runtime discovery is
limited to 256 entries and 16 matching responders; unsafe directories, stale
processes and malformed data are refused. See [live capture](keys.md#live-zsh-bindings-from-the-tmux-shortcut).

## Yazi plugin configuration

Yazi component settings live in the setup table in `config/yazi/init.lua`; the [plugin README](../config/yazi/plugins/dots.yazi/README.md) owns their complete interface. `githead.hide_in_tmux` is a boolean defaulting to `false`. When true, a nonempty `TMUX` environment variable at setup suppresses both Githead getters and their refresh queries, while per-file Git indicators remain active. The personal configuration enables it. Theme refreshes preserve the setup decision; changing the option or launch environment requires restarting Yazi.

### Less style environment

The shared application registry defaults `LESS` to `--mouse`. When that default is selected, the environment adapters prepend it to nonempty inherited options unless an existing `--mouse` or `--MOUSE` token is present (including an `=` argument). Existing option text is retained literally, and repeated initialization does not duplicate the mouse token. A different profile default retains ordinary environment precedence. The Python resolver and cached Bash/Zsh, Fish and PowerShell adapters use the same rule; no pager probe runs at startup. See [less mouse support](shell-environment.md#global-less-mouse-support) for activation and terminal requirements.

Interactive theme integration exports `LESS_TERMCAP_so` as an SGR reset plus truecolor foreground/background and `LESS_TERMCAP_se` as `ESC[0m`. The internal exported `_DOTS_LESS_STYLE` stores the last managed start sequence; ownership requires both the current start and reset to match. Explicit values are preserved, including empty overrides. Bash/Zsh initializers retain private foreground/background hex values independently of optional named shortcuts; native `shell.tsv` snapshots include the resolved semantic color records. Missing older records fall back to background. Existing snapshot record grammar and raw/JSON palette schemas are unchanged. See [less colors](shell-environment.md#global-less-colors) for policy and platform limits.

The separate `dots:less` catalog resource owns `config/less/lesskey`, linked to `${CONFIG}/lesskey` on POSIX and `${HOME}/_lesskey` on native Windows. On less 702+, its version-guarded `LESS` definition expands inherited option text, appends the `$` string-option delimiter, then explicitly enables `vmove,click` through `--emouse`. This launch-time policy takes precedence over inherited mouse-feature choices while retaining other options and reverse scrolling; command-line options remain later overrides. The shell environment itself is unchanged. Older versions retain shell defaults, and explicit less configuration bypasses remain effective. Theme publication does not generate or replace this resource.

## Bundled application integration

For the [application report views](presentation.md#application-reports), color precedence is an explicit application `--color` flag, then `DOTS_COLOR` (including a Dots prefix flag), then pkgs' configured `color`, then `auto`. Automatic color requires a non-dumb destination terminal and empty/unset `NO_COLOR`; explicit `always` overrides `NO_COLOR`. Icons independently follow `DOTS_ICONS`. The private reader sets `DOTS_MENU_CAPTURE=1` only in its capture child to request a human layout despite redirected streams; it supplies resolved presentation settings and the available `COLUMNS`/`LINES`. Data modes bypass this context and all decoration. This marker is internal transport, not a public CLI option. Ordinary redirected report formats remain unchanged. Application pickers and help keep their existing policies.

`plugins/manifest.json` is a schema-1 source-provenance document with an `imports` object keyed by application name, recording original repository, commit, version, imported file count and excluded Git/machine-local state. It contains no live machine state and does not select external checkout paths.

Bundled command/completion/manual entries use the existing schema-1 installation receipt, with IDs `dots:NAME:command`, `dots:NAME:completion:SHELL` and `dots:NAME:manual`. There is no separate application-install ownership database. Runtime configuration and JSON formats remain application-owned; see [bundled applications](bundled-applications.md). Generated static completion metadata is private to Dots and is regenerated with the route headers from the application grammars.

## Application plugin manifest

`plugins/manifest.json` schema 1 maps plugin IDs to relative runtime, manual and Bash/Zsh/Fish completion paths, Python requirements, platform declarations and source provenance. Absolute paths, parent traversal and incomplete asset sets are invalid. The installer guards the manifest and selected files. Paths are relative to `plugins/ID`; this declaration does not execute hooks or change command grammar. Migration uses the existing schema-1 installation plan and receipt, with `retained` inventory rows for deliberately preserved legacy material.

## Codex attention state

The optional [attention bridge](themes.md#codex-attention-notifications) reads repository preferences from `config/tmux/codex-alerts.toml` (schema 1). Its event switches, unfocused-only/view-acknowledgement policy, Termux `focus_policy` (`conservative` by default, or explicitly verified `terminal`), vibration duration/force and toast semantic roles, gravity, duration and excerpt limit are consumed directly. `toast_short = false` is the default and omits `termux-toast -s` for longer display; `true` selects short display. The polling interval is currently fixed at five seconds; unsupported schema/settings fail without notification. Full-label brackets and bold bright_red/darker_background use the existing tmux alert template rather than a competing palette.

Explicit setup merges hooks into `${CODEX_HOME:-$HOME/.codex}/hooks.json`, edits only `notify`, `features.hooks`, `tui.notification_condition` and `tui.terminal_title` in personal TOML, and installs an owned `dots-notifications.json` record holding source paths and the previous notify argv. The final title field must be `thread-id`: either a full lowercase UUID or Codex's 32-character form containing its first 29 characters followed by `...`. The latter resolves only against a unique full ID from the queue's event and lifecycle records, including acknowledged/stopped records; the incoming event ID participates during focus-at-receipt checks. The read-only identity query is capped at 4096 distinct IDs; an unavailable, unsafe, malformed or over-limit store leaves shortened fields unmatched. Missing/ambiguous IDs do not match a pane. Published snapshots and acknowledgement retain full UUIDs; raw titles and abbreviated IDs never enter the overview. These personal files belong to a retained Store transaction, not repository tracking or automatic checkout installation.

Runtime state is private `${XDG_STATE_HOME:-$HOME/.local/state}/dots/codex-alerts/`: an SQLite queue, per-socket advisory locks, and atomic JSON attention snapshots. Events carry thread/turn/request identity, kind, timestamp, lifecycle phase and a bounded excerpt; acknowledgements retain IDs and erase excerpts. Socket keys include path, device and inode. Per-socket window snapshots retain their time/window-ID contract and are filtered against current foreground Codex presence before emitting private `@N:attention` tokens. An additional private schema-1 `overview.json` carries a bounded list of registered servers, original per-server observation timestamps, socket identities, pane/window IDs, thread identities, activity/attention, session IDs/creation times, attached-client TTYs and tab PID/start-time identities. Both snapshot types expire after 15 seconds; another worker cannot refresh a stale server observation. The overview reader limits input to 1 MiB, 16 servers, 2048 panes per server, 64 clients and 256 tabs; it rejects unsafe permissions, stale/replaced sockets and invalid records. No excerpts or raw titles enter the overview. An additive SQLite topology table preserves the existing event and deduplication tables. Rendering never writes this state. Cross-worker queue claims serialize; delivery is an at-most-once attempt and does not guarantee crash recovery of a claimed notification. There is no public command/data-schema change.

## Todo goal documents

The current storage document is exactly `{"schema": 2, "goals": [...]}`. Each goal contains `id` (32 lowercase UUID hex characters), nullable `alias`, nonblank `title`, `notes`, `status` (`open`, `doing`, `blocked`, `done`), `priority` (`high`, `normal`, `low`), unique string arrays `tags` and `acceptance`, nullable `due` (`YYYY-MM-DD`) and `parent` (full ID), and timezone-aware ISO timestamps `created`, `updated`, nullable `completed`, and nullable `removed`. Completed status and timestamp agree; parent references exist and form an acyclic forest. Removal preserves the other fields apart from required project-tag repair and update timestamps. Unknown schema/record fields are refused rather than discarded.

Aliases match `[a-z][a-z0-9._-]{0,63}`, are case-sensitive and unique across all records in a scope, including removed records. UUIDs remain canonical. `@NAME` resolves an exact alias; bare hexadecimal text is a UUID/prefix selector, while other valid names resolve exact aliases. UUID-prefix ambiguity is checked before removal-state filtering. Schema 1 has the same fields except `alias`: it is validated and normalized in memory with null aliases. Only an effective mutation writes schema 2; reads, dry runs and unchanged operations preserve the stored bytes. The existing transaction retains the prior document for exact recovery/undo.

Titles allow 256 characters, notes 32,768, tags/criteria 1,024 per item and 256 items per collection, and documents at most 10,000 goals and 4 MiB. Text excludes NUL; human displays escape control characters. JSON retains literal data through JSON escaping. Project documents contain no machine-specific scope paths.

Project mutations require a tag equal to the resolved root's basename (or anchor for a filesystem root), preserving its exact spelling. Append it when absent without changing custom tag order; replacement/clearing retains the required tag. Global tags are unrestricted by this rule. Every successful project mutation backfills all records, including completed and removed goals, in the same transaction. Schema/field shape is unchanged and reads expose stored tags without repair. Renaming a project adds the new name on its next mutation without deleting the old tag. Limits include the required tag; overflow reports the affected goal IDs and refuses the whole update. Mutation results include their normal target records, followed by any other repaired records once in document order. Only effective record changes update timestamps; missing-tag repair is an effective mutation, including for schema-1 storage, while repeat repairs are no-ops.

List/show/next JSON is `{"schema": 2, "scope": {"kind": "project|global", "root": "absolute project path or null", "path": "absolute storage path"}, "goals": [...]}`. Mutation JSON adds `action`, `status` (`complete`, `planned`, `unchanged`) and `transaction` (ID or null). `note` appends to the existing notes string, inserting enough LF characters for a blank line between nonempty values while preserving both texts. It has no separate note IDs or timestamp fields. `--dry-run` returns proposed records without writing; an unchanged operation has no transaction. Goal ordering, filters, scope rules and lifecycle semantics are defined in [todo](todo.md). `path` emits the full storage path plus newline; Markdown and brief outputs are undecorated text.

Brief exports begin with `/plan ` followed by an optional `$dots-todo-planning` reference, complete trusted interview/save/implementation instructions, exact scope, scoped command examples and the selected nonremoved subtree (including full notes, criteria and completed context). Missing skill availability does not remove the self-contained workflow. In execution mode, an explicit implementation request saves/reconciles the agreed tree and continues through the work with Todo status/note updates; a save-only request stops after saving. Interview-only mode instructions do not restart planning after approval. CLI print and popup print/copy use the same bytes; Codex's app-server receives the body with explicit Plan Mode instead of a slash command. The export is intentionally a Codex planning prompt; ordinary Markdown/JSON export contracts are unchanged.

Private Codex associations use schema 1 under `<Dots state root>/todo/codex/<sha256>.json`; the key hashes the canonical goal-storage path, NUL separator and full goal UUID. Each record stores `schema`, `scope` (canonical storage path), `goal`, `thread`, `backend`, `cwd`, nullable `submission`, and optionally `previous_thread` after `--new`. A submission contains `key` (client message UUID), `state` (`sending` or `accepted`), `brief_hash` (SHA-256), and `turn` after acceptance. No prompt bodies or credentials are stored. `sending` is written before the RPC; uncertain delivery attaches without resending. Association files are bounded, validated and replaced atomically under a per-goal lock. They are machine-local integration state, not fields in portable goal JSON or a public JSON command contract.

Visual preference literals and per-key precedence are defined in [profile visual preferences](profiles.md#icons-and-semantic-colors). `preferences.json` schema 1 contains flattened icon keys, resolved color-role fields and per-consumer projections. `colors.json` includes that document under `preferences`; native Lua is serialized as data. `resources.tsv` stores matcher kind, pattern, icon token, MIME and dependency-free fallback glyph. It does not own editable icon defaults.

Generated profile variables and native maps come from `profile_environment.py`. Alias validation covers all declared profiles before assignments or config writes; aliases are not inherited. Application templates resolve after generated paths. Names, reserved-variable collision policy, immediate-directory discovery and shell representations are specified in [generated profile paths](profiles.md#generated-profile-paths).


## Visual preference resolution and publication

Visual precedence is layer-first: defaults, inherited parents, selected profile;
within a layer, general fields precede app-specific fields. Color attributes
merge separately, including explicit false. Empty icon strings override inherited
glyphs. `applications.codex` is canonical and `navigation.codex` is an alias,
with canonical declarations winning at equal layer/app specificity. The supported
binding catalog governs new edits/completion; existing unsupported declarations
remain readable and removable. Explicit process settings retain their existing
precedence; this rule concerns icons/colors.

The additive `config explain` schema-1 report contains key, profile and consumer
records with app, supported, refresh, value, source and ordered declarations.
Existing get/list JSON is preserved. Visual mutation reports add a refresh object
containing status, available transaction/generation identities and consumer
results. A pending result must not be treated as proof of visible activation.

Generated preferences retain schema 1 and include resolved CLI preferences.
`visual.tsv` contains literal three-field tab-separated icon, color and environment
records for native shell adapters. Icon values have no controls, including tabs
or newlines. `visual.json` records the visual renderer/template fingerprint,
checkout and profile. A visual refresh clones the complete active generation,
regenerates supported visuals from its published palette, and guards source
inputs plus both publication pointers. It does not change the full-theme source
fingerprint or imply a complete source/theme rebuild. See [visual behavior](profiles.md#effective-visual-values-and-refresh).

### Typed application preferences

Shared `default/config.json` is a schema-1 object containing `formatting` and
`apps`. Profile manifests accept these objects as fieldwise overrides; null
inherits, while false/zero/empty strings/lists retain their types. Literal map
keys use dot identifiers or JSON string bracket segments. No key or value is
shell-evaluated by the configuration controller. Validation, completion and
popup drafts share `config_values.py`; supported visual bindings remain in
`style_catalog.py`. Recognized absent fields resolve to null, unknown fields
remain errors, and application color reads apply the established layer-first
fallback. The JSON get envelope retains its `value` member, including null.

`formatting.apps.cli.label_width` and `formatting.apps.menu.label_width` are unions of integer `0..4096` and integer percentage strings `1%..100%`. Zero means spacing only; `label_gap` retains its nonnegative integer type and `alignment` its `left|right|center` enum. Human consumers resolve percentages against terminal or popup content cells and clamp columns/gaps to retain value space. These two formatting groups are read at invocation and do not require publication. Data output bypasses their human layout. See [shared row alignment](profiles.md#shared-row-alignment).

The published schema-1 preferences snapshot includes typed `config` data and
per-consumer `options`/`formatting` projections. Native shell adapters consume
single-line literal FZF defaults from `visual.tsv`. Neovim consumes bounded JSON
through its local bridge; tmux receives only generated formats for named owned
components. Native wttr is an explicit ownership exception: `config_wttr.py`
edits the selected native TOML with native validation and no profile overlay.
See [controls and native weather](profiles.md#application-and-formatting-controls).

`apps.menu.popup` declares dedicated Dots popup position, border style and nullable native color slots in the same typed defaults/profile objects. The shared selector applies these after generic FZF presentation preferences; shell border defaults cannot suppress a Dots frame. Position changes retain controller-owned dimensions. FZF selectors and native tmux terminal hosts read effective settings at invocation, without publication, global tmux option changes or a second configuration store. See [popup controls](profiles.md#dots-popup-appearance) for accepted fields and defaults.

Popup `width`/`height` are string-or-integer controls: `auto`, `fit`, `fill`, integer percentages 1%–100%, or integer cells 1–10000. Both default to `auto`. Resolution uses the addressed client's viewport; explicit overrides are bounded, while inline width remains owned by its terminal. Typed explain data includes `constraints` (`type`, optional finite `choices`, `syntax`, `examples`) from the validation declarations. Choices are exhaustive only for finite enums; examples do not restrict custom syntax. Profile null/reset semantics and exact scalar get output are unchanged.
