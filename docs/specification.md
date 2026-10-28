# Implemented Data Contracts

This reference describes the data consumed and produced by the live theme, file catalog, shell and checkout installation controllers. Command-specific behavior is documented in [commands](commands.md), [files](files.md) and [installation](installation.md).

## Shared menu records

`dots menu --json` uses `menu: "dots"` and `title: "Dots menu"`, with exactly the base item fields below. Its ordered IDs are `keys`, `tmux`, `files`, `git`, `theme`, `themes`, `anodize`, `debug`, `profile`, `profiles`, `wiki`, `env`; the schema-1 envelope and base item fields remain unchanged. Action meanings are documented in [launcher commands](commands.md#dots-workflow-menu). Availability reflects static command presence, required tmux/Git executables and platform/Python limits; it does not assert that a child inventory contains results. Data views never probe FZF or run those tools. They exclude icons, action arrays, environment and private transport even when decoration is forced.

**Implemented shared library, launcher and session-menu contract.** `Menu.document(query)` in `lib/dots/menus.py` returns schema 1 with `schema` (integer 1), `menu` (stable string ID), `title` (string), and ordered `items` (array). Each base item contains exactly `id`, `label`, `description`, `available` (boolean), and `reason` (string, empty when no reason is needed). IDs must be unique within a menu; unavailable entries require a reason. Icons, executable arguments, callbacks, transport paths and environment are excluded. The shared JSON view uses escaped JSON strings and emits no ANSI, even with decoration forced.

`dots menu tmux sessions --json` uses `menu: "tmux-sessions"` and `title: "Tmux sessions"`. Its items extend the base fields with `name` (literal session-name string), `windows` (nonnegative integer), `attached_clients` (nonnegative integer) and `current` (boolean). `id` is tmux's stable `$N` session ID; `label` equals `name`, and the readable description summarizes counts and current state. All observed sessions have `available: true` and an empty `reason`. `current` refers to the inherited originating pane's session; outside tmux it is false. Socket paths, server/client PIDs and session creation times are private revalidation details, excluded from the document. No server or no sessions produces an empty `items` array; inspection failures and native Windows unavailability produce an error status and stderr diagnostic, not a misleading empty document.

Listing filters use case-insensitive whitespace-separated terms matched against each item's ID, label, description and reason; every term must match. An empty query preserves registry order. The interactive query seeds FZF without filtering the source records first. Printed/JSON and redirected default views never select or execute actions and do not probe FZF. Session views still require read-only tmux observations. `add_arguments` provides `--query` and mutually exclusive `--browse`, `--print`, `--json` parser fields for menu routes; it does not register a route itself.

`Entry`/`Menu` are immutable library records. Actions remain controller-owned literal argument arrays outside the display document. `choose` returns one `Entry`, returns `None` after a listing/empty/missing-tool fallback, or raises `SelectionEnded(130)` for cancellation. Without navigation state, failed or unavailable selection raises an error without retrying or invoking an action. The launcher opts into compact labels and a private per-frame query dictionary: `SelectionEvent` distinguishes Back and contextual help from `SelectionEnded(130)` (Ctrl-C). Unavailable entries return to the controller for a visible reason. These internal frame fields do not enter public JSON. The session controller also provides a private selected/code/message outcome so an empty inventory cannot be mistaken for completed session navigation. `run_action` preserves the selected child's exit status and requires terminal input/output or an explicit validated tmux context. Output actions capture complete stdout/stderr once, then page it. Capture presentation resolves the caller's color/icon policy and terminal dimensions; progress is disabled while capturing. Interactive commands retain their terminal. Internally, `review_output` returns `OutputResult(code, reviewed)` so command success cannot be confused with canceled reading. `run_action(kind='output')` still returns the original command status. The Git sync menu requires both success and normal reader dismissal before offering its separate confirmation. The persistent launcher displays workflow errors and returns to its menu; direct session-command statuses are unchanged.

`DOTS_MENU_CONTEXT` is a private, transient request-file reference passed only to popup-owning child workflows. Consumers must use `TmuxContext.from_environment()` before opening their own chooser. It is not a user setting or a cross-platform tmux bridge. The captured socket, exact client name/PID, pane/session and cwd are revalidated; native Windows refuses tmux context. Hosted terminal workflows receive the caller environment through private mode-0600 transport, never through the public menu document or command-line environment values. `DOTS_MENU_SPOOL_DIR` is a private host-to-child reference for temporary reader captures under that request directory, not a user setting. Output hosts capture and prepare the report, then close before a separately sized reader opens; completion receipts retain the command status independently of reader cancellation. `DOTS_MENU_READER_HANDOFF` is a private request reference set only for cooperating `document` actions. Interactive wiki browsing uses `page_text(..., defer=True)` to prepare its selected document and mark it ready before the selection host exits. Neither variable is a public option, and ordinary terminal reading stays inline. These files are removed after normal completion, cancellation or an exception; no startup cleanup, persistent registry or crash-recovery guarantee is introduced. See [ownership](architecture.md#shared-menu-support).

## Session browser projects

Interactive `dots menu tmux sessions` and managed-workspace reconciliation read this optional file:
`${XDG_CONFIG_HOME:-$HOME/.config}/dots/projects.json`. It is user-authored data;
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

`files repair` uses existing schema-1 catalogs, transaction journals and installation receipts without migrating historical data. It preserves first-install `before`/`backup`/`index` values and updates `after` for repaired destinations in the same transaction, including explicitly approved same-resource drift. Newly repaired destinations receive a pre-repair baseline; correct pre-existing links remain unowned. Receipt evidence takes precedence over transaction evidence, which uses only the latest completed operation at the destination. `replacement_unavailable` alone is informational; only actual conflicting catalog claims block repair. Interactive issue/action identities and queued decisions stay internal and introduce no new catalog, receipt or JSON fields. The schema-1 command result is specified in [repair results](files.md#repair-managed-destinations).

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

Profile schema 1 uses `id`, optional `description`, `extends`, `environment`,
`path` and `replaces_commands`; definitions and precedence are specified in
[profiles](profiles.md#definitions-and-inheritance). Profile catalogs retain the
existing explicit resource/replacement schema. The internal source flag `bundled`
marks resources that no longer need optional-source acquisition.

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
